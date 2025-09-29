import logging
from collections import Counter
from decimal import Decimal
from enum import StrEnum

from asgiref.sync import sync_to_async
from django.db import models, transaction
from django.db.models import Count
from django.utils import timezone

from backend.config import PAYMENT_CONFIG
from backend.constants import CODES_MAP, UC_RECIPES
from bot.tasks import send_notification_task
from codes.models import StockbleCode, UcCode
from items.models import Item
from users.models import TgUser

logger = logging.getLogger(__name__)


class Order(models.Model):
    class Status(StrEnum):
        PENDING = "Pending"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"
        FAILED = "Failed"

    tg_user = models.ForeignKey(
        TgUser, on_delete=models.CASCADE, verbose_name="TG USER"
    )
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name="Item")
    quantity = models.PositiveSmallIntegerField(verbose_name="Quantity")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updation date")
    data = models.JSONField(verbose_name="Item data")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    category = models.CharField(choices=Item.Category, verbose_name="Category")
    pubg_id = models.CharField(
        blank=True, null=True, max_length=50, verbose_name="PUBG id"
    )
    player_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Player Name"
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Provider Transaction ID",
    )
    is_completed = models.BooleanField(
        blank=True, null=True, verbose_name="Completed/Failed"
    )
    message_id = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Message id"
    )
    balance_before = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Balance before order"
    )
    _status = None

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ("created_at",)

    @property
    def title(self):
        if self.category == Item.Category.PUBG_UC:
            return f"PUBG_UC_{self.data.get('amount')}_{self.id}"
        if self.category == Item.Category.CODES:
            return f"PUBG_UC_{self.data.get('amount')}_{self.id}"
        return f"{self.data.get('value')}_{self.id}"

    def __str__(self):
        return (
            f"{self.id}.{self.data.get('price')} USDT "
            f"{self.data.get('value')} "
            f"x{self.quantity} "
            f"{self.data.get('category')} "
        )

    def to_str(self):
        quantity_str = f"{self.quantity}\n" if self.quantity > 1 else None
        pubg_id_str = f"PUBG ID: {self.pubg_id}\n" if self.pubg_id else None
        return (
            f"Order #{self.id}\n"
            f"{Item.Category(self.category).label}\n"
            f"{self.data.get('value')}\n"
            f"{pubg_id_str or ''}"
            f"{quantity_str or ''}"
            f"Total: {self.price}$\n"
            f"Complete: {'✅' if self.is_completed else '❌'}\n"
        )

    async def ato_str(self):
        return await sync_to_async(self.to_str)()

    def user_str(self):
        status = {
            self.__class__.Status.PENDING: "",
            self.__class__.Status.COMPLETED: "completed ✅",
            self.__class__.Status.CANCELLED: "cancelled ❌",
            self.__class__.Status.FAILED: "failed ❌",
        }.get(self.status, "unknown")
        completed = f"Order {status}\n"

        player_id_label = "PUBG ID"
        if self.item.category == Item.Category.STARS:
            player_id_label = "USERNAME"
        elif self.item.category == Item.Category.DIAMOND:
            player_id_label = "USERID"
        elif self.item.category == Item.Category.FREE_FIRE:
            player_id_label = "Player ID"

        player_id_str = f"{player_id_label}: {self.pubg_id}\n" if self.pubg_id else ""

        codes = (
            f"Code USED: {' '.join([code.code for code in self.uc_codes.all()])}\n"
            if self.uc_codes.all()
            else ""
        )

        return (
            f"{completed}"
            f"{self.title}\n"
            f"{player_id_str}"
            f"Balance before order: {self.balance_before}$\n"
            f"Order Cost: {self.price}$\n"
            f"Balance after Order: {self.balance_before - self.price.quantize(Decimal('0.01'))}$\n"
            f"{codes}"
        )

    async def auser_str(self):
        return await sync_to_async(self.user_str)()

    def admin_str(self):
        codes = (
            f"Code USED: {' '.join([code.code for code in self.uc_codes.all()])}\n"
            if self.uc_codes.all()
            else ""
        )

        player_id_label = "PUBG ID"
        if self.item.category == Item.Category.STARS:
            player_id_label = "USERNAME"
        elif self.item.category == Item.Category.DIAMOND:
            player_id_label = "USERID"
        elif self.item.category == Item.Category.FREE_FIRE:
            player_id_label = "Player ID"

        player_id_str = f"{player_id_label}: {self.pubg_id}\n" if self.pubg_id else ""

        return (
            f"userid: {self.tg_user.tg_id}\n"
            f"Order: {self.title}\n"
            f"{player_id_str}"
            f"Balance before order: {self.balance_before}$\n"
            f"Order Cost: {self.price}$\n"
            f"Balance after Order: {self.balance_before - self.price.quantize(Decimal('0.01'))}$\n"
            f"{codes}"
        )

    async def aadmin_str(self):
        return await sync_to_async(self.user_str)()

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.id:
            self.tg_user.process_payment(amount=(-self.price))
        return super().save(force_insert, force_update, using, update_fields)

    def grab_code(self):
        codes_count = self.stockble_codes.count()
        if self.stockble_codes and codes_count == self.quantity:
            return list(self.stockble_codes.all())
        codes = StockbleCode.objects.filter(amount=self.item.amount)[
            : (self.quantity - codes_count)
        ]
        for code in codes:
            code.order = self
            code.save(update_fields=("order",))
        return list(self.stockble_codes.all())

    def get_code_nominals(self):
        if self.category != Item.Category.PUBG_UC:
            raise ValueError("Order category must be PUBG_UC")

        target_amount = self.item.amount

        if target_amount not in UC_RECIPES:
            return CODES_MAP.get(target_amount)

        recipes = UC_RECIPES.get(target_amount, [])
        if not recipes:
            return None

        all_possible_components = {comp for recipe in recipes for comp in recipe}
        available_codes_counts = {
            item["amount"]: item["count"]
            for item in UcCode.objects.filter(
                order__isnull=True, amount__in=all_possible_components
            )
            .values("amount")
            .annotate(count=Count("id"))
        }

        for recipe in recipes:
            recipe_requirements = Counter(recipe)
            is_viable = True
            for component, required_count in recipe_requirements.items():
                if (
                    available_codes_counts.get(component, 0)
                    < required_count * self.quantity
                ):
                    is_viable = False
                    break

            if is_viable:
                logger.info(f"Для заказа #{self.id} выбран рецепт: {recipe}")
                return recipe

        logger.warning(
            f"Для заказа #{self.id} не найдено ни одного выполнимого рецепта."
        )
        return None

    def grab_uc(self):
        codes_sum = self.uc_codes.aggregate(models.Sum("amount"))["amount__sum"] or 0
        if codes_sum >= self.item.amount * self.quantity:
            return
        nominals = self.get_code_nominals()

        if not nominals:
            text = f"Not enough codes for item {self.item.amount} to fulfill order #{self.id}"
            logger.error(text)
            self.send_manager_notification(text)
            self.is_completed = False
            self.save(update_fields=["is_completed"])
            return

        logger.info(f"Резервируем коды для заказа #{self.id} по рецепту {nominals}")

        try:
            with transaction.atomic():
                for _ in range(self.quantity):
                    for nom in nominals:
                        code = (
                            UcCode.objects.select_for_update()
                            .filter(amount=nom, is_activated=False, order__isnull=True)
                            .order_by("-is_priority_use", "created_at")
                            .first()
                        )

                        if code:
                            code.order = self
                            code.save(update_fields=("order",))
                        else:
                            raise Exception(
                                f"Race condition: Not enough codes of amount {nom} for order #{self.id}"
                            )
        except Exception as e:
            logger.error(f"Ошибка при резервировании кодов для заказа #{self.id}: {e}")
            self.send_manager_notification(
                f"Critical error grabbing codes for order #{self.id}. Please check stock. Error: {e}"
            )
            self.is_completed = False
            self.save(update_fields=["is_completed"])

    def grab_giftcard(self):
        codes = self.item.giftcard_codes.filter(order__isnull=True)[: self.quantity]
        for code in codes:
            code.order = self
            code.save()
        return codes

    def grab_codes(self):
        if self.item.category == Item.Category.CODES:
            return self.grab_code()
        if self.item.category == Item.Category.PUBG_UC:
            return self.grab_uc()
        if self.item.category == Item.Category.GIFTCARD:
            return self.grab_giftcard()

    async def agrab_codes(self):
        return await sync_to_async(self.grab_codes)()

    def send_manager_notification(
        self, text, keyboard: str | None = None, kwargs: dict | None = None
    ):
        if chat := self.item.chat:
            send_notification_task.delay(
                chat.tg_id, text, keyboard, kwargs={"id": self.id}
            )
        else:
            logger.warning(f"There no chat for Item {self.item.value}")

    def cancel(self):
        if self.is_completed is not None:
            logger.error(
                f"Order {self.id} can`t be cancelled! Because has alreary have status `{self.status}`"
            )
            return
        self._status = self.Status.CANCELLED
        with transaction.atomic():
            self.tg_user.process_payment(amount=self.price)
            self.__class__.objects.filter(id=self.id).update(is_completed=False)
        self.refresh_from_db()
        send_notification_task(self.tg_user.tg_id, text=self.user_str())

    async def acancel(self):
        return await sync_to_async(self.cancel)()

    @property
    def status(self):
        if self._status:
            return self._status
        if self.is_completed is None:
            return self.__class__.Status.PENDING
        return (
            self.__class__.Status.COMPLETED
            if self.is_completed
            else self.__class__.Status.FAILED
        )


