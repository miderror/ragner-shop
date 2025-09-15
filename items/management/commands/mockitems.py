from django.core.management import BaseCommand
from django.core.management.base import CommandError

from admin_panel.models import ManagerChat
from items.models import Folder, PopularityItem, PUBGUCItem, StockCodesItem


def mock_pubg_uc():
    uc_values = {
        60: 0.87,
        180: 2.6,
        325: 4.25,
        385: 5.12,
        660: 8.5,
        720: 9.37,
        985: 12.75,
        1320: 17.0,
        1800: 21.15,
        1920: 22.89,
        3850: 42.0,
        8100: 82.0,
        16200: 164.0,
        24300: 246.0,
        32400: 328.0,
    }
    for amount, price in uc_values.items():
        item, _ = PUBGUCItem.objects.get_or_create(
            category=PUBGUCItem.Category.PUBG_UC,
            price=price,
            amount=amount,
            is_active=True,
            chat=ManagerChat.objects.first(),
        )


def mock_codes():
    codes = (
        10,
        60,
        325,
        660,
        1800,
        3850,
        8100,
        16200,
        24300,
        32400,
    )
    for code in codes:
        StockCodesItem.objects.get_or_create(
            amount=code,
            price=10,
            category=PUBGUCItem.Category.CODES,
            is_active=True,
            chat=ManagerChat.objects.first(),
        )


def mock_pops():
    pops = {
        10: 1.6,
        20: 3.0,
        50: 7.0,
        80: 11.2,
        100: 14.0,
        300: 41.5,
        500: 68.5,
        1000: 133.0,
    }
    for amount, price in pops.items():
        PopularityItem.objects.get_or_create(
            amount=amount,
            price=price,
            category=PUBGUCItem.Category.POPULARITY,
            is_active=True,
            chat=ManagerChat.objects.first(),
        )
    PopularityItem.objects.get_or_create(
        title="HELICOPTER",
        price=22.0,
        category=PUBGUCItem.Category.POPULARITY,
        is_active=True,
        chat=ManagerChat.objects.first(),
    )
    PopularityItem.objects.get_or_create(
        title="PRIVATE PLANE",
        price=68.0,
        category=PUBGUCItem.Category.POPULARITY,
        is_active=True,
        chat=ManagerChat.objects.first(),
    )


def mock_home_votes():
    values = {
        "10k": "➖ 0.7🏢",
        "20k": "➖ 1.4🏢",
        "50k": "➖ 3.5🏢",
        "100k": "➖ 6.5🏢",
        "500k": "➖ 30🏢",
        "1000k": "➖ 55🏢",
    }
    return values


def mock_folders():
    folder_titles = [
        "PUBG MOBILE STOCKABLE CODES",
        "XBOX USA",
        "XBOX TURKEY",
        "PLAYSTATION USA",
        "PLAYSTATION TURKEY",
        "STEAM USA",
        "STEAM GLOBAL",
        "YALLA LUDO",
        "ITUNES USA",
        "Roblox USA",
        "Roblox brazil",
        "Nintendo usa",
        "FREE FIRE GLOBAL PINS",
        "JAWAKER CODES",
        "RAZER GOLD PINS",
    ]
    for title in folder_titles:
        Folder.objects.get_or_create(title=title)


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not ManagerChat.objects.exists():
            raise CommandError(
                'No ManagerChat found. Please run "python manage.py mockchats" first.'
            )

        self.stdout.write("Creating mock folders...")
        mock_folders()

        self.stdout.write("Creating mock PUBG UC items...")
        mock_pubg_uc()

        self.stdout.write("Creating mock Stockable Codes items...")
        mock_codes()

        self.stdout.write("Creating mock Popularity items...")
        mock_pops()

        self.stdout.write(
            self.style.SUCCESS("Successfully populated the database with mock items.")
        )
