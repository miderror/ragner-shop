import logging

from celery.exceptions import Retry

from backend.celery import app
from bot.tasks import send_notification_task
from integrations.shop2topup import shop2topup_api
from items.models import Item

from .models import Order
from .utils import process_diamond

logger = logging.getLogger(__name__)


@app.task()
def process_order_task(order_id):
    """Фоново обрабатывает заказ."""
    order = Order.objects.select_related(
        "item",
    ).get(id=order_id)
    if order.item.category == Item.Category.DIAMOND:
        process_diamond(order)


@app.task(bind=True, max_retries=10)
def check_free_fire_order_status_task(self, order_id):
    import asyncio

    try:
        order = Order.objects.get(id=order_id)
        if order.is_completed is not None:
            logger.info(f"Order {order_id} already has a final status. Stopping task.")
            return

        status_info = asyncio.run(
            shop2topup_api.get_transaction_status(order.provider_transaction_id)
        )

        if not status_info:
            raise ValueError("Failed to get status from API: empty response.")

        status = status_info.get("status")
        if status == "DONE":
            order.is_completed = True
            order.save()
            send_notification_task.delay(
                order.tg_user.tg_id,
                f"✅ Success! Your order for {order.item.title} has been completed.",
            )
            logger.info(f"Order {order_id} completed successfully.")

        elif status in ["PROCESSING", "TRX_NOT_READY"]:
            delay = 60 * (self.request.retries + 1)
            logger.info(
                f"Order {order_id} is still processing. Retrying in {delay} seconds."
            )
            self.retry(countdown=delay)

        else:
            raise ValueError(f"Order failed with status: {status}")

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for status check.")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error checking status for order {order_id}: {e}")
        try:
            order_to_fail = Order.objects.get(id=order_id)
            if order_to_fail.is_completed is None:
                order_to_fail.is_completed = False
                order_to_fail.save()
                order_to_fail.tg_user.process_payment(order_to_fail.price)
                send_notification_task.delay(
                    order_to_fail.tg_user.tg_id,
                    f"❌ Unfortunately, there was an error with your order for {order_to_fail.item.title}. The funds have been returned to your balance.",
                )
        except Order.DoesNotExist:
            logger.error(f"Could not fail order {order_id} as it was not found.")
