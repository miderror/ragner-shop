import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)


class Shop2TopUpClient:
    def __init__(self):
        self.api_key = settings.ENV.str("SHOP2TOPUP_API_KEY", "")
        self.base_url = settings.ENV.str("SHOP2TOPUP_BASE_URL", "")
        if not self.api_key or not self.base_url:
            logger.error("Shop2TopUp API Key or Base URL is not configured.")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.request(method, url, **kwargs) as response:
                    if response.status != 200:
                        logger.error(
                            f"Shop2TopUp API error {response.status}: {await response.text()}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP Status {response.status}",
                        }
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Shop2TopUp request failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_offers(self) -> List[Dict[str, Any]]:
        response = await self._request("get", "/offers")
        return response.get("offers", []) if response.get("success") else []

    async def get_player_info(self, player_id: str) -> Optional[Dict[str, str]]:
        post_response = await self._request("post", "/id", json={"playerID": player_id})
        if not post_response.get("success"):
            logger.warning(
                f"Failed to initiate player ID check for {player_id}: {post_response}"
            )
            return None

        await asyncio.sleep(2)

        get_response = await self._request("get", f"/id?playerID={player_id}")
        if get_response.get("success") and "player_name" in get_response:
            return {
                "player_name": get_response["player_name"],
                "region": get_response.get("region", "UNKNOWN"),
            }
        logger.warning(f"Failed to get player info for {player_id}: {get_response}")
        return None

    async def create_topup(self, player_id: str, offer_id: int) -> Optional[str]:
        trx_id = str(uuid.uuid4())
        payload = {
            "playerID": player_id,
            "offer": offer_id,
            "trx_id": trx_id,
        }
        response = await self._request("post", "/topup", json=payload)
        if response.get("success"):
            return response.get("trxID", trx_id)
        return None

    async def get_transaction_status(self, trx_id: str) -> Optional[Dict[str, Any]]:
        response = await self._request("post", "/transaction", json={"trx_id": trx_id})
        if response.get("success"):
            return response
        return None


shop2topup_api = Shop2TopUpClient()
