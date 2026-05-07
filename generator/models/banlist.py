from django.db import models
from .base import BaseModel, VersionedModel


class BanReason(BaseModel):
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        app_label = "generator"
        db_table  = "ban_reason"

    def __str__(self):
        return self.name


class BannedWord(VersionedModel):
    word   = models.CharField(max_length=100, unique=True)
    reason = models.ForeignKey(
        BanReason, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="banned_words",
    )
    note   = models.TextField(blank=True)

    class Meta:
        app_label = "generator"
        db_table  = "banned_word"

    def save(self, *args, **kwargs):
        self.word = self.word.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.word} [{self.reason}]" if self.reason else self.word
