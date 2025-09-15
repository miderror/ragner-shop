import json
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from orders.models import TopUp

from codes.tasks import process_result
from codes.models import UcCode

MIN_PERCENT = 10
logger = logging.getLogger(name=__name__)


# Статусы и причины FARS
# Status
# 0"CREATED"
# 1"PROCESSING"
# 2"RESTART"
# 3"PENDING"
# 4"DEFERRED"
# 5"FAILED"
# 6"REDEEMED"
# 7"REJECTED"
# 8"CANCELLED"

# StatusReason
# 0"SITE_ERROR"
# 1"SERVER_ERROR"
# 2"ACCOUNT_BLOCKED"
# 3"RISK_ID_CONTROL"
# 4"NO_CODES"
# 5"INVALID_CODE"
# 6"UNMATCHED_CODE_AMOUNT"
# 7"INVALID_PUBG_ID"
# 8"DECOMPOSE_ERROR"
# 9"NO_LINKED_ACCOUNT"
# 10"TOO_LARGE_ORDER_AMOUNT"
# 11"TOO_MANY_REDEEM_ATTEMPTS"


@api_view(["POST",])
@permission_classes((AllowAny,))
def webhook_fars(request: Request):
    in_data = json.loads(request.data)
    logger.warning(in_data)
    for c in in_data.get('codes').keys():
        _status = in_data['status']
        code = UcCode.objects.filter(code=c).select_related('order').first()
        if not code:
            logger.warning(f'Код {c} не найден в базе')
            continue
        succ = None
        if _status in ('REDEEMED',):
            succ = True
        elif _status in ('DEFERRED', 'FAILED', 'REJECTED', 'CANCELLED'):
            succ = False
        if succ is None:
            UcCode.objects.filter(code=c).update(status=_status)
            continue
        async_to_sync(process_result)(code, succ, _status)
    return Response({'status': 'success', 'message': 'Payment processed successfully'}, status.HTTP_200_OK)


@api_view(["POST",])
@permission_classes((AllowAny,))
def codeepay_webhook(request: Request):
    in_data = request.data
    if not in_data:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    logger.debug(in_data)
    # in_data = {
    #     "order_id": "6PH111bkENp",
    #     "amount": 15,
    #     "method": "2",
    #     "metadata": {
    #         "order_id": 17311128531,
    #         "notification_url": "https://piglet.ngrok-free.app/api/payments/codeepay/",
    #     },
    #     "final_amount": "14.0475",
    # }
    order_id = in_data['metadata']['order_id']
    if float(in_data['final_amount']) / float(in_data['amount']) > MIN_PERCENT / 100:
        topup = get_object_or_404(TopUp, id=order_id)
        topup.is_paid = True
        topup.save(update_fields=('is_paid',))
    return Response({'status': 'success', 'message': 'Payment processed successfully'}, status.HTTP_200_OK)
