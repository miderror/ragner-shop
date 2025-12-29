import logging

from asgiref.sync import async_to_sync, sync_to_async
from django.db import transaction
from django.db.models import Sum

from backend.celery import app
from backend.config import URL_CONFIG
from bot.tasks import send_notification_task
from orders.models import Order
from payments.activators import (
    aactivate_code,
    aactivate_code_fars,
    aactivate_code_kokos,
    aactivate_code_midasbuy,
)

from .models import Activator, ActivatorPriority, UcCode

logger = logging.getLogger(__name__)


def _check_and_complete_order_sync(order_id: int):
    try:
        with transaction.atomic():
            order_locked = Order.objects.select_for_update().get(id=order_id)

            if order_locked.is_completed is not None:
                logger.info(
                    f"Order {order_id} already has a final status. Skipping check."
                )
                return

            codes = UcCode.objects.filter(
                order=order_locked, is_success=True
            ).aggregate(Sum("amount"))
            order_amount = order_locked.data.get("amount")
            ready_amount = codes.get("amount__sum", 0) or 0

            logger.info(
                f"order_id={order_locked.id} order_amount={order_amount} ready_amount={ready_amount}"
            )

            if ready_amount >= order_amount:
                logger.info(
                    f"Completing order {order_locked.id}. Setting is_completed=True."
                )
                order_locked.is_completed = True
                order_locked.save(update_fields=("is_completed",))
            else:
                logger.info(f"Order {order_locked.id} is not yet complete.")

    except Order.DoesNotExist:
        logger.error(f"Order with id={order_id} not found during sync check.")


async def check_order(order: Order):
    await sync_to_async(_check_and_complete_order_sync, thread_sensitive=True)(order.id)


async def activate_code(code: UcCode, pubg_id: str):
    logger.info(f"Activating code {code.code} for user {pubg_id}")

    activator_functions = {
        Activator.UCODEIUM: aactivate_code,
        Activator.KOKOS: aactivate_code_kokos,
        Activator.FARS: aactivate_code_fars,
        Activator.MIDASBUY: aactivate_code_midasbuy,
    }

    priorities = await sync_to_async(list)(
        ActivatorPriority.objects.filter(is_active=True)
        .order_by("order")
        .values_list("name", flat=True)
    )

    if not priorities:
        logger.error("No activators priorities are configured in the admin panel!")
        await process_result(code, False, "Configuration Error: No activators.")
        return

    final_success = False
    final_status = "No activator succeeded."

    for activator_name in priorities:
        logger.info(f"Trying activator: {activator_name} for code {code.code}")

        activation_func = activator_functions.get(activator_name)
        if not activation_func:
            logger.warning(
                f"No activation function found for '{activator_name}'. Skipping."
            )
            continue

        try:
            kwargs = {"player_id": pubg_id, "uc_code": code.code}
            if activator_name in [Activator.UCODEIUM, Activator.FARS]:
                kwargs["uc_value"] = code.amount
            if activator_name == Activator.FARS:
                kwargs["order_id"] = code.order.id

            succ, status = await activation_func(**kwargs)

            if succ:
                logger.info(
                    f"SUCCESS: Code {code.code} activated via {activator_name}."
                )
                final_success = True
                final_status = status
                code.activator = activator_name
                await code.asave(update_fields=("activator",))

                if activator_name == Activator.FARS:
                    logger.info("FARS activation request sent. Waiting for webhook.")
                    return

                break
            else:
                logger.warning(
                    f"FAIL: Activator {activator_name} failed with status: {status}"
                )
                final_status = f"{activator_name}: {status}"
        except Exception as e:
            logger.error(
                f"Exception during activation with {activator_name}: {e}", exc_info=True
            )
            final_status = f"Exception with {activator_name}"

    await process_result(code, final_success, final_status)


async def process_result(code: UcCode, succ: bool, status: str):
    code.is_activated = True
    code.status = status
    code.is_success = succ
    await code.asave(update_fields=("is_activated", "status", "is_success"))
    text = (
        f"{'✅' if succ else '❗️'} "
        f"Activating code {code.code} {'' if succ else 'NOT'} "
        f"activated with status {status}"
    )
    logger.info(text)
    chat_id = await sync_to_async(lambda: URL_CONFIG.ADMIN_ID)()
    send_notification_task.delay(chat_id, text)

    if not succ:
        code.order.is_completed = False
        await code.order.asave(update_fields=("is_completed",))
    await check_order(code.order)


@app.task()
def activate_code_task(code: str):
    uccode = UcCode.objects.select_related("order__item", "order__tg_user").get(
        code=code
    )
    if not uccode.is_activated and uccode.order and uccode.order.pubg_id:
        logger.info(f"Got activation task! code: {code}")
        async_to_sync(activate_code)(uccode, uccode.order.pubg_id)
