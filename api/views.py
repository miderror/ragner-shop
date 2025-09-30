import logging
from decimal import Decimal

from asgiref.sync import async_to_sync, sync_to_async
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from integrations.shop2topup import shop2topup_api
from items.models import FreeFireRegionPrice, Item, PUBGUCItem
from orders.models import Order, TopUp
from orders.services import (
    InsufficientBalanceError,
    ItemNotActiveError,
    OutOfStockError,
    create_free_fire_order,
    create_order_service,
)

from .permissions import HasPositiveBalance
from .serializers import (
    CreateOrderSerializer,
    CreatePaymentSerializer,
    FreeFireProductSerializer,
    OrderSerializer,
    PaymentSerializer,
    ProductSerializer,
    ProfileSerializer,
)


@extend_schema(
    summary="Get User Profile",
    description="Retrieves the profile information for the authenticated user.",
    responses={200: ProfileSerializer},
)
class ProfileView(APIView):
    permission_classes = [HasPositiveBalance]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response({"success": True, **serializer.data})


class ProductViewSet(ReadOnlyModelViewSet):
    queryset = PUBGUCItem.objects.filter(is_active=True, category=Item.Category.PUBG_UC)
    serializer_class = ProductSerializer
    permission_classes = [HasPositiveBalance]


@extend_schema(
    summary="Get Free Fire Products",
    description="Retrieves a list of available Free Fire products with prices per region.",
)
class FreeFireProductViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = FreeFireRegionPrice.objects.filter(
        is_active=True, item__is_active=True
    ).select_related("item", "region")
    serializer_class = FreeFireProductSerializer
    permission_classes = [HasPositiveBalance]


@extend_schema(
    summary="Manage Orders",
    description="List your orders, retrieve a specific order, or create a new one.",
)
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [HasPositiveBalance]

    def get_queryset(self):
        return Order.objects.filter(tg_user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrderSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        return async_to_sync(self.a_create)(request, *args, **kwargs)

    async def a_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        await sync_to_async(serializer.is_valid)(raise_exception=True)

        data = serializer.validated_data

        item_id = data.pop("item_id")
        item = await sync_to_async(get_object_or_404)(Item, id=item_id)
        try:
            order = None
            if item.category == Item.Category.FREE_FIRE:
                player_id = data.get("pubg_id")
                region_id = data.get("region_id")

                region_price_obj = await FreeFireRegionPrice.objects.aget(
                    item_id=item.id, region_id=region_id
                )
                final_price = float(region_price_obj.final_price)

                if request.user.balance < Decimal(str(final_price)):
                    raise InsufficientBalanceError(
                        "You do not have enough balance for this Free Fire item."
                    )

                player_info = await shop2topup_api.get_player_info(player_id)
                if not player_info:
                    return Response(
                        {
                            "success": False,
                            "error": "Could not find a player with this ID.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                player_name = player_info.get("player_name", "Unknown")

                order = await create_free_fire_order(
                    tg_user=request.user,
                    item_id=item.id,
                    region_id=region_id,
                    player_id=player_id,
                    player_name=player_name,
                    price=final_price,
                )
                if not order:
                    raise Exception("Failed to create order with the provider.")

            else:
                order = await create_order_service(
                    tg_user=request.user, item=item, **data
                )

            return Response(
                {
                    "success": True,
                    "order_id": order.id,
                    "message": "Order created successfully and is being processed.",
                },
                status=status.HTTP_201_CREATED,
            )
        except ItemNotActiveError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except InsufficientBalanceError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except OutOfStockError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logging.error(f"Unexpected error during API order creation: {e}")
            return Response(
                {"success": False, "error": "An internal error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    summary="Manage Payments",
    description="List your payment requests, retrieve a specific one, or create a new payment request.",
)
class PaymentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [HasPositiveBalance]

    def get_queryset(self):
        return TopUp.objects.filter(tg_user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        return async_to_sync(self.a_create)(request, *args, **kwargs)

    async def a_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        topup = await TopUp.objects.acreate(
            tg_user=request.user, amount=serializer.validated_data["amount"]
        )

        response_serializer = PaymentSerializer(topup)
        return Response(
            {"success": True, **response_serializer.data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Check Free Fire Player ID",
    description="Validates a Free Fire Player ID and returns the player's name and region.",
    request={"application/json": {"properties": {"player_id": {"type": "string"}}}},
    responses={
        200: {
            "description": "Player found",
            "examples": {
                "application/json": {
                    "success": True,
                    "player_name": "MockPlayer_123",
                    "region": "RU",
                }
            },
        },
        400: {
            "description": "Invalid input or player not found",
            "examples": {
                "application/json": {"success": False, "error": "Player not found."}
            },
        },
    },
)
class FreeFirePlayerCheckView(APIView):
    permission_classes = [HasPositiveBalance]

    def post(self, request, *args, **kwargs):
        return async_to_sync(self.a_post)(request, *args, **kwargs)
    
    async def a_post(self, request, *args, **kwargs):
        player_id = request.data.get('player_id')
        if not player_id:
            return Response(
                {"success": False, "error": "player_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        player_info = await shop2topup_api.get_player_info(str(player_id))

        if not player_info:
            return Response(
                {"success": False, "error": "Player not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"success": True, **player_info})
