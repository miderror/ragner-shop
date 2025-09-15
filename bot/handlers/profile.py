from datetime import timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone

import bot.keyboards as kb
from backend.config import FEATURES_CONFIG, PAYMENT_CONFIG
from bot.callbacks import ApiCD, HistoryCD, MenuCD, ProfileCD
from bot.states import TopUpState
from bot.utils import validated_payment_amount
from orders.models import Order, TopUp
from users.models import TgUser
from payments.payment import create_codeepay_payment

ENV = settings.ENV

router = Router(name=__name__)


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.profile))
async def get_profile(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    await query.message.edit_text(
        text="Choose category", reply_markup=await kb.get_profile_inline()
    )


@router.callback_query(ProfileCD.filter(F.category == ProfileCD.Category.HISOTORY))
async def get_history(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    # tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    # orders = await sync_to_async(lambda: list(Order.objects.filter(tg_user=tg_user)))()
    # order_text = '\n'.join([order.to_str() for order in orders])
    # await query.message.edit_text(
    #     text=f'There your orders history:\n{order_text}', reply_markup=await kb.get_history_inline()
    # )
    await query.message.edit_text(
        "Choose category", reply_markup=await kb.get_history_inline()
    )


@router.callback_query(HistoryCD.filter(F.category))
async def get_history_slice(
    query: CallbackQuery, callback_data: HistoryCD, state: FSMContext
):
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    target_date = timezone.now() - timedelta(days=callback_data.category)
    orders = await sync_to_async(
        lambda: list(Order.objects.filter(tg_user=tg_user, created_at__gte=target_date))
    )()
    paginator = Paginator(orders, 25)
    p = paginator.page(callback_data.page)
    order_text = "\n".join([order.to_str() for order in p.object_list])
    text = (
        f"There your orders history for last {callback_data.category} days:\n\n"
        f"{order_text}"
    )
    await query.message.edit_text(
        text,
        reply_markup=await kb.get_paginated_inline(
            p.has_previous(),
            p.has_next(),
            callback_data,
            back_to=ProfileCD(category=ProfileCD.Category.HISOTORY),
        ),
    )


@router.callback_query(
    ProfileCD.filter((F.category == ProfileCD.Category.POINTS) & (F.action == None))  # NOQA
)  # NOQA
async def get_points(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    if not await sync_to_async(lambda: FEATURES_CONFIG.POINTS_SYSTEM_ENABLED, thread_sensitive=True)():
        await query.answer("The points system is currently disabled.", show_alert=True)
        return
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    show_redeem = tg_user.points > tg_user.POINTS_RATIO
    await query.message.edit_text(
        text=f"You have {tg_user.points} points",
        reply_markup=await kb.get_points_inline(show_redeem),
    )


@router.callback_query(
    ProfileCD.filter((F.category == ProfileCD.Category.BALANCE) & (F.action == None))  # NOQA
)  # NOQA
async def get_balance(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    await query.message.edit_text(
        text=f"You have {tg_user.balance} USD",
        reply_markup=await kb.get_balance_inline(),
    )


@router.callback_query(ProfileCD.filter(F.action == "topup"))
async def ask_topup_amount(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    await state.set_state(TopUpState.amount)
    await query.message.edit_text("Write topup amount")


@router.message(TopUpState.amount)
async def gen_topup(message: Message, state: FSMContext):
    try:
        text = message.text.replace(",", ".")
        amount = float(text)
        if amount < 1:
            await message.answer("Min amount 1 USDT.")
            return
    except Exception:
        await message.answer("Can't understand amount. Please try again.")
        return
    topup, _ = await TopUp.objects.aget_or_create(
        tg_user=await TgUser.objects.aget(tg_id=message.from_user.id),
        amount=Decimal(str(amount)).quantize(Decimal("0.001")),
        is_paid=False,
        is_topped=False,
    )
    text = (
        f"Please topup exactly that amount: {topup.to_pay}\n"
        f"{await sync_to_async(lambda: PAYMENT_CONFIG.PAYMENT_TEXT)()}\n"
        f"<b>Valid for {await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_LIFETIME)()} minutes</b>"
    )
    await message.answer(text, parse_mode="HTML")
    await state.clear()


@router.callback_query(
    ProfileCD.filter((F.category == ProfileCD.Category.POINTS) & (F.action))
)
async def redeem_points(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    if not await sync_to_async(lambda: FEATURES_CONFIG.POINTS_SYSTEM_ENABLED, thread_sensitive=True)():
        await query.answer("The points system is currently disabled.", show_alert=True)
        return
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    res = await tg_user.aredeem_points()
    if res:
        await tg_user.arefresh_from_db()
        await query.message.edit_text(
            text=f"You have {tg_user.points} points",
            reply_markup=await kb.get_points_inline(False),
        )
        return
    await query.answer(
        f"You do not have enough points to redeem. Min amount: {tg_user.POINTS_RATIO}",
        show_alert=True,
    )


trusted_origins = settings.CSRF_TRUSTED_ORIGINS
if trusted_origins:
    base_url = trusted_origins[0]
    docs_url = f"{base_url}/api/v1/docs/"

API_INFO_TEXT = """
🚀 Public API

✅ API Documentation: [View Docs]({docs_url})
🔑 Your X-API-Key:
`{api_key}`

👆 Tap to Copy
⚠️ Do not share your API key with anyone to prevent unauthorized purchases.

✨ Need a fresh API key? Click the button below to generate a new one!
⚠️ Note: Your old API key will be invalid after regeneration.
"""


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.api))
async def show_api_key(query: CallbackQuery, state: FSMContext):
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    api_key = await tg_user.aget_or_generate_api_key()
    await query.message.edit_text(
        text=API_INFO_TEXT.format(docs_url=docs_url, api_key=api_key),
        reply_markup=await kb.get_api_management_inline(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


@router.callback_query(ApiCD.filter(F.action == "regenerate"))
async def regenerate_api_key(query: CallbackQuery, state: FSMContext):
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)
    new_api_key = await tg_user.aregenerate_api_key()
    await query.message.edit_text(
        text=API_INFO_TEXT.format(docs_url=docs_url, api_key=new_api_key),
        reply_markup=await kb.get_api_management_inline(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    await query.answer("New API Key generated!")


@router.callback_query(ProfileCD.filter(F.action == "topup_ruble"))
async def ask_topup_ruble_amount(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    await state.set_state(TopUpState.ruble_amount)
    await query.message.edit_text(
        f"Comission: {await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_COMISSION)()}%\n"
        f"Exchange rate: {await sync_to_async(lambda: PAYMENT_CONFIG.RUB_USDT_EXCHANGE_RATE)()}\n\n"
        "Write amount to topup in RUB")


@router.message(TopUpState.ruble_amount)
async def gen_rub_topup(message: Message, state: FSMContext):
    tg_user = await TgUser.objects.aget(tg_id=message.from_user.id)
    try:
        amount = await validated_payment_amount(message.text, 'RUB')
    except ValueError as e:
        await message.answer(f"{e}")
        return
    topup = await create_codeepay_payment(tg_user, amount)
    TOPUP_RUBLE_COMISSION = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_COMISSION)()
    RUB_USDT_EXCHANGE_RATE = await sync_to_async(lambda: PAYMENT_CONFIG.RUB_USDT_EXCHANGE_RATE)()
    TOPUP_LIFETIME = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_LIFETIME)()
    text = (
        '💰 <b>Сведения по оплате</b>\n'
        f'• <b>Сумма к оплате:</b> {topup.to_pay} ₽\n'
        f'• <b>Доступно для обмена:</b> {topup.amount} ₽ (включена комиссия {TOPUP_RUBLE_COMISSION}%)\n'
        f'• <b>Курс обмена:</b> 1 USDT = {RUB_USDT_EXCHANGE_RATE} ₽\n'
        f'🗳 <b>Вы получите: {topup.convert_to_ustd()} USDT</b>\n\n'

        f'🔗 <b>Для оплаты перейдите по ссылке:</b> {topup.payment_url}\n\n'

        f'⏳ <i>Ссылка действует {TOPUP_LIFETIME} минут.</i>'
    )
    await message.answer(text, parse_mode='HTML')
