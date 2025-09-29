from enum import IntEnum, StrEnum

from aiogram.filters.callback_data import CallbackData


class MenuCD(CallbackData, prefix="men"):
    class Category(StrEnum):
        pubg_uc = "pubg_uc"
        stock_codes = "codes"
        pop_home = "pop_home"
        popularity = "popularity"
        home_vote = "home_vote"
        offers = "offers"
        profile = "profile"
        stars = "stars"
        diamond = "diamond"
        api = "api"
        free_fire = "free_fire"

    category: str


class ProfileCD(CallbackData, prefix="pro"):
    class Category(StrEnum):
        HISOTORY = "hisotory"
        POINTS = "points"
        BALANCE = "balance"

    category: Category
    action: str | None = None


class ItemCD(CallbackData, prefix="itm"):
    class Action(StrEnum):
        view = "view"
        proceed = "proceed"

    category: str
    id: int
    action: str


class OrderCD(CallbackData, prefix="ordr"):
    class Action(StrEnum):
        complete = "complete"
        cancel = "cancel"

    id: int
    action: Action


class HistoryCD(CallbackData, prefix="hstr"):
    class Category(IntEnum):
        DAY = 1
        WEEK = 7
        MONTH = 30

    category: Category
    page: int = 1


class FolderCD(CallbackData, prefix="fldr"):
    id: int
    category: str


class ApiCD(CallbackData, prefix="api"):
    action: str


class FreeFireCD(CallbackData, prefix="ff"):
    action: str
    region_id: int | None = None
    item_id: int | None = None
