from django.conf import settings
from django.db import models
from .base import TrackableModel


class UserWordFeedback(TrackableModel):
    """
    Nutzerbeurteilung einzelner Wörter — lokales adaptives Lernen.
    Kein Cloud-Profil, keine KI. Nur: wie fühlt sich dieses Wort an?

    user_feel_diff = subjektive Schwierigkeitseinschätzung aus Nutzersicht.
    """

    FEEL_CHOICES = [
        (1, "sehr gut merkbar"),
        (2, "gut merkbar"),
        (3, "mittel"),
        (4, "schwer merkbar"),
        (5, "nicht verwendbar"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="word_feedbacks",
    )
    word = models.ForeignKey(
        "generator.Word",
        on_delete=models.CASCADE,
        related_name="user_feedbacks",
    )
    user_feel_diff = models.PositiveSmallIntegerField(
        choices=FEEL_CHOICES,
        help_text="Subjektive Schwierigkeitseinschätzung (1=sehr gut merkbar, 5=nicht verwendbar)",
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optionale Freitextnotiz des Nutzers",
    )

    class Meta:
        app_label   = "generator"
        db_table    = "user_word_feedback"
        unique_together = [("user", "word")]
        indexes = [
            models.Index(fields=["user", "user_feel_diff"]),
            models.Index(fields=["word", "user_feel_diff"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user_feel_diff__gte=1, user_feel_diff__lte=5),
                name="user_feel_diff_range",
            ),
        ]

    def __str__(self) -> str:
        label = dict(self.FEEL_CHOICES).get(self.user_feel_diff, "?")
        return f"{self.user} → {self.word.word}: {label}"
