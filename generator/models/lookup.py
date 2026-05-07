from django.db import models
from .base import TrackableModel


class LookupType(models.Model):
    code        = models.CharField(max_length=50, unique=True)
    label       = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        app_label = "generator"
        db_table  = "lookup_type"

    def __str__(self):
        return f"{self.label} ({self.code})"


class Lookup(TrackableModel):
    type         = models.ForeignKey(LookupType, on_delete=models.PROTECT, related_name="lookups")
    code         = models.CharField(max_length=50)
    label        = models.CharField(max_length=100)
    vowels       = models.CharField(max_length=50, blank=True,
                       help_text="Vokalanker für Silbenprüfung, z.B. 'aeiouäöüy' für Deutsch")
    extra_vowels = models.CharField(max_length=50, blank=True)
    pyphen_lang  = models.CharField(max_length=10, blank=True,
                       help_text="Pyphen-Sprachcode, z.B. de_DE, en_US")
    sort_order   = models.PositiveSmallIntegerField(default=0)
    is_active    = models.BooleanField(default=True)

    class Meta:
        app_label       = "generator"
        db_table        = "lookup"
        unique_together = [("type", "code")]
        ordering        = ["type", "sort_order", "label"]

    def __str__(self):
        return f"{self.type.code}::{self.code} — {self.label}"

    @property
    def all_vowels(self) -> frozenset:
        combined = self.vowels + self.extra_vowels
        return frozenset(combined + combined.upper())
