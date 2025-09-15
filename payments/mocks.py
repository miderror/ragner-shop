import asyncio
import logging
import time

from .smileone import SmileOneProduct

logger = logging.getLogger(__name__)


class MockSmileOneAPI:
    """Полная имитация класса SmileOneAPI."""

    def get_product_list(self, product: str) -> list[SmileOneProduct]:
        logger.warning(f"SMILE.ONE MOCK: Запрос списка продуктов для '{product}'")
        if product == "mobilelegends":
            return [
                SmileOneProduct(
                    product="mobilelegends",
                    id=101,
                    spu="56 Алмазов",
                    price="0.80",
                    cost_price="0.70",
                    discount="0.1",
                ),
                SmileOneProduct(
                    product="mobilelegends",
                    id=102,
                    spu="112 Алмазов",
                    price="1.50",
                    cost_price="1.30",
                    discount="0.1",
                ),
                SmileOneProduct(
                    product="mobilelegends",
                    id=103,
                    spu="296 Алмазов",
                    price="3.50",
                    cost_price="3.20",
                    discount="0.1",
                ),
            ]
        return []

    def create_order(self, product, product_id, user_id, zone_id=None):
        logger.warning(f"SMILE.ONE MOCK: Создание заказа для product_id={product_id}")
        time.sleep(1)
        if not zone_id or len(zone_id) < 4:
            return False, "Mocked error: Invalid Zone ID"
        return True, f"Mocked success: order SO_MOCK_{product_id}_{user_id} created"


async def mock_ucodeium_activate(player_id: int, uc_code: str, uc_value: str | int):
    """Мок для активатора UCodeium."""
    logger.warning(
        f"[MOCK] UCODEIUM: Попытка активации кода {uc_code} для {player_id} ({uc_value})"
    )
    await asyncio.sleep(1)
    if "FAIL" in uc_code.upper():
        logger.error(f"[MOCK] UCODEIUM: Симуляция ошибки для кода {uc_code}")
        return False, "201: Mocked Invalid Code"
    logger.info(f"[MOCK] UCODEIUM: Код {uc_code} успешно 'активирован'")
    return True, "0"


async def mock_kokos_activate(
    player_id: int, uc_code: str, uc_value: str | None = None
):
    """Мок для активатора Kokos."""
    logger.warning(f"[MOCK] KOKOS: Попытка активации кода {uc_code} для {player_id}")
    await asyncio.sleep(1)
    if "FAIL" in uc_code.upper():
        logger.error(f"[MOCK] KOKOS: Симуляция ошибки для кода {uc_code}")
        return False, "CODE_USED"
    logger.info(f"[MOCK] KOKOS: Код {uc_code} успешно 'активирован'")
    return True, "0"


async def mock_fars_activate(
    player_id: int,
    uc_code: str,
    uc_value: str | None = None,
    order_id: str | None = None,
):
    """Мок для активатора FARS."""
    logger.warning(
        f"[MOCK] FARS: Попытка активации кода {uc_code} для {player_id} (order: {order_id})"
    )
    await asyncio.sleep(1)
    if "FAIL" in uc_code.upper():
        logger.error(f"[MOCK] FARS: Симуляция ошибки для кода {uc_code}")
        return False, "INVALID_CODE"
    logger.info(f"[MOCK] FARS: Код {uc_code} успешно 'активирован'")
    return True, "0"


def mock_get_binance_updates():
    """Мок для получения депозитов с Binance."""
    logger.warning("[MOCK] BINANCE: Проверка 'депозитов'")
    return [("10.123", "mock_tx_binance_12345")]


def mock_get_bybit_updates():
    """Мок для получения депозитов с ByBit."""
    logger.warning("[MOCK] BYBIT: Проверка 'депозитов'")
    return [("25.456", "mock_tx_bybit_67890")]
