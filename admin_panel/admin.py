from datetime import datetime

from django.contrib import admin
from django.db.models import Case, Count, DecimalField, F, Sum, When
from django.forms import ModelForm
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.timezone import now

from codes.models import Giftcard, StockbleCode, UcCode
from items.models import Item
from orders.models import Order

from .models import Attachment, DailyReport, Mailing, ManagerChat, ProfitReport


@admin.register(ManagerChat)
class ManagerChatAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "tg_id",
    )


class AttachmentInlineAdmin(admin.TabularInline):
    """Class to inline Attachment."""

    model = Attachment
    fields = (
        "file_type",
        "file",
        "file_id",
    )


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    inlines = (AttachmentInlineAdmin,)

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
        return super().save_form(request, form, change)


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/daily_report.html"

    def changelist_view(self, request, extra_context=None):
        context = self.admin_site.each_context(request)

        report_date_str = request.GET.get("report_date", now().strftime("%Y-%m-%d"))
        try:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        except ValueError:
            report_date = now().date()

        uc_sold_today = (
            UcCode.objects.filter(order__created_at__date=report_date)
            .values("amount")
            .annotate(count=Count("id"))
            .order_by("amount")
        )

        uc_remaining_stock = (
            UcCode.objects.filter(order__isnull=True)
            .values("amount")
            .annotate(count=Count("id"))
            .order_by("amount")
        )

        uc_added_today = (
            UcCode.objects.filter(created_at__date=report_date)
            .values("amount")
            .annotate(count=Count("id"))
            .order_by("amount")
        )

        daily_orders = (
            Order.objects.filter(
                created_at__date=report_date,
                category__in=[Item.Category.GIFTCARD, Item.Category.CODES],
            )
            .select_related("tg_user", "item")
            .order_by("tg_user__username")
        )

        sold_codes_summary = (
            daily_orders.values("item__title", "item__amount")
            .annotate(total_sold=Sum("quantity"))
            .order_by("item__title")
        )

        giftcards_added_today = (
            Giftcard.objects.filter(created_at__date=report_date)
            .values("item__title")
            .annotate(count=Count("id"))
        )

        stockblecodes_added_today = (
            StockbleCode.objects.filter(created_at__date=report_date)
            .values("amount")
            .annotate(count=Count("id"))
        )

        report_data = {
            "report_date": report_date,
            "report_date_str": report_date_str,
            "uc_sold_today": uc_sold_today,
            "uc_remaining_stock": uc_remaining_stock,
            "uc_added_today": uc_added_today,
            "daily_orders_details": daily_orders,
            "sold_codes_summary": sold_codes_summary,
            "giftcards_added_today": giftcards_added_today,
            "stockblecodes_added_today": stockblecodes_added_today,
            "title": "Daily Sales Report",
        }
        context.update(report_data)

        return TemplateResponse(request, self.change_list_template, context)


@admin.register(ProfitReport)
class ProfitReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/profit_report.html"

    def changelist_view(self, request, extra_context=None):
        context = self.admin_site.each_context(request)

        today = now().date()
        start_date_str = request.GET.get("start_date", today.strftime("%Y-%m-%d"))
        end_date_str = request.GET.get("end_date", today.strftime("%Y-%m-%d"))

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today
            end_date = today


        code_based_buying_cost = Sum(
            Case(
                When(category=Item.Category.PUBG_UC, then=F("uc_codes__buying_cost")),
                When(
                    category=Item.Category.CODES, then=F("stockble_codes__buying_cost")
                ),
                When(
                    category=Item.Category.GIFTCARD,
                    then=F("giftcard_codes__buying_cost"),
                ),
                default=0,
                output_field=DecimalField(),
            )
        )

        manual_buying_cost = F("item__buying_cost") * F("quantity")

        orders = (
            Order.objects.filter(
                created_at__date__range=[start_date, end_date],
                is_completed=True,
            )
            .annotate(
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
            .filter(
                total_buying_cost__isnull=False
            )
            .annotate(net_profit=F("price") - F("total_buying_cost"))
            .select_related("tg_user", "item")
            .order_by("-created_at")
        )

        total_profit = orders.aggregate(total=Sum("net_profit"))["total"] or 0

        report_data = {
            "title": "Profit Report",
            "start_date_str": start_date_str,
            "end_date_str": end_date_str,
            "orders_with_profit": orders,
            "total_profit": total_profit,
        }
        context.update(report_data)

        return TemplateResponse(request, self.change_list_template, context)
