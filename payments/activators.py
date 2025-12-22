import logging

import aiohttp
from django.conf import settings

UCODEIUM_URL = settings.ENV.str('UCODEIUM_URL', '')
UCODEIUM_TOKEN = settings.ENV.str('UCODEIUM_TOKEN', '')

KOKOS_URL = settings.ENV.str('KOKOS_URL', '')
KOKOS_TOKEN = settings.ENV.str('KOKOS_TOKEN', '')

FARS_URL = settings.ENV.str('FARS_URL', '')
FARS_TOKEN = settings.ENV.str('FARS_TOKEN', '')

UCODEIUM_SUCCESS = (
    '0',
)
CODE_UCODEIUM_ERRORS = (
    '101',
    '102',
    '201',
)
NOT_CODE_UCODEIUM_ERRORS = (
    '202',
    '301',
)
CODE_KOKOS_ERRORS = (
    'CODE_USED',
    'INVALID_CODE',
)
NOT_CODE_KOKOS_ERRORS = (
    'NO_ACCOUNTS_AVAILABLE',
    'LOGIN_FAILED',
    'CHARACTER_NOT_FOUND',
    'INVALID_ACTIVATION_RESPONSE',
    'RISK_CONTROL',
    'UNKNOWN',
    'NETWORK_ERROR',
)

logger = logging.getLogger(__name__)


async def aactivate_code(player_id: int, uc_code: str, uc_value: str | int):
    if isinstance(uc_value, int):
        uc_value = f'{uc_value} UC'
    url = f'{UCODEIUM_URL}/api/activate'
    data = {
        'player_id': player_id,
        'uc_code': uc_code,
        'uc_value': uc_value,  # "60 UC" такой формат
    }
    logger.info(f'{data}')
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': UCODEIUM_TOKEN
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, json=data) as response:
            logger.info(f'Поступил ответ {await response.text()} со статусом {response.status}')
            if response.status not in (200, 201):
                logging.error(f'Ошибка активации кода {response.status}: {await response.text()}')
            res = await response.json()
    # res = {
    #     "result_code": 0,
    #     "activation_data": {
    #         "activation_success": True,
    #         "activation_id": "482915829538",
    #         "player_id": "5555555555",
    #         "uc_pack": "60 UC",
    #         "redeem_code": "AeCmNADi2R2bQbF3A3",
    #         "request_cost": 0.3,
    #     },
    # }
    if res["result_code"] == 0 and res["activation_data"]['activation_success']:
        return True, res["result_code"]
    logger.error(f'Код не активирован. Ошибка {res["result_code"]} см. документацию')
    return False, f'{res.get("result_code")}:{res.get("message")}'[:50]


async def aactivate_code_kokos(player_id: int, uc_code: str, uc_value: str | None = None):
    url = f'{KOKOS_URL}/redeem'
    data = {
        'requireReceipt': True,
        'playerId': str(player_id),
        'codeOverride': uc_code
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {KOKOS_TOKEN}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, json=data) as response:
            logger.info(f'Поступил ответ {await response.text()} со статусом {response.status}')
            if response.status in (503,):
                logging.warning(f'Ошибка активации кода {response.status}: {await response.json()}')
                res = await response.json()
                # res = {
                #     "type": "ActivationError",
                #     "id": 18,
                #     "code": "r3h4x2Jh2W2853g9g4",
                #     "playerId": "51364069154",
                #     "errorCode": "CODE_USED",
                #     "errorMessage": ("REDEEM_CODE_ALREADY_USED: Redeem code is "
                #                      "already used, please check the redeem code, "
                #                      "cause: -, solution:-, debugid: 98fa4c6ab945320d0fe4304f38cc5653"),
                #     "codeReset": False,
                #     "createdAt": "2024-09-25T17:32:28Z"
                #     }
                return False, res['errorCode']
            elif response.status in (200, 201):
                return True, '0'
            logger.error(f'Поступил неожиданный ответ от сервера {response.status}: {await response.text()}')
            return False, 'Unexpectable error'


async def aactivate_code_fars(player_id: int, uc_code: str, uc_value: str | None = None, order_id: str | None = None):
    """https://prostodomendlyachegoto.online/midas-controller/v2/docs."""
    url = f'{FARS_URL}/activators/redeem'
    if uc_value:
        uc_value = int(uc_value)
    data = {
        "merchant_id": f'{order_id}_player_id',
        "activator_type": None,
        "amount": uc_value,
        "pubg_id": player_id,
        "codes": {
            uc_code: uc_value,
        },
        "max_redeem_attempts": 1,
        "ignore_redeem_error": False,
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {FARS_TOKEN}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, json=data) as response:
            logger.info(f'Поступил ответ {await response.text()} со статусом {response.status}')
            if response.status in (200, 201,):
                return True, '0'
            logging.error(f'Ошибка активации кода {response.status}: {await response.text()}')
            res = await response.json()
            return False, res.get('error_code')
