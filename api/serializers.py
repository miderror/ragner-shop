from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from items.models import FreeFireRegionPrice, Item, PUBGUCItem
from orders.models import Order, TopUp
from users.models import TgUser


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TgUser
        fields = ("tg_id", "username", "first_name", "balance")


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.SerializerMethodField()

    class Meta:
        model = PUBGUCItem
        fields = ("id", "title", "price", "amount", "stock")

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_stock(self, obj: Item):
        return obj.get_stock_amount()


class FreeFireProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="item.id", read_only=True)
    title = serializers.CharField(source="item.title", read_only=True)
    region_id = serializers.IntegerField(source="region.id", read_only=True)
    region_name = serializers.CharField(source="region.display_name", read_only=True)

    class Meta:
        model = FreeFireRegionPrice
        fields = ("id", "title", "region_id", "region_name", "final_price")


class OrderSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "item_title",
            "quantity",
            "price",
            "status",
            "pubg_id",
            "created_at",
        )


class CreateOrderSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)

    pubg_id = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Required for PUBG UC, Popularity, Manual Orders, etc.",
    )
    free_fire_id = serializers.CharField(
        max_length=50, required=False, help_text="Required for Free Fire items."
    )
    username = serializers.CharField(
        max_length=50, required=False, help_text="Required for Telegram Stars."
    )
    user_id_zone_id = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Required for Mobile Legends Diamonds (e.g., '123456(7890)').",
    )
    region_id = serializers.IntegerField(
        required=False, help_text="Required for Free Fire items."
    )

    def validate(self, data):
        try:
            item = Item.objects.select_related("manual_category").get(
                id=data["item_id"]
            )
        except Item.DoesNotExist:
            raise serializers.ValidationError(
                {"item_id": "Item with this ID does not exist."}
            )

        if not item.is_active:
            raise serializers.ValidationError(
                {"item_id": "This item is currently not available for purchase."}
            )

        category = item.category

        is_stockable = category in (Item.Category.CODES, Item.Category.GIFTCARD)
        quantity = data.get("quantity", 1)

        if is_stockable:
            if quantity < 1:
                raise serializers.ValidationError(
                    {"quantity": "A quantity of at least 1 is required."}
                )
        else:
            if "quantity" in data and data["quantity"] != 1:
                raise serializers.ValidationError(
                    {"quantity": "This item can only be purchased in a quantity of 1."}
                )
            data["quantity"] = 1

        manual_category = item.manual_category

        if manual_category:
            if not data.get("pubg_id"):
                raise serializers.ValidationError(
                    {
                        "pubg_id": f"This field is required for '{item.title}'. Prompt: '{manual_category.prompt_text}'"
                    }
                )

        elif category in (
            Item.Category.PUBG_UC,
            Item.Category.POPULARITY,
            Item.Category.HOME_VOTE,
            Item.Category.OFFERS,
        ):
            if not data.get("pubg_id"):
                raise serializers.ValidationError(
                    {"pubg_id": "This field is required for this item type."}
                )

        elif category == Item.Category.DIAMOND:
            if not data.get("user_id_zone_id"):
                raise serializers.ValidationError(
                    {
                        "user_id_zone_id": "This field is required (format: 'USERID(ZONEID)')."
                    }
                )
            data["pubg_id"] = data.pop("user_id_zone_id")

        elif category == Item.Category.STARS:
            if not data.get("username"):
                raise serializers.ValidationError(
                    {"username": "This field is required for Telegram Stars."}
                )
            data["pubg_id"] = data.pop("username")

        elif category == Item.Category.FREE_FIRE:
            player_id = data.get("free_fire_id")
            region_id = data.get("region_id")
            if not player_id:
                raise serializers.ValidationError(
                    {"free_fire_id": "This field is required for Free Fire items."}
                )
            if not region_id:
                raise serializers.ValidationError(
                    {"region_id": "This field is required for Free Fire items."}
                )
            
            data["pubg_id"] = data.pop("free_fire_id")

            if not FreeFireRegionPrice.objects.filter(
                item_id=item.id, region_id=region_id, is_active=True
            ).exists():
                raise serializers.ValidationError(
                    {"region_id": "Invalid item and region combination."}
                )

        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopUp
        fields = ("id", "amount", "to_pay", "is_paid", "created_at")


class CreatePaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("1.00")
    )
