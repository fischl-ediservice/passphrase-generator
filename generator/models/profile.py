from django.db import models
from .base import VersionedModel
from .wordlist import Wordlist
from core.generator import GeneratorConfig


class GeneratorProfile(VersionedModel):
    name       = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)
    wordlist   = models.ForeignKey(
        Wordlist, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="profiles",
    )
    word_count   = models.PositiveSmallIntegerField(default=4)
    min_length   = models.PositiveSmallIntegerField(default=4)
    max_length   = models.PositiveSmallIntegerField(default=30)
    difficulty   = models.ForeignKey("generator.Lookup", on_delete=models.PROTECT, related_name="profiles_by_difficulty",  limit_choices_to={"type__code": "difficulty"},   null=True, blank=True)
    case_mode    = models.ForeignKey("generator.Lookup", on_delete=models.PROTECT, related_name="profiles_by_case",        limit_choices_to={"type__code": "case_mode"},    null=True, blank=True)
    umlaut_mode  = models.ForeignKey("generator.Lookup", on_delete=models.PROTECT, related_name="profiles_by_umlaut",      limit_choices_to={"type__code": "umlaut_mode"},  null=True, blank=True)
    eszett_mode  = models.ForeignKey("generator.Lookup", on_delete=models.PROTECT, related_name="profiles_by_eszett",      limit_choices_to={"type__code": "eszett_mode"},  null=True, blank=True)
    reverse_mode = models.ForeignKey("generator.Lookup", on_delete=models.PROTECT, related_name="profiles_by_reverse",     limit_choices_to={"type__code": "reverse_mode"}, null=True, blank=True)
    separator             = models.CharField(max_length=10, default="-", blank=True)
    special_chars_enabled = models.BooleanField(default=False)
    digit_mode            = models.CharField(max_length=20, default="off")
    special_mode          = models.CharField(max_length=20, default="off")
    avoid_same_initial    = models.BooleanField(default=False)
    syllable_shuffle_enabled = models.BooleanField(default=False)
    exclude_germanized    = models.BooleanField(default=True)

    class Meta:
        app_label = "generator"
        db_table  = "generator_profile"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(word_count__gte=1, word_count__lte=20),
                name="word_count_range",
            ),
            models.CheckConstraint(
                condition=models.Q(min_length__lte=models.F("max_length")),
                name="min_length_lte_max_length",
            ),
        ]

    def to_config(self) -> GeneratorConfig:
        rules = [
            (r.source_char, r.target_char, r.weight)
            for r in self.special_char_rules.filter(is_active=True)
        ] if self.special_chars_enabled else []
        return GeneratorConfig(
            word_count            = self.word_count,
            separator             = self.separator,
            case_mode             = self.case_mode.code    if self.case_mode    else "lower",
            umlaut_mode           = self.umlaut_mode.code  if self.umlaut_mode  else "allow",
            eszett_mode           = self.eszett_mode.code  if self.eszett_mode  else "allow",
            reverse_mode          = self.reverse_mode.code if self.reverse_mode else "off",
            special_chars_enabled = self.special_chars_enabled,
            special_char_rules    = rules,
            special_mode          = self.special_mode or ("replace" if self.special_chars_enabled else "off"),
            digit_mode            = self.digit_mode,
            syllable_shuffle_enabled = self.syllable_shuffle_enabled,
            avoid_same_initial    = self.avoid_same_initial,
            include_adult_words   = False,
        )

    def __str__(self):
        return f"{self.name} ({'Standard' if self.is_default else 'Profil'})"
