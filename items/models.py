from collections import Counter

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import Count

from admin_panel.models import ManagerChat
from backend.constants import CODES_MAP, DEFAULT_UC_AMOUNTS, UC_RECIPES
from codes.models import Activator, StockbleCode, UcCode


class ManualCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name="Button Name")
    prompt_text = models.CharField(
        max_length=255,
        verbose_name="Player ID Prompt",
        help_text='e.g., "Input your PUBG ID" or "Enter your Riot ID (Name#Tag)"',
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="This text will be shown at the top of this category menu.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active?")
    ordering = models.PositiveSmallIntegerField(default=100, verbose_name="Ordering")

    class Meta:
        verbose_name = "Manual Order Category"
        verbose_name_plural = "Manual Order Categories"
        ordering = ["ordering"]

    def __str__(self):
        return self.name


class Item(models.Model):
    class Category(models.TextChoices):
        PUBG_UC = "pubg_uc", "PUBG UC"
        CODES = "codes", "GIFTCARDS & CODES"
        POPULARITY = "popularity", "Popularity"
        HOME_VOTE = "home_vote", "HOME VOTE"
        OFFERS = "offers", "Offers"
        GIFTCARD = "giftcard", "Giftcard"
        STARS = "stars", "Telegram Stars"
        DIAMOND = "diamond", "Mobilelegends diamond"
        MORE_PUBG = "more_pubg", "More PUBG Services"

    title = models.CharField(
        blank=True,
        null=True,
        verbose_name="Title",
        help_text="Not obligatory. Has priority in the display in the menu",
    )
    category = models.CharField(
        blank=True, max_length=50, choices=Category, verbose_name="Category"
    )
    price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Price")
    amount = models.IntegerField(
        blank=True,
        null=True,
        choices=DEFAULT_UC_AMOUNTS,
        verbose_name="Amount",
        help_text="For codes and popularity",
    )
    is_active = models.BooleanField(default=False, verbose_name="Active?")
    activator = models.CharField(
        blank=True,
        null=True,
        choices=Activator,
        verbose_name="Activator",
        help_text="if not selected, then manual activation",
    )
    data = models.JSONField(blank=True, null=True, verbose_name="Additional data")
    chat = models.ForeignKey(
        ManagerChat,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="items",
        verbose_name="Chat for notifications",
    )
    manual_category = models.ForeignKey(
        "ManualCategory",
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Manual Category",
        blank=True,
        null=True,
        help_text="Select only for manual order items",
    )
    folder = models.ForeignKey(
        "Folder",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="items",
        verbose_name="Folder",
    )
    serial_number = models.PositiveIntegerField(
        default=100,
        verbose_name="Serial Number",
        help_text="Used for sorting items in the bot. Lower number comes first.",
    )

    class Meta:
        ordering = [
            "serial_number",
            "price",
            "title",
        ]

    def __str__(self) -> str:
        return f"{self.value} | {self.price}$"

    @classmethod
    def items(cls, **kwargs):
        return cls.objects.filter(is_active=True, **kwargs)

    @classmethod
    async def aitems(cls, **kwargs):
        return await sync_to_async(lambda: list(cls.items(**kwargs)))()

    @classmethod
    def have_active_items(cls):
        return cls.items().exists()

    @classmethod
    async def ahave_active_items(cls):
        return await sync_to_async(cls.have_active_items)()

    @property
    def value(self):
        if self.category == Item.Category.PUBG_UC:
            return self.title or f"{self.amount} UC"
        if self.category == Item.Category.CODES:
            return self.title or f"{self.amount} UC"
        if self.category == Item.Category.POPULARITY:
            return self.title or f"{self.amount} Popularity"
        return f"{self.title}"

    def to_dict(self):
        return {
            "title": self.title,
            "value": self.value,
            "category": self.category,
            "price": str(self.price),
            "amount": self.amount,
            "is_active": self.is_active,
            "activator": self.activator,
        }

    def get_total_price(self, quantity: int):
        return self.price * quantity

    def get_stock_amount(self):
        if self.category == Item.Category.CODES:
            return StockbleCode.objects.filter(
                amount=self.amount, order__isnull=True
            ).count()
        if self.category == Item.Category.GIFTCARD:
            return self.giftcard_codes.filter(order__isnull=True).count()
        if self.category == Item.Category.PUBG_UC:
            if self.amount not in UC_RECIPES:
                nominals = CODES_MAP.get(self.amount)
                if not nominals:
                    return 0

                counter = []
                for nom in set(nominals):
                    available_codes = UcCode.objects.filter(
                        order__isnull=True,
                        amount=nom,
                    ).count()

                    possible_items = available_codes // nominals.count(nom)
                    counter.append(possible_items)

                return min(counter) if counter else 0

            recipes = UC_RECIPES.get(self.amount, [])
            if not recipes:
                return 0

            all_possible_components = {
                component for recipe in recipes for component in recipe
            }
            available_codes_counts = {
                item["amount"]: item["count"]
                for item in UcCode.objects.filter(
                    order__isnull=True, amount__in=all_possible_components
                )
                .values("amount")
                .annotate(count=Count("id"))
            }

            direct_recipe = [self.amount]
            if direct_recipe in recipes:
                direct_codes_count = available_codes_counts.get(self.amount, 0)
                if direct_codes_count > 0:
                    return direct_codes_count

            for recipe in recipes:
                if recipe == [self.amount]:
                    continue

                recipe_requirements = Counter(recipe)
                possible_builds = []
                can_build = True
                for component, required_count in recipe_requirements.items():
                    available_count = available_codes_counts.get(component, 0)
                    if available_count < required_count:
                        can_build = False
                        break
                    possible_builds.append(available_count // required_count)

                if can_build and possible_builds:
                    return min(possible_builds)

            return 0
        return None

    async def aget_stock_amount(self):
        return await sync_to_async(self.get_stock_amount)()


class CategoryDescription(models.Model):
    category = models.CharField(
        max_length=50,
        choices=Item.Category.choices,
        unique=True,
        verbose_name="Category",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="This text will be shown at the top of the selected category menu.",
    )

    class Meta:
        verbose_name = "Category Description"
        verbose_name_plural = "Category Descriptions"

    def __str__(self):
        return self.get_category_display()


class PUBGUCItem(Item):
    class Meta:
        proxy = True
        verbose_name = "PUBG UC"
        verbose_name_plural = "PUBG UC Items"

    def __str__(self) -> str:
        return f"{self.value} | {self.price}$"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.PUBG_UC, **kwargs)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.PUBG_UC
        return super().save(force_insert, force_update, using, update_fields)


