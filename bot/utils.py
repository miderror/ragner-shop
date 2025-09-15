import io
import logging
from typing import TYPE_CHECKING, Union

from aiogram import Bot
from aiogram.types import BufferedInputFile
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone

from backend.settings import ENV
from codes.models import StockbleCode
from users.models import TgUser
from backend.config import PAYMENT_CONFIG

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from orders.models import Order


@sync_to_async
def get_all_admins_id() -> list:
    return list(
        TgUser.objects.filter(tg_id__isnull=False)
        .filter(is_admin=True)
        .values_list("tg_id", flat=True)
    )


def generate_codes_text(codes: list[StockbleCode], order: Union["Order", None] = None):
    if order:
        header = f"{order.item.value} x {order.quantity}"
    else:
        header = "Your codes:"

    codes_text = "\n".join([f"{code.code}" for code in codes])
    return f"{header}\n\n{codes_text}"


def generate_file(text: str, filename: str):
    file_buffer = io.BytesIO(text.encode("utf-8"))
    file_buffer.seek(0)
    return BufferedInputFile(file_buffer.read(), filename=filename)


async def send_codes_to_user(bot: Bot, chat_id: int, codes: list[StockbleCode]):
    async with Bot(ENV.str("TG_TOKEN_BOT")) as bot:
        text = "\n".join([code.code for code in codes])
        if text:
            if len(text) > 3500:
                document = generate_file(text, "codes.txt")
                await bot.send_document(
                    chat_id=chat_id, document=document, caption="There your codes"
                )
                return
            await bot.send_message(chat_id, text=f"There your codes:\n{text}")


async def asend_notification(
    chat_id: int, text: str, reply_markup=None, message_id=None
):
    async with Bot(ENV.str("TG_TOKEN_BOT")) as bot:
        if message_id:
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(f"{e}")
                logger.error(
                    f"Message {message_id} in chat {chat_id} cant be edited. Sending new"
                )
                await bot.send_message(chat_id, text=text, reply_markup=reply_markup)
        else:
            try:
                await bot.send_message(chat_id, text=text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Message has not been delivered to {chat_id}")
                logger.error(f"{e}")


@async_to_sync
async def send_notification(
    chat_id: int, text: str, reply_markup=None, message_id=None
):
    return await asend_notification(chat_id, text, reply_markup, message_id)


async def asend_text_or_txt(bot, chat_id, text, order: Union["Order", None] = None):
    if len(text) > 3500:
        filename = "codes.txt"
        if order:
            code_name = order.item.value
            quantity = order.quantity
            time_of_delivery = timezone.now().strftime("%H-%M-%S_%d-%m-%Y")
            filename = f"{code_name} x {quantity} x {time_of_delivery}.txt"
        document = generate_file(text, filename)
        await bot.send_document(
            chat_id=chat_id, document=document, caption="Codes are in file"
        )
        return
    await bot.send_message(chat_id, text=text)


async def validated_payment_amount(amount: str, currency: str):
    try:
        amount = int(amount)
    except ValueError:
        raise ValueError("Can't understand amount. Please try again.")
    if currency == 'RUB':
        ruble_comission = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_COMISSION)()
        comission = amount * (ruble_comission / 100)
        TOPUP_RUBLE_MIN = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_MIN)()
        TOPUP_RUBLE_MAX = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_MAX)()
        if not TOPUP_RUBLE_MIN < amount - comission < TOPUP_RUBLE_MAX:
            raise ValueError(
                f"Amount should be from {PAYMENT_CONFIG.TOPUP_RUBLE_MIN} to {PAYMENT_CONFIG.TOPUP_RUBLE_MAX}"
            )
    return amount
