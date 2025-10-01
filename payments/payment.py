import logging
from time import time

import aiohttp
from binance.spot import Spot
from pybit.unified_trading import HTTP

from backend.config import PAYMENT_CONFIG
from backend.settings import ENV
from orders.models import TopUp
from users.models import TgUser
from asgiref.sync import sync_to_async

CODEEPAY_API_KEY = ENV.str('CODEEPAY_API_KEY')
BASE_IP = ENV.str('BASE_IP')
BOT_URL = ENV.str('BOT_URL')

MIN_PRICE = 100


logger = logging.getLogger(__name__)

client = Spot(api_key=ENV.str('BINANCE_API_KEY'), api_secret=ENV.str('BINANCE_API_SECRET'))
session = HTTP(testnet=False, api_key=ENV.str('BYBIT_API_KEY'), api_secret=ENV.str('BYBIT_API_SECRET'),)


def get_binance_updates():
    timestamp = int((time()) * 1000)
    startTime = timestamp - 1000 * 60 * 60 * 24
    try:
        logger.warning("BINANCE_DEBUG: Trying get_binance_updates")
        history = client.deposit_history(status=1, coin='USDT', startTime=startTime, timestamp=timestamp)
        logger.warning(f"BINANCE_DEBUG: Raw response from Binance API: {history}")
        return [(row['amount'], row['txId']) for row in history if row['status'] == 1]
    except Exception as e:
        logger.error(f"BINANCE_DEBUG: Exception in get_binance_updates: {e}", exc_info=True)
        return []


def get_bybit_updates():
    startTime = int((time() - 60 * 60 * 24) * 1000)
    result = []
    try:
        cursor = None
        while True:
            response = session.get_deposit_records(coin='USDT', startTime=startTime, cursor=cursor)
            result.extend([(row['amount'], row['txID']) for row in response['result']['rows'] if row['status'] == 3])
            logger.debug(f'bybit response {response}')
            cursor = response['result']['nextPageCursor']
            if cursor is None or cursor == '':
                break
        logger.debug(f'{result=}')
    except Exception as e:
        logger.error(e)
    try:
        cursor = None
        while True:
            response = session.get_internal_deposit_records(coin='USDT', startTime=startTime, cursor=cursor)
            result.extend([(row['amount'], row['txID']) for row in response['result']['rows'] if row['status'] == 2])
            logger.debug(f'bybit response {response}')
            cursor = response['result']['nextPageCursor']
            if cursor is None or cursor == '':
                break
    except Exception as e:
        logger.error(e)
    logger.debug(f'{result=}')
    return result


async def check_wallets():
    result = [*get_binance_updates(), *get_bybit_updates()]
    for amount, txId in result:
        if await TopUp.objects.filter(tx_id=txId).aexists():
            logger.debug('This payment has been already proceed')
            continue
        topup = await TopUp.objects.filter(to_pay=amount, is_paid=False).afirst()
        if topup:
            logger.info(f'Found topup {topup}')
            topup.is_paid = True
            topup.tx_id = txId
            await topup.atop()
            await topup.asave(update_fields=('is_paid', 'tx_id'))


async def create_codeepay_payment(tg_user: TgUser, to_pay: int):
    url = 'https://codeepay.ru/initiate_payment'
    ruble_comission = await sync_to_async(lambda: PAYMENT_CONFIG.TOPUP_RUBLE_COMISSION)()
    comission = to_pay * (ruble_comission / 100)
    amount = to_pay - comission
    topup = await TopUp.objects.acreate(
        tg_user=tg_user,
        amount=amount,
        comission=comission,
        to_pay=to_pay,
        currency=TopUp.Currency.RUB,
    )
    callback_url = f'{BASE_IP}/webhook/codeepay/'
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': CODEEPAY_API_KEY
    }
    data = {
        'method_slug': 'sbp',
        'amount': topup.to_pay,
        'description': f'Оплата {topup} {tg_user}',
        'shop_name': 'string',
        'shop_url': BOT_URL,
        'metadata': {
            'order_id': topup.id,
            'notification_url': callback_url
        }
    }
    logging.info(f'Запрос платежа {data}')
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, json=data) as response:
            response_text = await response.text()
            logger.warning(f"CODEEPAY_DEBUG: Response status: {response.status}, Response body: {response_text}")
            if response.status not in (200, 201):
                logging.error(f'Ошибка codeepay {response.status}: {await response.text()}')
            res = await response.json()
    topup.payment_url = res.get('url')
    await topup.asave(update_fields=['payment_url'])
    return topup