class TopUp(models.Model):
    class Currency(models.TextChoices):
        USDT = "USDT", "USDT"
        RUB = "RUB", "RUB"

    tg_user = models.ForeignKey(
        TgUser, on_delete=models.CASCADE, verbose_name="TG USER"
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="Amount to topup"
    )
    comission = models.DecimalField(
        blank=True, max_digits=10, decimal_places=3, verbose_name="Comission"
    )
    to_pay = models.DecimalField(
        blank=True, max_digits=10, decimal_places=3, verbose_name="Total to pay"
    )
    tx_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="txId")
    is_paid = models.BooleanField(default=False, verbose_name="Paid")
    is_topped = models.BooleanField(default=False, verbose_name="Topped")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updation date")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="Paid at")
    payment_url = models.URLField(blank=True, null=True, verbose_name="Payment URL")
    currency = models.CharField(
        max_length=10, choices=Currency, default=Currency.USDT, verbose_name="Currency"
    )

    class Meta:
        verbose_name = "TopUp"
        verbose_name_plural = "TopUps"
        ordering = ("-id",)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.comission or not self.to_pay:
            self.generate_comission()
        if self.is_paid and not self.paid_at:
            self.paid_at = timezone.now()
        return super().save(force_insert, force_update, using, update_fields)

    def generate_comission(self, start: float = 0.001):
        comission = start + PAYMENT_CONFIG.TOPUP_COMISSION
        to_pay = Decimal(str(comission)) + self.amount
        if TopUp.objects.filter(to_pay=to_pay, is_paid=False).exists():
            start = start + 0.001
            return self.generate_comission(start)
        self.comission = comission
        self.to_pay = to_pay

    def convert_to_ustd(self) -> Decimal | None:
        if self.currency == self.Currency.RUB:
            return (
                Decimal(str(self.amount))
                / Decimal(str(PAYMENT_CONFIG.RUB_USDT_EXCHANGE_RATE))
            ).quantize(Decimal("0.01"))
        if self.currency == self.Currency.USDT:
            return self.amount
        return None

    def top(self):
        if self.is_topped:
            return
        if self.currency == self.Currency.RUB:
            amount = self.convert_to_ustd()
        elif self.currency == self.Currency.USDT:
            amount = self.amount
        self.tg_user.process_payment(amount)
        self.is_topped = True
        self.save(update_fields=("is_topped",))

    async def atop(self):
        return await sync_to_async(self.top)()
