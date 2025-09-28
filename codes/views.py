import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from codes.models import Giftcard, StockbleCode, UcCode

from .forms import GiftCardImportForm, ImportForm, StockbleCodeImportForm

MIN_PERCENT = 80

logger = logging.getLogger(name=__name__)


@staff_member_required
def import_codes_view(request):
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            codes = form.cleaned_data["codes"]
            amount = form.cleaned_data["amount"]
            is_priority_use = form.cleaned_data["is_priority_use"]
            buying_cost = form.cleaned_data.get("price_of_codes")
            db_codes = [
                UcCode(
                    amount=amount,
                    code=code,
                    is_priority_use=is_priority_use,
                    buying_cost=buying_cost,
                )
                for code in codes
            ]
            UcCode.objects.bulk_create(
                db_codes,
                batch_size=1000,
            )
            return redirect(reverse("admin:codes_uccode_changelist"))
        else:
            return HttpResponse(f"There error in form:\n {form.errors}")
    else:
        form = ImportForm()
    return render(request, "admin/import_codes.html", {"form": form})


@staff_member_required
def import_giftcards_view(request):
    if request.method == "POST":
        form = GiftCardImportForm(request.POST)
        if form.is_valid():
            buying_cost = form.cleaned_data.get("price_of_codes")
            db_codes = [
                Giftcard(
                    item=form.cleaned_data["item"],
                    code=code,
                    buying_cost=buying_cost,
                )
                for code in form.cleaned_data["codes"]
            ]
            Giftcard.objects.bulk_create(
                db_codes,
                batch_size=1000,
            )
            return redirect(reverse("admin:codes_giftcard_changelist"))
        else:
            return HttpResponse(f"There error in form:\n {form.errors}")
    else:
        form = ImportForm()
    return render(request, "admin/import_codes.html", {"form": form})


@staff_member_required
def import_stockblecode_view(request):
    if request.method == "POST":
        form = StockbleCodeImportForm(request.POST)
        if form.is_valid():
            codes = form.cleaned_data["codes"]
            amount = form.cleaned_data["amount"]
            buying_cost = form.cleaned_data.get("price_of_codes")
            db_codes = [
                StockbleCode(
                    amount=amount,
                    code=code,
                    buying_cost=buying_cost,
                )
                for code in codes
            ]
            StockbleCode.objects.bulk_create(
                db_codes,
                batch_size=1000,
            )
            return redirect(reverse("admin:codes_stockblecode_changelist"))
        else:
            return HttpResponse(f"There error in form:\n {form.errors}")
    else:
        form = StockbleCodeImportForm()
    return render(request, "admin/import_codes.html", {"form": form})
