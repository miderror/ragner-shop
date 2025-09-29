from django.contrib import admin

from .models import (
    CategoryDescription,
    DiamondItem,
    Folder,
    FreeFireItem,
    FreeFireRegion,
    FreeFireRegionPrice,
    GiftcardItem,
    HomeVoteItem,
    Item,
    ManualCategory,
    ManualItem,
    MorePubgItem,
    OffersItem,
    PopularityItem,
    PUBGUCItem,
    StarItem,
    StockCodesItem,
)


@admin.register(CategoryDescription)
class CategoryDescriptionAdmin(admin.ModelAdmin):
    list_display = ("category", "description")
    search_fields = ("category",)


@admin.register(PUBGUCItem)
class PUBGUCItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "amount",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = (
        "category",
        "data",
    )
    exclude = ("activator",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.PUBG_UC)


@admin.register(StockCodesItem)
class StockCodesItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "amount",
        "folder",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    readonly_fields = ("category",)
    exclude = (
        "activator",
        "data",
    )
    list_editable = ("folder", "price", "serial_number", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.CODES)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "folder":
            kwargs["queryset"] = Folder.objects.filter(category=Item.Category.CODES)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(GiftcardItem)
class GiftcardItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "folder",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    readonly_fields = ("category",)
    exclude = (
        "amount",
        "activator",
        "data",
    )
    list_editable = ("folder", "price", "serial_number", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.GIFTCARD)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "folder":
            kwargs["queryset"] = Folder.objects.filter(category=Item.Category.CODES)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(PopularityItem)
class PopularityItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = ("category",)
    exclude = ("amount", "activator", "data", "manual_category", "folder")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(category=Item.Category.POPULARITY, folder__isnull=True)
        )


@admin.register(HomeVoteItem)
class HomeVoteItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = ("category",)
    exclude = ("amount", "activator", "data", "manual_category", "folder")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(category=Item.Category.HOME_VOTE, folder__isnull=True)
        )


@admin.register(OffersItem)
class OffersItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = ("category",)
    exclude = ("amount", "activator", "data", "manual_category", "folder")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(category=Item.Category.OFFERS, manual_category__isnull=True)
        )


@admin.register(StarItem)
class StarItemAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "amount",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = ("category",)
    exclude = (
        "amount",
        "activator",
        "data",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.STARS)


@admin.register(DiamondItem)
class DiamondAdmin(admin.ModelAdmin):
    list_display = (
        "value",
        "title",
        "price",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = ("price", "serial_number", "is_active")
    readonly_fields = (
        "category",
        "data",
    )
    exclude = (
        "amount",
        "activator",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.DIAMOND)


@admin.register(MorePubgItem)
class MorePubgItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "folder",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_filter = ("folder", "is_active")
    list_editable = ("folder", "price", "serial_number", "is_active")
    exclude = ("amount", "activator", "data", "manual_category")
    readonly_fields = ("category",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(folder__category=Item.Category.MORE_PUBG)
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "folder":
            kwargs["queryset"] = Folder.objects.filter(category=Item.Category.MORE_PUBG)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["folder"].required = True
        return form


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "description",
        "ordering_id",
        "category",
    )
    list_editable = ("ordering_id", "category")
    list_filter = ("category",)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "category":
            allowed_categories = [
                Item.Category.CODES.value,
                Item.Category.MORE_PUBG.value,
            ]
            kwargs["choices"] = [
                (value, label)
                for value, label in db_field.choices
                if value in allowed_categories
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(ManualCategory)
class ManualCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "prompt_text", "is_active", "ordering")
    list_editable = ("is_active", "ordering")


@admin.register(ManualItem)
class ManualItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "manual_category",
        "buying_cost",
        "serial_number",
        "is_active",
    )
    list_editable = (
        "price",
        "manual_category",
        "serial_number",
        "is_active",
    )
    list_filter = ("manual_category", "is_active")
    readonly_fields = ("category",)
    exclude = ("amount", "activator", "data", "folder")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(manual_category__isnull=False)


@admin.register(FreeFireRegion)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("display_name", "name")
    search_fields = ("display_name", "name")
    fieldsets = ((None, {"fields": ("display_name", "name", "description")}),)

    def get_queryset(self, request):
        return super().get_queryset(request)


class FreeFireRegionPriceInline(admin.TabularInline):
    model = FreeFireRegionPrice
    extra = 1
    fields = ("region", "markup", "final_price", "is_active")
    readonly_fields = ("final_price",)


@admin.register(FreeFireItem)
class FreeFireItemAdmin(admin.ModelAdmin):
    list_display = ("title", "provider_item_id", "price", "serial_number", "is_active")
    list_editable = (
        "serial_number",
        "is_active",
    )
    search_fields = ("title", "provider_item_id")
    list_filter = ("is_active",)
    readonly_fields = ("provider_item_id", "title", "price", "category", "data")
    exclude = ("amount", "activator", "manual_category", "folder")

    inlines = [FreeFireRegionPriceInline]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category=Item.Category.FREE_FIRE)

    def has_add_permission(self, request):
        return False
