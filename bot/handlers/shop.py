from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from asgiref.sync import sync_to_async
from django.conf import settings

import bot.keyboards as kb
from backend.config import TEXT_CONFIG
from bot.callbacks import FolderCD, ItemCD, MenuCD
from bot.states import OrderState
from bot.utils import asend_text_or_txt, generate_codes_text
from items.models import (
    CategoryDescription,
    DiamondItem,
    Folder,
    GiftcardItem,
    HomeVoteItem,
    Item,
    ManualCategory,
    OffersItem,
    PopularityItem,
    PUBGUCItem,
    StarItem,
    StockCodesItem,
)
from orders.models import Order
from orders.utils import get_user_zone_id
from users.models import TgUser

ENV = settings.ENV
PUBG_ID_LEN = 5

router = Router(name=__name__)


async def get_shop_text(base_text: str, category_key: str) -> str:
    shop_description = ""
    try:
        if category_key.startswith("manual_"):
            category_id = int(category_key.split("_")[1])
            manual_cat = await ManualCategory.objects.filter(id=category_id).afirst()
            if manual_cat and manual_cat.description:
                shop_description = manual_cat.description
        else:
            desc_obj = await CategoryDescription.objects.filter(
                category=category_key
            ).afirst()
            if desc_obj and desc_obj.description:
                shop_description = desc_obj.description
    except (ValueError, IndexError):
        pass

    if shop_description:
        return f"{shop_description}\n\n{base_text}"

    default_shop_info = await sync_to_async(lambda: TEXT_CONFIG.SHOP_INFO_TEXT)()
    if default_shop_info:
        return f"{default_shop_info}\n\n{base_text}"

    return base_text


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.pubg_uc))
async def get_uc_items(query: CallbackQuery, callback_data: MenuCD, state: FSMContext):
    items = await PUBGUCItem.aitems()
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text, reply_markup=await kb.get_items_inline(items)
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.stock_codes))
async def get_codes_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = [
        *(await StockCodesItem.aitems(folder__isnull=True)),
        *(await GiftcardItem.aitems(folder__isnull=True)),
    ]
    folders = [
        *(await Folder.aget(category=Item.Category.CODES)),
        *(await Folder.aget(category=Item.Category.GIFTCARD)),
    ]
    base_text = "Checkout your desired GiftCards from the list. All Cards are 1 Year Stockable🥰"
    text = await get_shop_text(base_text, category_key=callback_data.category)
    await query.message.edit_text(
        text=text,
        reply_markup=await kb.get_folders_inline(
            callback_data.category, folders, items
        ),
    )


@router.callback_query(FolderCD.filter(F.category != None))  # NOQA
async def get_folder_items(
    query: CallbackQuery, callback_data: FolderCD, state: FSMContext
):
    folder = await Folder.objects.aget(id=callback_data.id)
    items = await folder.aitems()

    back_callback = MenuCD(category="root")
    description_key = callback_data.category
    if callback_data.category == Item.Category.MORE_PUBG:
        back_callback = MenuCD(category=MenuCD.Category.pop_home)
        description_key = Item.Category.MORE_PUBG
    elif callback_data.category in [Item.Category.CODES, Item.Category.GIFTCARD]:
        back_callback = MenuCD(category=MenuCD.Category.stock_codes)
        description_key = MenuCD.Category.stock_codes

    text = await get_shop_text("Choose item", category_key=description_key)

    await query.message.edit_text(
        text=text,
        reply_markup=await kb.get_items_inline(items, callback_data=back_callback),
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.pop_home))
async def get_pop_home_root(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    await query.message.edit_text(
        text="Choose category", reply_markup=await kb.get_more_pubg_services_inline()
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.popularity))
async def get_popularity_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = await PopularityItem.aitems(folder__isnull=True)
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text,
        reply_markup=await kb.get_items_inline(
            items, callback_data=MenuCD(category=MenuCD.Category.pop_home)
        ),
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.home_vote))
async def get_home_vote_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = await HomeVoteItem.aitems(folder__isnull=True)
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text,
        reply_markup=await kb.get_items_inline(
            items,
            callback_data=MenuCD(category=MenuCD.Category.pop_home),
        ),
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.offers))
async def get_offer_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = await OffersItem.aitems()
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text, reply_markup=await kb.get_items_inline(items)
    )


