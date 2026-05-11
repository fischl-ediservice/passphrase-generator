from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import VersionedModel
from .wordlist import Wordlist, Category


class Word(VersionedModel):
    SYLLABLE_SHUFFLE_CHOICES = [
        ("unsuitable", "Nicht geeignet"),
        ("rotate",     "Rotation"),
        ("random",     "Zufällig"),
        ("reverse",    "Umgekehrt"),
    ]

    wordlist       = models.ForeignKey(Wordlist, on_delete=models.CASCADE, related_name="words")
    word           = models.CharField(max_length=100)
    part_of_speech = models.ForeignKey(
        "generator.Lookup", on_delete=models.PROTECT,
        related_name="words_by_pos",
        limit_choices_to={"type__code": "part_of_speech"},
        null=True, blank=True,
    )
    categories = models.ManyToManyField(
        Category, through="WordCategory", blank=True, related_name="words",
    )
    difficulty = models.ForeignKey(
        "generator.Lookup", on_delete=models.PROTECT,
        related_name="words_by_difficulty",
        limit_choices_to={"type__code": "difficulty"},
        null=True, blank=True,
    )
    origin = models.ForeignKey(
        "generator.Lookup", on_delete=models.PROTECT,
        related_name="words_by_origin",
        limit_choices_to={"type__code": "origin"},
        null=True, blank=True,
    )
    word_length           = models.PositiveSmallIntegerField(editable=False)
    syllable_count        = models.PositiveSmallIntegerField(null=True, blank=True)
    syllables             = models.JSONField(default=list, blank=True)
    syllable_shuffle_mode = models.CharField(
        max_length=20, choices=SYLLABLE_SHUFFLE_CHOICES, default="unsuitable"
    )
    phonetic_score = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    is_compound        = models.BooleanField(default=False)
    is_loanword        = models.BooleanField(default=False)
    is_germanized      = models.BooleanField(default=False, help_text="z.B. Computer, Meeting")
    is_technical       = models.BooleanField(default=False)
    adult_only         = models.BooleanField(default=False)
    reverse_suitable   = models.BooleanField(default=True)
    syllables_anchored = models.BooleanField(default=True)

    class Meta:
        app_label       = "generator"
        db_table        = "word"
        unique_together = [("wordlist", "word")]
        indexes = [
            models.Index(fields=["wordlist", "word_length"]),
            models.Index(fields=["wordlist", "is_germanized"]),
            models.Index(fields=["wordlist", "syllable_count"]),
            models.Index(fields=["wordlist", "syllables_anchored"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(word_length__gte=1),
                name="word_length_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(phonetic_score__gte=1, phonetic_score__lte=10)
                    | models.Q(phonetic_score__isnull=True)
                ),
                name="phonetic_score_range",
            ),
        ]

    def save(self, *args, **kwargs):
        self.word_length = len(self.word)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.word

    def phonetic_label(self) -> str:
        if self.phonetic_score is None:
            return "nicht bewertet"
        if self.phonetic_score >= 8:
            return "gut merkbar"
        if self.phonetic_score >= 5:
            return "etwas hakelig"
        return "schwer aussprechbar"


class WordCategory(models.Model):
    word     = models.ForeignKey(Word,     on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        app_label       = "generator"
        db_table        = "word_category"
        unique_together = [("word", "category")]

    def __str__(self):
        return f"{self.word.word} → {self.category.name}"
