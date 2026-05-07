from django.db import models
from .base import TrackableModel


class Wordlist(TrackableModel):
    name        = models.CharField(max_length=100, unique=True)
    language    = models.ForeignKey(
        "generator.Lookup", on_delete=models.PROTECT,
        related_name="wordlists_by_language",
        limit_choices_to={"type__code": "language"},
    )
    theme       = models.ForeignKey(
        "generator.Lookup", on_delete=models.PROTECT,
        related_name="wordlists_by_theme",
        limit_choices_to={"type__code": "wordlist_theme"},
    )
    description = models.TextField(blank=True)
    source      = models.CharField(max_length=255, blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        app_label = "generator"
        db_table  = "wordlist"

    def __str__(self):
        return f"{self.name} ({self.language.code}/{self.theme.code})"


class Category(TrackableModel):
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        app_label = "generator"
        db_table  = "category"

    def __str__(self):
        return self.name
