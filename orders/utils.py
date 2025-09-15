import logging
from datetime import timedelta

from django.utils import timezone
from asgiref.sync import sync_to_async

from backend.config import PAYMENT_CONFIG, URL_CONFIG
from items.models import Item
from payments.smileone import so_api
from bot.tasks import send_notification_task
from .models import TopUp, Order

logger = logging.getLogger()


async def delete_old_topups():
    lifetime = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_LIFETIME)()
    target_date = timezone.now() - timedelta(minutes=lifetime)
    logger.info(f'Deleting unpayed topups before {target_date}')
    await TopUp.objects.filter(created_at__lt=target_date, is_paid=False, is_topped=False).adelete()


def get_user_zone_id(text: str):
    user_id = text.split('(')[0]
    zone_id = text.split('(')[1].split(')')[0]
    return user_id, zone_id


def process_diamond(order: Order):
    item = order.item
    if item.category == Item.Category.DIAMOND:
        user_id, zone_id = get_user_zone_id(order.pubg_id)
        succ, msg = so_api.create_order(item.data.get('product'), item.data.get('id'), user_id, zone_id)
        logger.debug(msg)
        order.is_completed = succ
        order.save(update_fields=('is_completed',))
        if not succ:
            text = f'Activation of order {order.id} failed\nServer response: {msg}'
            logger.error(f'{text}')
            send_notification_task.delay(URL_CONFIG.ADMIN_ID, text)
