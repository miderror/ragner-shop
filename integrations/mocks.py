import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockShop2TopUpClient:
    async def get_offers(self) -> List[Dict[str, Any]]:
        logger.warning("[MOCK] Shop2TopUp: Getting offers.")
        return [
            {"name": "100 💎 + 10", "itemId": 1, "price": "1.00"},
            {"name": "310 💎 + 31", "itemId": 2, "price": "3.00"},
            {"name": "520 💎 + 52", "itemId": 3, "price": "5.00"},
        ]

    async def get_player_info(self, player_id: str) -> Optional[Dict[str, str]]:
        logger.warning(f"[MOCK] Shop2TopUp: Getting player info for {player_id}.")
        await asyncio.sleep(1)
        if player_id == "000000":
            return None
        regions = ["RU", "CIS", "EUROPE"]
        region = regions[int(player_id[-1]) % len(regions)]
        return {"player_name": f"MockPlayer_{player_id}", "region": region}

    async def create_topup(self, player_id: str, offer_id: int) -> Optional[str]:
        trx_id = str(uuid.uuid4())
        logger.warning(
            f"[MOCK] Shop2TopUp: Creating topup for player {player_id}, offer {offer_id}. TRX_ID: {trx_id}"
        )
        await asyncio.sleep(1)
        return trx_id

    async def get_transaction_status(self, trx_id: str) -> Optional[Dict[str, Any]]:
        logger.warning(f"[MOCK] Shop2TopUp: Getting status for TRX_ID {trx_id}.")
        await asyncio.sleep(1)
        if hasattr(self, f"_called_{trx_id}"):
            return {"success": True, "status": "DONE", "player_id": "12345678"}
        setattr(self, f"_called_{trx_id}", True)
        return {"success": True, "status": "PROCESSING"}


mock_shop2topup_api = MockShop2TopUpClient()
