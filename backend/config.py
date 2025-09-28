import logging
from enum import Enum

from django.conf import settings
from liveconfigs.models import BaseConfig

from .validators import validate_telegram_html

logger = logging.getLogger()

DESCRIPTION_SUFFIX = "_DESCRIPTION"
TAGS_SUFFIX = "_TAGS"
VALIDATORS_SUFFIX = "_VALIDATORS"


class ConfigTags(str, Enum):
    urls = "links"
    payment = "payments"
    basic = "basic"
    other = "other"
    text = "text"


class URL_CONFIG(BaseConfig):
    __topic__ = "Links configuration"

    __exported__ = [
        "DAYS",
        "FIRST_DAY_OF_WEEK",
        "TYPES_OF_LOADING",
        "USE_CALENDAR",
        "CONSOLIDATION_GROUPS",
    ]

    SITE_LINK: str = "https://www.python.org/"
    SITE_LINK_DESCRIPTION = "Настройка ссылки на сайт"
    SITE_LINK_TAGS = [ConfigTags.urls]

    BOT_URL = settings.ENV.str("BOT_URL")
    BOT_URL_DESCRIPTION = "LINK to this bot"
    BOT_URL_LINK_TAGS = [ConfigTags.urls]

    ADMIN_ID: int = settings.ENV.int("ADMIN_ID")
    ADMIN_ID_DESCRIPTION = "ADMIN_ID for notifications"
    ADMIN_ID_LINK_TAGS = [ConfigTags.urls]

    ADMIN_USERNAME: str = settings.ENV.str("ADMIN_USERNAME", "")
    ADMIN_USERNAME_DESCRIPTION = "ADMIN_USERNAME for notifications"
    ADMIN_USERNAME_LINK_TAGS = [ConfigTags.urls]

    REPORT_CHAT_ID: int = settings.ENV.int("REPORT_CHAT_ID", 0)
    REPORT_CHAT_ID_DESCRIPTION = "Telegram Chat ID for sending daily summary reports"
    REPORT_CHAT_ID_LINK_TAGS = [ConfigTags.other]


class TEXT_CONFIG(BaseConfig):
    __topic__ = "Text configurations"

    HI_MSG: str = "Welcome To RAGNER GIFTCARD BOT"
    HI_MSG_DESCRIPTION = "Welcome message"
    HI_MSG_TAGS = [ConfigTags.text]

    MENU_MSG: str = "Menu"
    MENU_MSG_DESCRIPTION = "Welcome message"
    MENU_MSG_TAGS = [ConfigTags.text]

    WRONG_PUBGID_MSG: str = "Not valid ID format"
    WRONG_PUBGID_MSG_DESCRIPTION = "Not valid ID format"
    WRONG_PUBGID_MSG_TAGS = [ConfigTags.text]

    SHOP_INFO_TEXT: str = (
        "🕑 Working hours: 10:00 AM - 10:00 PM (GMT+3)\n"
        "ℹ️ Please review your order details carefully before payment."
    )
    SHOP_INFO_TEXT_DESCRIPTION = "Description text shown in all item selection menus."
    SHOP_INFO_TEXT_TAGS = [ConfigTags.text]


class BUTT_CONFIG(BaseConfig):
    __topic__ = "Button text configuration"

    BACK: str = "Back"
    BACK_DESCRIPTION = "Back button text"
    BACK_TAGS = [ConfigTags.text]

    TOPUP: str = "TOPUP"
    TOPUP_DESCRIPTION = "TOPUP button text"
    TOPUP_TAGS = [ConfigTags.text]

    TOPUP_RUBLE: str = "TOPUP RUBLE"
    TOPUP_RUBLE_DESCRIPTION = "TOPUP RUBLE button text"
    TOPUP_RUBLE_TAGS = [ConfigTags.text]


class PAYMENT_CONFIG(BaseConfig):
    __topic__ = "Payment configuration"

    TOPUP_COMISSION: float = 1.000
    TOPUP_COMISSION_DESCRIPTION = "Min topup comission (max 3 digits after point)"
    TOPUP_COMISSION_TAGS = [ConfigTags.payment]

    TOPUP_LIFETIME: int = 20
    TOPUP_LIFETIME_DESCRIPTION = "Topup lifetime in minutes"
    TOPUP_LIFETIME_TAGS = [ConfigTags.payment]

    PAYMENT_TEXT: str = (
        "Bybit\n\n"
        "UID: <code>000000000</code>\n"
        "TRC20: <code>TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT</code>\n"
        "BEP20: <code>0x000000000000000000000000000000</code>\n"
        "APTOS: <code>0x111111111111111111111111111111</code>\n"
    )
    PAYMENT_TEXT_DESCRIPTION = "Text with payment credentials"
    PAYMENT_TEXT_TAGS = [ConfigTags.payment]
    PAYMENT_TEXT_VALIDATORS = [validate_telegram_html]

    TOPUP_RUBLE_COMISSION: float = 1.000
    TOPUP_RUBLE_COMISSION_DESCRIPTION = "Ruble topup comission in % (max 3 digits after point)"
    TOPUP_RUBLE_COMISSION_TAGS = [ConfigTags.payment]

    RUB_USDT_EXCHANGE_RATE: float = 84.63
    RUB_USDT_EXCHANGE_RATE_DESCRIPTION = "Ruble topup comission in % (max 3 digits after point)"
    RUB_USDT_EXCHANGE_RATE_TAGS = [ConfigTags.payment]

    TOPUP_RUBLE_MIN: int = 50
    TOPUP_RUBLE_MIN_DESCRIPTION = "Ruble topup min sum"
    TOPUP_RUBLE_MIN_TAGS = [ConfigTags.payment]

    TOPUP_RUBLE_MAX: int = 85_000
    TOPUP_RUBLE_MAX_DESCRIPTION = "Ruble topup max sum"
    TOPUP_RUBLE_MAX_TAGS = [ConfigTags.payment]


class FEATURES_CONFIG(BaseConfig):
    __topic__ = "Feature Flags"

    POINTS_SYSTEM_ENABLED: bool = True
    POINTS_SYSTEM_ENABLED_DESCRIPTION = (
        "Enable (True) or disable (False) the user points system."
    )
    POINTS_SYSTEM_ENABLED_TAGS = [ConfigTags.basic]
