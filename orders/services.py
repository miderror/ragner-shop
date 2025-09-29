import logging
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.db import transaction

from integrations.shop2topup import shop2topup_api
from items.models import Item
from users.models import TgUser

from .models import Order
from .tasks import check_free_fire_order_status_task

logger = logging.getLogger(__name__)


class OrderCreationError(Exception):
    """Базовый класс для ошибок создания заказа."""

    pass


class InsufficientBalanceError(OrderCreationError):
    """Ошибка при недостаточном балансе."""

    pass


class OutOfStockError(OrderCreationError):
    """Ошибка, если товара нет в наличии."""

    pass


class ItemNotActiveError(OrderCreationError):
    """Ошибка, если товар неактивен."""

    pass


@sync_to_async
@transaction.atomic
def create_order_service(
    *,
    tg_user: TgUser,
    item: Item,
    quantity: int = 1,
    pubg_id: str | None = None,
) -> Order:
    if not item.is_active:
        raise ItemNotActiveError("This item is currently not available for purchase.")

    is_stockable = item.category in (Item.Category.CODES, Item.Category.GIFTCARD)
    if not is_stockable and quantity != 1:
        logger.warning(
            f"Attempted to buy non-stockable item #{item.id} with quantity {quantity}. "
            f"Forcing quantity to 1 for user {tg_user.tg_id}."
        )
        quantity = 1

    price = item.price * quantity
    if price > tg_user.balance:
        raise InsufficientBalanceError("You do not have enough balance.")

    stock = item.get_stock_amount()
    if stock is not None and stock < quantity:
        raise OutOfStockError(f"Not enough stock. Available: {stock}")

    locked_user = TgUser.objects.select_for_update().get(id=tg_user.id)

    order = Order.objects.create(
        tg_user=locked_user,
        item=item,
        quantity=quantity,
        data=item.to_dict(),
        price=price,
        category=item.category,
        pubg_id=pubg_id,
        balance_before=locked_user.balance,
    )

    logger.info(f"Order #{order.id} created for user {tg_user.tg_id} via service.")

    order.grab_codes()

    return order


@sync_to_async
@transaction.atomic
def create_free_fire_order(
    *,
    tg_user: TgUser,
    item_id: int,
    region_id: int,
    player_id: str,
    player_name: str,
    price: float,
) -> Order | None:
    item = Item.objects.get(id=item_id)
    price_decimal = Decimal(str(price))

    locked_user = TgUser.objects.select_for_update().get(id=tg_user.id)

    if locked_user.balance < price_decimal:
        logger.error(f"User {tg_user.tg_id} balance check failed inside transaction.")
        return None

    order = Order.objects.create(
        tg_user=locked_user,
        item=item,
        quantity=1,
        data=item.to_dict(),
        price=price_decimal,
        category=Item.Category.FREE_FIRE,
        pubg_id=player_id,
        player_name=player_name,
        balance_before=locked_user.balance,
        is_completed=None,
    )

    import asyncio

    provider_trx_id = asyncio.run(
        shop2topup_api.create_topup(player_id, item.provider_item_id)
    )

    if provider_trx_id:
        order.provider_transaction_id = provider_trx_id
        order.save()

        check_free_fire_order_status_task.apply_async(
            args=[order.id],
            countdown=30,
        )
        return order
    else:
        logger.error(
            f"Failed to create topup via Shop2TopUp for order {order.id}. Transaction will be rolled back."
        )
        transaction.set_rollback(True)
        return None
