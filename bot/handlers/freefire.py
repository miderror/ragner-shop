import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import bot.keyboards as kb
from bot.callbacks import FreeFireCD, MenuCD
from bot.states import FreeFireOrderState
from integrations.shop2topup import shop2topup_api
from items.models import FreeFireRegionPrice, Region
from users.models import TgUser

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.free_fire))
async def select_free_fire_region(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text(
        "Please select your region",
        reply_markup=await kb.get_free_fire_regions_keyboard(),
    )


@router.callback_query(FreeFireCD.filter(F.action == "select_region"))
async def select_free_fire_item(
    query: CallbackQuery, callback_data: FreeFireCD, state: FSMContext
):
    region = await Region.objects.aget(id=callback_data.region_id)

    text = "Choose item"
    if region.description:
        text = f"{region.description}\n\n{text}"

    await query.message.edit_text(
        text=text,
        reply_markup=await kb.get_free_fire_items_keyboard(callback_data.region_id),
    )


@router.callback_query(FreeFireCD.filter(F.action == "select_item"))
async def enter_player_id(
    query: CallbackQuery, callback_data: FreeFireCD, state: FSMContext
):
    await state.set_state(FreeFireOrderState.player_id)
    await state.update_data(
        item_id=callback_data.item_id, region_id=callback_data.region_id
    )
    await query.message.edit_text("Please enter your Player ID.")


@router.message(FreeFireOrderState.player_id)
async def confirm_purchase(message: Message, state: FSMContext):
    player_id = message.text.strip()
    if not player_id.isdigit():
        await message.answer("Invalid Player ID format. Please enter numbers only.")
        return

    data = await state.get_data()
    item_id = data["item_id"]
    region_id = data["region_id"]

    await message.answer("Checking your Player ID, please wait...")

    player_info = await shop2topup_api.get_player_info(player_id)

    if not player_info:
        await message.answer(
            "Could not find a player with this ID. Please check and try again."
        )
        return

    player_name = player_info["player_name"]
    player_region_name = player_info["region"]
    selected_region = await Region.objects.aget(id=region_id)

    if player_region_name.upper() != selected_region.name.upper():
        await message.answer(
            f"⚠️ Warning! Your account region is '{player_region_name}', "
            f"but you are trying to top up from the '{selected_region.name}' list. "
            f"Please go back and select the correct region to see the correct prices."
        )
        return

    region_price = await FreeFireRegionPrice.objects.select_related("item").aget(
        item_id=item_id, region_id=region_id
    )

    await state.update_data(
        player_id=player_id,
        player_name=player_name,
        final_price=float(region_price.final_price),
    )

    text = (
        f"Please confirm your order:\n\n"
        f"<b>Product:</b> {region_price.item.title}\n"
        f"<b>Player Name:</b> {player_name}\n"
        f"<b>Player ID:</b> {player_id}\n"
        f"<b>Region:</b> {selected_region.name}\n"
        f"<b>Total Price:</b> ${region_price.final_price}\n"
    )

    await state.set_state(FreeFireOrderState.confirmation)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=await kb.get_free_fire_confirmation_keyboard(item_id, region_id),
    )


@router.callback_query(
    FreeFireCD.filter(F.action == "confirm_purchase"), FreeFireOrderState.confirmation
)
async def process_purchase(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_user = await TgUser.objects.aget(tg_id=query.from_user.id)

    final_price = data["final_price"]

    if tg_user.balance < final_price:
        await query.message.edit_text(
            "You do not have enough balance to complete this purchase."
        )
        await state.clear()
        return

    from orders.services import create_free_fire_order

    order = await create_free_fire_order(
        tg_user=tg_user,
        item_id=data["item_id"],
        region_id=data["region_id"],
        player_id=data["player_id"],
        player_name=data["player_name"],
        price=final_price,
    )

    if order:
        await query.message.edit_text(
            f"✅ Your order #{order.id} has been accepted and is now being processed. "
            f"You will receive a notification upon completion."
        )
    else:
        await query.message.edit_text(
            "❌ An error occurred while creating your order. Please try again later or contact support."
        )

    await state.clear()


@router.callback_query(FreeFireCD.filter(F.action == "cancel"))
async def cancel_purchase(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text("Purchase cancelled.", reply_markup=None)
    await select_free_fire_region(query, state)
