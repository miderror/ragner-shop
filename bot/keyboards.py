import copy
import typing
from enum import StrEnum

from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async

from backend.config import BUTT_CONFIG, FEATURES_CONFIG
from items.models import (
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
)

from .callbacks import ApiCD, FolderCD, HistoryCD, ItemCD, MenuCD, OrderCD, ProfileCD


async def get_menu_inline():
    markup = InlineKeyboardBuilder()
    if await PUBGUCItem.ahave_active_items():
        markup.button(
            text="PUBG UC", callback_data=MenuCD(category=MenuCD.Category.pubg_uc)
        )
    if await GiftcardItem.ahave_active_items():
        markup.button(
            text="GIFTCARDS & CODES",
            callback_data=MenuCD(category=MenuCD.Category.stock_codes),
        )
    if (
        await PopularityItem.ahave_active_items()
        or await HomeVoteItem.ahave_active_items()
    ):
        markup.button(
            text="More PUBG Services",
            callback_data=MenuCD(category=MenuCD.Category.pop_home),
        )
    if await OffersItem.ahave_active_items():
        markup.button(
            text="Offers", callback_data=MenuCD(category=MenuCD.Category.offers)
        )

    manual_categories = await sync_to_async(list)(
        ManualCategory.objects.filter(is_active=True)
    )
    for cat in manual_categories:
        markup.button(text=cat.name, callback_data=MenuCD(category=f"manual_{cat.id}"))
    if await StarItem.ahave_active_items():
        markup.button(
            text="Telegram stars", callback_data=MenuCD(category=MenuCD.Category.stars)
        )
    if await DiamondItem.ahave_active_items():
        markup.button(
            text="MLBB Russia", callback_data=MenuCD(category=MenuCD.Category.diamond)
        )
    markup.button(
        text="Profile", callback_data=MenuCD(category=MenuCD.Category.profile)
    )
    markup.button(text="🔐 API", callback_data=MenuCD(category=MenuCD.Category.api))
    markup.adjust(1, 2, 2)
    return markup.as_markup()


async def get_back_inline(callback_data):
    markup = InlineKeyboardBuilder()
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=callback_data,
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_more_pubg_services_inline():
    markup = InlineKeyboardBuilder()
    if await PopularityItem.ahave_active_items():
        markup.button(
            text="Popularity", callback_data=MenuCD(category=MenuCD.Category.popularity)
        )
    if await HomeVoteItem.ahave_active_items():
        markup.button(
            text="Home Vote", callback_data=MenuCD(category=MenuCD.Category.home_vote)
        )
    new_folders = await Folder.aget(category=Item.Category.MORE_PUBG)
    for folder in new_folders:
        markup.button(
            text=folder.title,
            callback_data=FolderCD(id=folder.id, category=Item.Category.MORE_PUBG),
        )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category="root"),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_items_inline(items: list[Item], callback_data=MenuCD(category="root")):
    markup = InlineKeyboardBuilder()
    for item in items:
        amount = await item.aget_stock_amount()
        text = f"{item} {'| ' + str(amount) + ' items' if amount is not None else ''}"
        markup.button(
            text=text,
            callback_data=ItemCD(
                category=item.category, id=item.id, action=ItemCD.Action.view
            ),
        )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=callback_data,
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_profile_inline():
    markup = InlineKeyboardBuilder()
    markup.button(
        text="HISTORY", callback_data=ProfileCD(category=ProfileCD.Category.HISOTORY)
    )
    if await sync_to_async(lambda: FEATURES_CONFIG.POINTS_SYSTEM_ENABLED, thread_sensitive=True)():
        markup.button(
            text="POINTS", callback_data=ProfileCD(category=ProfileCD.Category.POINTS)
        )
    markup.button(
        text="BALANCE", callback_data=ProfileCD(category=ProfileCD.Category.BALANCE)
    )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category="root"),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_balance_inline():
    markup = InlineKeyboardBuilder()
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.TOPUP)(),
        callback_data=ProfileCD(category=ProfileCD.Category.BALANCE, action="topup"),
    )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.TOPUP_RUBLE)(),
        callback_data=ProfileCD(category=ProfileCD.Category.BALANCE, action="topup_ruble"),
    )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category=MenuCD.Category.profile),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_points_inline(show_redeem: bool = True):
    markup = InlineKeyboardBuilder()
    if show_redeem:
        markup.button(
            text="Redeem points",
            callback_data=ProfileCD(
                category=ProfileCD.Category.POINTS, action="redeem"
            ),
        )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category=MenuCD.Category.profile),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_order_inline(category: str, id: int):
    markup = InlineKeyboardBuilder()
    markup.button(
        text="Pay",
        callback_data=ItemCD(category=category, id=id, action=ItemCD.Action.proceed),
    )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category=category),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


def make_order_comleted(id: int):
    markup = InlineKeyboardBuilder()
    markup.button(
        text="Complete", callback_data=OrderCD(id=id, action=OrderCD.Action.complete)
    )
    markup.button(
        text="Cancel", callback_data=OrderCD(id=id, action=OrderCD.Action.cancel)
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


class KEYBOARDS(StrEnum):
    MAKE_ORDER_COMLETED = "MAKE_ORDER_COMLETED"

    @classmethod
    def get_func(cls, key) -> typing.Callable:
        return {
            "MAKE_ORDER_COMLETED": make_order_comleted,
        }[key]


async def get_history_inline():
    markup = InlineKeyboardBuilder()
    for cat in HistoryCD.Category:
        markup.button(text=f"{cat} days", callback_data=HistoryCD(category=cat))
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category=MenuCD.Category.profile),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_paginated_inline(
    has_previous: bool, has_next: bool, callback_data: HistoryCD, back_to
):
    markup = InlineKeyboardBuilder()
    if has_previous or has_next:
        if has_previous:
            prev_cb = copy.deepcopy(callback_data)
            prev_cb.page -= 1
            markup.button(text="<", callback_data=prev_cb)
        else:
            markup.button(text=" ", callback_data="blabla")
        if has_next:
            next_cb = copy.deepcopy(callback_data)
            next_cb.page += 1
            markup.button(text=">", callback_data=next_cb)
        else:
            markup.button(text=" ", callback_data="blabla")
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(), callback_data=back_to
    )
    markup.adjust(2, repeat=True)
    return markup.as_markup()


async def get_folders_inline(category: str, folders: list[Folder], items: list[Item]):
    markup = InlineKeyboardBuilder()
    for folder in folders:
        markup.button(
            text=folder.title, callback_data=FolderCD(id=folder.id, category=category)
        )
    for item in items:
        amount = await item.aget_stock_amount()
        text = f"{item} {'| ' + str(amount) + ' items' if amount is not None else ''}"
        markup.button(
            text=text,
            callback_data=ItemCD(
                category=item.category, id=item.id, action=ItemCD.Action.view
            ),
        )
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category="root"),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


async def get_api_management_inline():
    markup = InlineKeyboardBuilder()
    markup.button(text="🔁 Generate New Key", callback_data=ApiCD(action="regenerate"))
    markup.button(
        text=await sync_to_async(lambda: BUTT_CONFIG.BACK)(),
        callback_data=MenuCD(category="root"),
    )
    markup.adjust(1)
    return markup.as_markup()