@router.callback_query(MenuCD.filter(F.category.startswith("manual_")))
async def get_manual_category_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    category_id = int(callback_data.category.split("_")[1])
    items = await sync_to_async(list)(
        Item.objects.filter(manual_category_id=category_id, is_active=True)
    )
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text, reply_markup=await kb.get_items_inline(items)
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.stars))
async def get_stars_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = await StarItem.aitems()
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text, reply_markup=await kb.get_items_inline(items)
    )


@router.callback_query(MenuCD.filter(F.category == MenuCD.Category.diamond))
async def get_DiamondItem_items(
    query: CallbackQuery, callback_data: MenuCD, state: FSMContext
):
    items = await DiamondItem.aitems()
    text = await get_shop_text("Choose item", category_key=callback_data.category)
    await query.message.edit_text(
        text=text, reply_markup=await kb.get_items_inline(items)
    )


@router.callback_query(ItemCD.filter(F.action == ItemCD.Action.view))
async def get_item(query: CallbackQuery, callback_data: ItemCD, state: FSMContext):
    await state.clear()
    item = await Item.objects.select_related("manual_category").aget(
        id=callback_data.id
    )
    quantity = await item.aget_stock_amount()
    if quantity is not None and quantity < 1:
        await query.answer("Not available at the moment")
        return
    await state.update_data(callback_data.model_dump())

    if item.manual_category:
        await state.set_state(OrderState.pubg_id)
        prompt_text = item.manual_category.prompt_text
        await query.message.edit_text(
            f'"{prompt_text}" for {item.value}', reply_markup=None
        )
    elif item.category in (
        Item.Category.PUBG_UC,
        Item.Category.POPULARITY,
        Item.Category.HOME_VOTE,
        Item.Category.OFFERS,
    ):
        await state.set_state(OrderState.pubg_id)
        await query.message.edit_text(
            f'"Input your PUBG id" for {item.value}', reply_markup=None
        )
    elif item.category in (Item.Category.DIAMOND,):
        await state.set_state(OrderState.user_id)
        await query.message.edit_text(
            f'Input your "User ID" and "Zone ID" for {item.value} like this: 334882026(1017)',
            reply_markup=None,
        )
    elif item.category in (Item.Category.CODES, Item.Category.GIFTCARD):
        await state.set_state(OrderState.quantity)
        await query.message.edit_text(
            text=f"Write the quantity of {item.value}", reply_markup=None
        )
    elif item.category in (Item.Category.STARS,):
        await state.set_state(OrderState.username)
        await query.message.edit_text(
            text=f"Write your username or tap /{query.from_user.username} for {item.value} ",
            reply_markup=None,
        )


@router.callback_query(ItemCD.filter(F.action == ItemCD.Action.proceed))
async def pay_item_by_keyboard(
    query: CallbackQuery, callback_data: ItemCD, state: FSMContext
):
    item = await Item.objects.aget(id=callback_data.id)
    await create_order(state, item, query=query)


@router.message(OrderState.pubg_id)
async def get_pubg_id(message: Message, state: FSMContext):
    data = await state.get_data()
    item_id = data["id"]
    item = await Item.objects.select_related("manual_category").aget(id=item_id)

    if not item.manual_category and item.category in (
        Item.Category.PUBG_UC,
        Item.Category.POPULARITY,
        Item.Category.HOME_VOTE,
        Item.Category.OFFERS,
    ):
        if len(message.text) < PUBG_ID_LEN or not message.text.isdigit():
            text = await sync_to_async(lambda: TEXT_CONFIG.WRONG_PUBGID_MSG)()
            await message.answer(text)
            return

    await state.update_data(pubg_id=message.text)
    await state.set_state(None)
    text = f"{item.value} for total {item.get_total_price(1)} USD"
    await create_order(state, item, message=message)
    await state.set_state(None)


