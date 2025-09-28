from django.db import models

from backend.constants import DEFAULT_SC_AMOUNTS, DEFAULT_UC_AMOUNTS


class Activator(models.TextChoices):
    KOKOS = "kokos", "Kokos"
    FARS = "fars", "FARS"
    SMILEONE = "smileone", "SmileOne"
    UCODEIUM = "ucodeium", "UCodeium"


class ActivatorPriority(models.Model):
    name = models.CharField(
        max_length=20,
        choices=Activator.choices,
        unique=True,
        verbose_name="Activator Name",
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Priority Order",
        help_text="Lower number means higher priority (e.g., 0 is first, 1 is second).",
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    class Meta:
        verbose_name = "Activator Priority"
        verbose_name_plural = "Activator Priorities"
        ordering = ["order"]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.get_name_display()} - Priority {self.order} ({status})"


class AbstractCode(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    buying_cost = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="Buying Cost",
        null=True,
        blank=True,
        help_text="The cost price of this specific code.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updation date")

    class Meta:
        abstract = True


class UcCode(AbstractCode):
    amount = models.PositiveIntegerField(
        choices=DEFAULT_UC_AMOUNTS, verbose_name="Nominal"
    )
    status = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="API status"
    )
    is_activated = models.BooleanField(default=False, verbose_name="Is used")
    is_success = models.BooleanField(
        blank=True, null=True, verbose_name="Is activated successfully"
    )
    activator = models.CharField(
        blank=True,
        null=True,
        choices=Activator,
        verbose_name="Successful Activator",
        help_text="Filled automatically after successful activation",
    )
    is_priority_use = models.BooleanField(
        default=False,
        verbose_name="Priority Use",
        db_index=True,
        help_text="These codes will be used before regular stock.",
    )
    order = models.ForeignKey(
        "orders.Order",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="uc_codes",
        verbose_name="Order",
    )

    class Meta:
        verbose_name = "UC activating code"
        verbose_name_plural = "UC activating codes"


class StockbleCode(AbstractCode):
    amount = models.IntegerField(choices=DEFAULT_SC_AMOUNTS, verbose_name="Nominal")
    order = models.ForeignKey(
        "orders.Order",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="stockble_codes",
        verbose_name="Order",
    )

    class Meta:
        verbose_name = "PUBG STOCKBLE CODE"
        verbose_name_plural = "PUBG STOCKBLE CODES"


class Giftcard(AbstractCode):
    order = models.ForeignKey(
        "orders.Order",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="giftcard_codes",
        verbose_name="Order",
    )
    item = models.ForeignKey(
        "items.GiftcardItem",
        on_delete=models.PROTECT,
        related_name="giftcard_codes",
        verbose_name="Item in menu",
    )

    class Meta:
        verbose_name = "GIFTCARD"
        verbose_name_plural = "GIFTCARDS"
