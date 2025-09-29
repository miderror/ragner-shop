from backend.celery import app

from .utils import sync_shop2topup_items, update_smileone_items


@app.task()
def update_smileone_items_task():
    """Фоново обновляет позиции SmileOne."""
    update_smileone_items()


@app.task()
def sync_shop2topup_items_task():
    """Background task to sync items from Shop2TopUp."""
    sync_shop2topup_items()