class StockCodesItem(Item):
    class Meta:
        proxy = True
        verbose_name = "STOCKBLE CODES"
        verbose_name_plural = "STOCKBLE CODES"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.CODES, **kwargs).order_by("amount")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.CODES
        return super().save(force_insert, force_update, using, update_fields)


class GiftcardItem(Item):
    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.GIFTCARD
        return super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.GIFTCARD, **kwargs)

    class Meta:
        proxy = True
        verbose_name = "Giftcards item"
        verbose_name_plural = "Giftcards items"


class PopularityItem(Item):
    class Meta:
        proxy = True
        verbose_name = "Popularity"
        verbose_name_plural = "Popularity Items"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.POPULARITY, **kwargs)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.POPULARITY
        return super().save(force_insert, force_update, using, update_fields)


class HomeVoteItem(Item):
    class Meta:
        proxy = True
        verbose_name = "HOME VOTE"
        verbose_name_plural = "HOME VOTE Items"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.HOME_VOTE, **kwargs)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.HOME_VOTE
        return super().save(force_insert, force_update, using, update_fields)


class OffersItem(Item):
    class Meta:
        proxy = True
        verbose_name = "Offer"
        verbose_name_plural = "Offers Items"

    @classmethod
    def items(cls, **kwargs):
        return super().items(
            category=cls.Category.OFFERS, manual_category__isnull=True, **kwargs
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.OFFERS
        return super().save(force_insert, force_update, using, update_fields)


class StarItem(Item):
    class Meta:
        proxy = True
        verbose_name = "Star"
        verbose_name_plural = "Star Items"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.STARS, **kwargs)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.STARS
        return super().save(force_insert, force_update, using, update_fields)


class DiamondItem(Item):
    class Meta:
        proxy = True
        verbose_name = "MLBB Russia"
        verbose_name_plural = "MLBB Russia"

    @classmethod
    def items(cls, **kwargs):
        return super().items(category=cls.Category.DIAMOND, **kwargs)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.category = Item.Category.DIAMOND
        return super().save(force_insert, force_update, using, update_fields)


class Folder(models.Model):
    category = models.CharField(
        blank=True,
        max_length=50,
        choices=Item.Category,
        verbose_name="Category",
    )
    title = models.CharField(max_length=35, verbose_name="Title")
    ordering_id = models.SmallIntegerField(
        blank=True, null=True, verbose_name="Ordering num"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Custom Description",
        help_text="Optional. If set, this will be shown inside this folder in the bot."
    )

    def aitems(self, **kwargs):
        return sync_to_async(lambda: list(self.items.filter(**kwargs)))()

    @classmethod
    def get(cls, **kwargs):
        return cls.objects.filter(**kwargs)

    @classmethod
    async def aget(cls, **kwargs):
        return await sync_to_async(lambda: list(cls.get(**kwargs)))()

    class Meta:
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
        ordering = [
            "ordering_id",
            "category",
            "id",
        ]

    def __str__(self) -> str:
        return f"{Item.Category(self.category).label} | {self.title}"


class ManualItem(Item):
    class Meta:
        proxy = True
        verbose_name = "Manual Order Item"
        verbose_name_plural = "Manual Order Items"

    def save(self, *args, **kwargs):
        self.category = Item.Category.OFFERS
        super().save(*args, **kwargs)


class MorePubgItem(Item):
    class Meta:
        proxy = True
        verbose_name = "More PUBG Service Item"
        verbose_name_plural = "More PUBG Service Items"

    def save(self, *args, **kwargs):
        self.category = Item.Category.POPULARITY
        super().save(*args, **kwargs)
