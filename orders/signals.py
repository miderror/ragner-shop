import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from bot.keyboards import KEYBOARDS
from bot.tasks import send_notification_task
from items.models import Item

from .models import Order, TopUp
from .tasks import process_order_task

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def order_pre_save(sender, instance: Order, **kwargs):
    old = (
        Order.objects.filter(id=instance.id).select_related("item__chat").first()
        if instance.id
        else None
    )
    if not old or old.is_completed is None:
        if instance.is_completed:
            text = f"{instance.user_str()}"
            logger.info(text)
            send_notification_task.delay(
                instance.tg_user.tg_id, text, message_id=instance.message_id
            )
            text = instance.admin_str()
            instance.send_manager_notification(text)
        if instance.is_completed is False:
            text = f"{instance.admin_str()}\nis failed"
            logger.info(text)
            instance.send_manager_notification(text)
            error_message = "ERROR🤬 Try redeeming the code mentioned in the last line"
            text = f"{error_message}\n\n{instance.user_str()}"
            send_notification_task.delay(
                chat_id=instance.tg_user.tg_id,
                text=text,
                message_id=instance.message_id,
            )


@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created, **kwargs):
    if created:
        if instance.category in (
            Item.Category.OFFERS,
            Item.Category.POPULARITY,
            Item.Category.HOME_VOTE,
            Item.Category.STARS,
        ):
            text = f"Complete order\n{instance.admin_str()}\n by yourself"
            logger.info(text)
            if chat := instance.item.chat:
                send_notification_task.delay(
                    chat.tg_id,
                    text,
                    keyboard=KEYBOARDS.MAKE_ORDER_COMLETED,
                    kwargs={"id": instance.id},
                )
        if instance.category == Item.Category.DIAMOND:
            process_order_task.delay(instance.id)


@receiver(pre_save, sender=TopUp)
def topup_pre_save(sender, instance: TopUp, **kwargs):
    old = TopUp.objects.filter(id=instance.id).first() if instance.id else None
    if old and not old.is_paid and instance.is_paid and not instance.is_topped:
        instance.top()
    if old:
        old.refresh_from_db()
        if not old.is_topped and instance.is_topped:
            if instance.currency == TopUp.Currency.USDT:
                text = "Your account has been successfully topped up"
            elif instance.currency == TopUp.Currency.RUB:
                text = (
                    f"{instance.amount} {instance.currency} Payment Received successfully\n"
                    f"{instance.convert_to_ustd()}$ have been added to your account"
                )
            send_notification_task.delay(instance.tg_user.tg_id, text=text)
