from django.core.exceptions import ValidationError
from django.db import models


class Mailing(models.Model):
    text = models.TextField(
        max_length=4096,
        help_text="Can be empty if mailing has attachment",
        verbose_name="Text",
        blank=True,
        null=True,
    )

    date_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time of mailing",
        verbose_name="Date/time",
    )
    is_sent = models.BooleanField(
        help_text="sending status", verbose_name="sending status", default=False
    )

    class Meta:
        verbose_name = "Mailing"
        verbose_name_plural = "Mailings"

    def __str__(self) -> str:
        return self.text[:20] if self.text else "Attachment"

    def clean(self) -> None:
        if self.date_time and not self.id:
            raise ValidationError("Firstly save object and then fill date/time")
        if self.id:
            all_types = set(
                [attachment.file_type for attachment in self.attachments.all()]
            )
            if Attachment.FileType.DOCUMENT in all_types and len(all_types) > 1:
                raise ValidationError("Documents and other types cant been mixed")
            if self.attachments.exists() and len(self.text) > 1024:
                raise ValidationError(
                    f"Text too long to send with attachment ({len(self.text)} of 1024)"
                )
        return super().clean()


class Attachment(models.Model):
    class FileType(models.TextChoices):
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"

    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="mailing",
    )
    file_type = models.CharField(
        max_length=10, choices=FileType, verbose_name="Type of attachment"
    )
    file = models.FileField(verbose_name="Attached file/video/photo")
    file_id = models.CharField(
        max_length=255,
        help_text="Leave empty. Delete to update media.",
        verbose_name="File ID",
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs) -> None:
        all_types = set(
            [attachment.file_type for attachment in self.mailing.attachments.all()]
        )
        if (
            Attachment.FileType.DOCUMENT in all_types
            and self.file_type != Attachment.FileType.DOCUMENT
            or Attachment.FileType.PHOTO in all_types
            and self.file_type == Attachment.FileType.DOCUMENT
            or Attachment.FileType.VIDEO in all_types
            and self.file_type == Attachment.FileType.DOCUMENT
        ):
            raise ValidationError("Documents and other types cant been mixed")
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"


class ManagerChat(models.Model):
    title = models.CharField(max_length=100, verbose_name="Title")
    tg_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")

    class Meta:
        verbose_name = "Manager chat"
        verbose_name_plural = "Manager chats"

    def __str__(self) -> str:
        return f"{self.title} | {self.tg_id}"


class DailyReport(ManagerChat):
    class Meta:
        proxy = True
        verbose_name = "Daily Sales Report"
        verbose_name_plural = "Daily Sales Reports"


class ProfitReport(ManagerChat):
    class Meta:
        proxy = True
        verbose_name = "Profit Report"
        verbose_name_plural = "Profit Reports"
