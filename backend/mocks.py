import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def patch_all():
    """
    Главная функция-патчер.
    Проверяет USE_MOCK и, если нужно, подменяет реальные функции/классы на моки.
    """
    USE_MOCK = getattr(settings, "ENV", lambda: None).bool("USE_MOCK", default=False)

    if not USE_MOCK:
        return

    logger.warning("=" * 50)
    logger.warning("!!! РЕЖИМ MOCK-СЕРВЕРОВ АКТИВИРОВАН !!!")
    logger.warning("!!! ВНЕШНИЕ API ВЫЗЫВАТЬСЯ НЕ БУДУТ !!!")
    logger.warning("=" * 50)

    try:
        from payments import smileone
        from payments.mocks import MockSmileOneAPI

        smileone.so_api = MockSmileOneAPI()
        logger.info("[MOCK] payments.smileone.so_api успешно подменен.")
    except Exception as e:
        logger.error(f"[MOCK] Не удалось подменить smileone.so_api: {e}")

    try:
        from payments import activators
        from payments.mocks import (
            mock_fars_activate,
            mock_kokos_activate,
            mock_ucodeium_activate,
        )

        activators.aactivate_code = mock_ucodeium_activate
        activators.aactivate_code_kokos = mock_kokos_activate
        activators.aactivate_code_fars = mock_fars_activate
        logger.info(
            "[MOCK] payments.activators (UCodeium, Kokos, FARS) успешно подменены."
        )
    except Exception as e:
        logger.error(f"[MOCK] Не удалось подменить активаторы: {e}")

    try:
        from payments import payment
        from payments.mocks import mock_get_binance_updates, mock_get_bybit_updates

        payment.get_binance_updates = mock_get_binance_updates
        payment.get_bybit_updates = mock_get_bybit_updates
        logger.info("[MOCK] payments.payment (Binance, ByBit) успешно подменены.")
    except Exception as e:
        logger.error(f"[MOCK] Не удалось подменить проверку кошельков: {e}")

    try:
        from integrations import shop2topup
        from integrations.mocks import mock_shop2topup_api

        shop2topup.shop2topup_api = mock_shop2topup_api
        logger.info(
            "[MOCK] integrations.shop2topup.shop2topup_api successfully patched."
        )
    except Exception as e:
        logger.error(f"[MOCK] Failed to patch shop2topup_api: {e}")
