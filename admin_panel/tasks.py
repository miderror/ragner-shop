import logging
from datetime import date

from aiogram import Bot
from asgiref.sync import sync_to_async
from django.db.models import Case, Count, DecimalField, F, Sum, When
from django.utils.timezone import now

from backend.config import URL_CONFIG
from items.models import Item
from orders.models import Order

logger = logging.getLogger(__name__)


@sync_to_async
def get_daily_summary_data(report_date: date):
    code_based_buying_cost = Sum(
        Case(
            When(category=Item.Category.PUBG_UC, then=F("uc_codes__buying_cost")),
            When(category=Item.Category.CODES, then=F("stockble_codes__buying_cost")),
            When(
                category=Item.Category.GIFTCARD, then=F("giftcard_codes__buying_cost")
            ),
            default=0,
            output_field=DecimalField(),
        )
    )
    manual_buying_cost = F("item__buying_cost") * F("quantity")

    orders = Order.objects.filter(
        created_at__date=report_date, is_completed=True
    ).annotate(
        total_buying_cost=Case(
            When(
                category__in=[
                    Item.Category.PUBG_UC,
                    Item.Category.CODES,
                    Item.Category.GIFTCARD,
                ],
                then=code_based_buying_cost,
            ),
            default=manual_buying_cost,
            output_field=DecimalField(),
        )
    )

    orders_with_profit = orders.filter(total_buying_cost__isnull=False)

    total_orders = orders.count()
    total_turnover = orders.aggregate(total=Sum("price"))["total"] or 0
    total_profit = (
        orders_with_profit.aggregate(profit=Sum(F("price") - F("total_buying_cost")))[
            "profit"
        ]
        or 0
    )

    top_products = (
        Order.objects.filter(created_at__date=report_date, is_completed=True)
        .values("item__title", "item__amount")
        .annotate(count=Count("id"))
        .order_by("-count")[:3]
    )

    return {
        "total_orders": total_orders,
        "total_turnover": total_turnover,
        "total_profit": total_profit,
        "top_products": list(top_products),
    }


async def send_daily_summary(bot: Bot):
    report_chat_id = await sync_to_async(lambda: URL_CONFIG.REPORT_CHAT_ID)()
    if not report_chat_id:
        logger.warning("REPORT_CHAT_ID is not set. Skipping daily summary.")
        return

    today = now().date()
    data = await get_daily_summary_data(today)

    top_selling_lines = []
    for product in data["top_products"]:
        title = product["item__title"]
        if not title and product["item__amount"]:
            title = f"{product['item__amount']} UC"

        top_selling_lines.append(f" • {title} → {product['count']} orders")

    top_selling_text = (
        "\n".join(top_selling_lines) if top_selling_lines else "No sales today."
    )

    message = (
        f"📊 **Daily Sales Summary – {today.strftime('%Y-%m-%d')}**\n\n"
        f"✅ **Total Orders:** {data['total_orders']}\n"
        f"💰 **Total Revenue:** ${data['total_profit']:.2f}\n"
        f"💰 **Total Turnover:** ${data['total_turnover']:.2f}\n\n"
        f"**Top-Selling Products:**\n"
        f"{top_selling_text}"
    )

    try:
        await bot.send_message(
            chat_id=report_chat_id, text=message, parse_mode="Markdown"
        )
        logger.info(f"Daily summary sent to group {report_chat_id}")
    except Exception as e:
        logger.error(f"Failed to send daily summary to group {report_chat_id}: {e}")
