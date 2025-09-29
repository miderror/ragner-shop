from items.tasks import sync_shop2topup_items_task, update_smileone_items_task


async def start_background_tasks():
    update_smileone_items_task.delay()
    sync_shop2topup_items_task.delay()
