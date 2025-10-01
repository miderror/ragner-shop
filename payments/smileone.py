import logging
from dataclasses import dataclass, asdict
import json
import hashlib
import time
import requests

from django.conf import settings

UID = settings.ENV.str('SO_CUSTOMER_ID')
EMAIL = settings.ENV.str('SO_MAIL')
KEY = settings.ENV.str('SO_SECRET_KEY')

logger = logging.getLogger(__name__)


@dataclass
class SmileOneProduct:

    product: str
    cost_price: str
    discount: str
    id: int
    price: str
    spu: str

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict())


class SmileOneAPI:
    BASE_URL = "https://www.smile.one/ru/smilecoin/api"

    def __init__(self, uid: str, email: str, key: str):
        self.uid = uid
        self.email = email
        self.key = key

    def _generate_sign(self, sign_arr):
        """
        Generates a double MD5 hash signature based on a dictionary of parameters.

        Args:
            sign_arr (dict): A dictionary of parameters to be signed.
                            Example: {'uid': 'some_uid', 'product': 'some_product', 'time': 'some_time'}
            m_key (str): The master key used in the signature generation.

        Returns:
            str: The double MD5 hash signature.
        """
        # Sort the dictionary by key
        sorted_items = sorted(sign_arr.items())

        # Concatenate key-value pairs
        str_to_hash = ""
        for k, v in sorted_items:
            str_to_hash += f"{k}={v}&"

        # Append the master key
        str_to_hash += self.key

        # Calculate the double MD5 hash
        first_md5 = hashlib.md5(str_to_hash.encode('utf-8')).hexdigest()
        final_md5 = hashlib.md5(first_md5.encode('utf-8')).hexdigest()

        return final_md5

    def _make_request(self, endpoint: str, extra_params: dict) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        base_params = {
            'uid': self.uid,
            'email': self.email,
            'time': int(time.time())
        }
        params = {**base_params, **extra_params}
        params['sign'] = self._generate_sign(params)
        logger.warning(f'SMILEONE_DEBUG:Request data for smileone: {params}')
        logger.warning(f"SMILEONE_DEBUG: Requesting endpoint: {endpoint}")
        logger.warning(f"SMILEONE_DEBUG: Params sent (without sign): {json.dumps({**base_params, **extra_params})}")
        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SMILEONE_DEBUG: RequestException for endpoint {endpoint}: {e}")
            return {"status": 500, "message": str(e), "data": {}}

    def get_balance(self, product: str) -> dict:
        return self._make_request("querypoints", {'product': product})

    def get_product_list(self, product: str) -> list[SmileOneProduct]:
        result = self._make_request("productlist", {'product': product})
        return [SmileOneProduct(product=product, **p) for p in result['data']['product']]

    def get_servers(self, product: str) -> dict:
        return self._make_request("getserver", {'product': product})

    def create_order(self, product, product_id, user_id, zone_id=None):
        if not zone_id:
            zone_id = user_id
        result = self._make_request(
            "createorder",
            {
                'product': product,
                'productid': product_id,
                'userid': user_id,
                "zoneid": zone_id,
            }
        )
        message = f"status: {result.get('status')}, result:{result.get('message')}, order_id:{result.get('order_id')}"
        if result.get('status') == 200:
            return True, message
        return False, message


so_api = SmileOneAPI(UID, EMAIL, KEY)
