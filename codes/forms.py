import string

from django import forms
from django.core.exceptions import ValidationError

from backend.constants import DEFAULT_SC_AMOUNTS, UC_AMOUNTS_FOR_IMPORT
from items.models import GiftcardItem, Item

MIN_CODE_LENGTH = 15


class ImportForm(forms.Form):
    amount = forms.ChoiceField(
        label="UC amount", choices=UC_AMOUNTS_FOR_IMPORT, required=True
    )
    is_priority_use = forms.BooleanField(
        required=False,
        label="Priority Use",
        help_text="Check this to mark these codes for priority use.",
    )
    price_of_codes = forms.DecimalField(
        label="Price of codes (per one)",
        required=False,
        help_text="Set the buying cost for each imported code.",
    )
    codes = forms.CharField(
        min_length=1,
        max_length=100_000 * 20,
        required=True,
        widget=forms.Textarea,
        help_text="Input codes separated by space or line break",
    )

    def clean_codes(self):
        codes = self.cleaned_data["codes"].split()
        for code in codes:
            if len(code) < MIN_CODE_LENGTH:
                raise ValidationError(f'Too short code: "{code}"')
            characters = string.ascii_letters + string.digits
            if any(char not in characters for char in code):
                raise ValidationError(f'Code has not valid symbols: "{code}"')
        return codes


class GiftCardImportForm(forms.Form):
    item = forms.ModelChoiceField(
        queryset=GiftcardItem.objects.filter(category=Item.Category.GIFTCARD),
        required=True,
        widget=forms.Select,
        help_text="Select a giftcard item",
    )
    price_of_codes = forms.DecimalField(
        label="Price of codes (per one)",
        required=False,
        help_text="Set the buying cost for each imported code.",
    )
    codes = forms.CharField(
        min_length=1,
        max_length=100_000 * 20,
        required=True,
        widget=forms.Textarea,
        help_text="Input codes separated by space or line break",
    )

    def clean_codes(self):
        codes = self.cleaned_data["codes"].split()
        return codes


class StockbleCodeImportForm(forms.Form):
    amount = forms.ChoiceField(
        label="UC amount", choices=DEFAULT_SC_AMOUNTS, required=True
    )
    price_of_codes = forms.DecimalField(
        label="Price of codes (per one)",
        required=False,
        help_text="Set the buying cost for each imported code.",
    )
    codes = forms.CharField(
        min_length=1,
        max_length=100_000 * 20,
        required=True,
        widget=forms.Textarea,
        help_text="Input codes separated by space or line break",
    )

    def clean_codes(self):
        codes = self.cleaned_data["codes"].split()
        for code in codes:
            if len(code) < MIN_CODE_LENGTH:
                raise ValidationError(f'Too short code: "{code}"')
            characters = string.ascii_letters + string.digits
            if any(char not in characters for char in code):
                raise ValidationError(f'Code has not valid symbols: "{code}"')
        return codes
