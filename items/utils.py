import logging

from codes.models import Activator
from integrations.shop2topup import shop2topup_api
from items.models import Item
from payments.smileone import so_api

logger = logging.getLogger(__name__)


def update_smileone_items():
    pl = so_api.get_product_list("mobilelegends")
    for p in pl:
        if Item.objects.filter(category=Item.Category.DIAMOND, data__id=p.id).exists():
            continue
        Item.objects.get_or_create(
            title=p.spu,
            category=Item.Category.DIAMOND,
            price=100,
            amount=None,
            is_active=False,
            activator=Activator.SMILEONE,
            data=p.to_dict(),
        )


def sync_shop2topup_items():
    logger.info("Starting Shop2TopUp items synchronization...")

    import asyncio

    offers = asyncio.run(shop2topup_api.get_offers())

    if not offers:
        logger.warning("No offers received from Shop2TopUp API. Skipping sync.")
        return

    provider_ids_from_api = set()
    synced_count = 0
    created_count = 0

    for offer in offers:
        provider_id = offer["itemId"]
        provider_ids_from_api.add(provider_id)

        defaults = {
            "title": offer["name"],
            "price": offer["price"],
            "category": Item.Category.FREE_FIRE,
        }

        item, created = Item.objects.update_or_create(
            provider_item_id=provider_id, defaults=defaults
        )

        if created:
            item.is_active = False
            item.save(update_fields=["is_active"])
            created_count += 1
            logger.info(f"Created new Free Fire item: {item.title}")

        synced_count += 1

    deactivated_count = (
        Item.objects.filter(category=Item.Category.FREE_FIRE, is_active=True)
        .exclude(provider_item_id__in=provider_ids_from_api)
        .update(is_active=False)
    )

    logger.info(
        f"Shop2TopUp sync finished. "
        f"Processed: {synced_count}, Created: {created_count}, Deactivated: {deactivated_count}."
    )