@router.message(OrderState.user_id)
async def get_user_id(message: Message, state: FSMContext):
    text = await sync_to_async(lambda: TEXT_CONFIG.WRONG_PUBGID_MSG)()
    try:
        user_id, zone_id = get_user_zone_id(message.text)
    except Exception:
        await message.answer(text)
        return
    if not user_id.isdigit() or not zone_id.isdigit():
        await message.answer(text)
        return
    await state.update_data(pubg_id=f"{user_id}({zone_id})")
    await state.set_state(None)
    data = await state.get_data()
    id = data["id"]
    item = await Item.objects.aget(id=id)
    text = f"{item.value} for total {item.get_total_price(1)} USD"
    await create_order(state, item, message=message)
    await state.set_state(None)


@router.message(OrderState.quantity)
async def get_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text)
    except ValueError:
        await message.answer("Try again")
        return
    if quantity < 1:
        await message.answer("Min quantity is 1")
        return
    await state.update_data(quantity=quantity)
    data = await state.get_data()
    id = data["id"]
    item = await Item.objects.aget(id=id)
    if (in_stock := await item.aget_stock_amount()) < quantity:
        await message.answer(f"Only {in_stock} {item} remains in stock")
        return
    await create_order(state, item, message=message)
    await state.set_state(None)


@router.message(OrderState.username)
async def get_username(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        username = message.text.split("/")[1]
    else:
        username = message.text
    data = await state.get_data()
    id = data["id"]
    await state.update_data(username=username)
    item = await Item.objects.aget(id=id)
    await create_order(state, item, message=message)
    await state.set_state(None)


async def create_order(
    state: FSMContext,
    item: Item,
    *,
    message: Message | None = None,
    query: CallbackQuery | None = None,
):
    tg_user = await TgUser.objects.aget(tg_id=(message or query).from_user.id)
    data = await state.get_data()
    quantity = data.get("quantity", 1)
    pubg_id = data.get("pubg_id") or data.get("username")

    price = item.price * quantity
    if price > tg_user.balance:
        text = "You do not have enough balance"
        if message:
            await message.answer(text)
        elif query:
            await query.answer(text)
        return
    order = await Order.objects.acreate(
        tg_user=tg_user,
        item=item,
        quantity=quantity,
        data=item.to_dict(),
        price=price,
        category=item.category,
        pubg_id=pubg_id,
        balance_before=tg_user.balance,
    )
    await tg_user.arefresh_from_db()
    text = f"Processing order…\n{await order.auser_str()}"
    if message:
        new_message = await message.answer(text)
    elif query:
        await query.message.edit_text(text, reply_markup=None)
        new_message = query.message
    order.message_id = new_message.message_id
    await order.asave(update_fields=("message_id",))
    text = await sync_to_async(lambda: TEXT_CONFIG.MENU_MSG)()
    if message:
        await message.answer(text, reply_markup=await kb.get_menu_inline())
    elif query:
        await query.message.answer(text, reply_markup=await kb.get_menu_inline())
    codes = await order.agrab_codes()
    bot = message.bot if message else query.bot
    if codes and len(codes) == order.quantity:
        text = generate_codes_text(codes=codes, order=order)
        if text:
            await asend_text_or_txt(
                bot, chat_id=message.from_user.id, text=text, order=order
            )
        order.is_completed = True
        await order.asave(update_fields=("is_completed",))
    if codes and len(codes) != order.quantity:
        order.is_completed = False
        await order.asave(update_fields=("is_completed",))
