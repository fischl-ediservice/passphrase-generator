from django.db import models
from .base import BaseModel
from .profile import GeneratorProfile


class SpecialCharRule(BaseModel):
    profile     = models.ForeignKey(GeneratorProfile, on_delete=models.CASCADE, related_name="special_char_rules")
    source_char = models.CharField(max_length=1)
    target_char = models.CharField(max_length=2)
    weight      = models.PositiveSmallIntegerField(default=5, help_text="1–10, höher = wahrscheinlicher")
    is_active   = models.BooleanField(default=True)

    class Meta:
        app_label       = "generator"
        db_table        = "special_char_rule"
        unique_together = [("profile", "source_char", "target_char")]
        constraints     = [
            models.CheckConstraint(
                condition=models.Q(weight__gte=1, weight__lte=10),
                name="special_char_weight_range",
            ),
        ]

    def save(self, *args, **kwargs):
        self.source_char = self.source_char.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source_char} → {self.target_char}"
