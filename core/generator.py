"""
Kern-Generator. Kein Framework-Import — nur stdlib + core.
"""
import secrets
from dataclasses import dataclass, field

from core.entropy import calculate_entropy, entropy_label, stride_sample
from core.transforms import (
    apply_case,
    apply_case_guarantee,
    apply_eszett,
    inject_special_char,
    inject_digit,
    normalize_umlaut,
    reverse_word,
    shuffle_syllables,
)


@dataclass
class GeneratorConfig:
    word_count:            int   = 4
    separator:             str   = "-"
    separator_pool:        list  = field(default_factory=list)  # nicht-leer → zufällig pro Paar
    case_mode:             str   = "lower"    # lower | upper | title | original
    umlaut_mode:           str   = "allow"    # allow | normalize | exclude
    eszett_mode:           str   = "allow"    # allow | replace
    reverse_mode:          str   = "off"      # off | some | every_other | all
    special_chars_enabled:    bool  = False
    special_char_rules:       list  = field(default_factory=list)  # [(source, target, weight)]
    special_mode:             str   = "off"   # off | replace | inject_syllable | inject_word_end | inject_phrase
    avoid_same_initial:       bool  = False
    syllable_shuffle_enabled: bool  = False
    digit_mode:               str   = "off"   # off | replace | inject_syllable | inject_word_end | inject_phrase
    include_adult_words:      bool  = False
    include_technical_words:  bool  = False


@dataclass
class PassphraseResult:
    passphrase:    str
    words:         list[str]
    entropy_bits:  float
    entropy_label: str
    pool_size:     int


def generate_passphrase(
    words: list[str],
    config: GeneratorConfig,
    syllables_map: dict[str, list[str]] | None = None,
) -> PassphraseResult:
    if len(words) < config.word_count:
        raise ValueError(
            f"Wortpool zu klein: {len(words)} Wörter, {config.word_count} benötigt."
        )

    pool_size      = len(words)
    selected       = _pick_words(words, config)
    return generate_passphrase_from_selection(selected, pool_size, config, syllables_map)


def generate_passphrase_from_selection(
    selected: list[str],
    pool_size: int,
    config: GeneratorConfig,
    syllables_map: dict[str, list[str]] | None = None,
) -> PassphraseResult:
    transformed = [
        _transform(w, i, config, syllables_map)
        for i, w in enumerate(selected)
    ]

    transformed = apply_case_guarantee(transformed, config.case_mode, secrets.randbelow)
    if config.digit_mode != "off":
        transformed = inject_digit(
            transformed, config.digit_mode, secrets.randbelow,
            syllables_map=syllables_map,
            original_words=selected,
        )
    if config.special_mode != "off":
        transformed = inject_special_char(
            transformed, config.special_mode, secrets.randbelow,
            rules=config.special_char_rules,
            syllables_map=syllables_map,
            original_words=selected,
        )

    bits = calculate_entropy(pool_size, config.word_count)
    return PassphraseResult(
        passphrase    = _join(transformed, config),
        words         = selected,   # Originalwörter für die Chips — nicht transformiert
        entropy_bits  = bits,
        entropy_label = entropy_label(bits),
        pool_size     = pool_size,
    )


def _join(words: list[str], config: GeneratorConfig) -> str:
    if not config.separator_pool:
        return config.separator.join(words)
    parts = [words[0]]
    for w in words[1:]:
        parts.append(config.separator_pool[secrets.randbelow(len(config.separator_pool))])
        parts.append(w)
    return "".join(parts)


def _pick_words(words: list[str], config: GeneratorConfig) -> list[str]:
    if not config.avoid_same_initial:
        return stride_sample(words, config.word_count)
    for _ in range(20):
        candidate = stride_sample(words, config.word_count)
        if len({w[0].lower() for w in candidate}) == len(candidate):
            return candidate
    return candidate  # type: ignore[return-value]


def _transform(
    word: str,
    index: int,
    config: GeneratorConfig,
    syllables_map: dict[str, list[str]] | None = None,
) -> str:
    if config.syllable_shuffle_enabled and syllables_map:
        syllables = syllables_map.get(word, [])
        word = shuffle_syllables(word, syllables, secrets.randbelow)
    word = normalize_umlaut(word, config.umlaut_mode)
    word = apply_eszett(word, config.eszett_mode)
    word = _maybe_reverse(word, index, config.reverse_mode)
    word = apply_case(word, config.case_mode)
    return word


def _maybe_reverse(word: str, index: int, mode: str) -> str:
    if mode == "off":
        return word
    if mode == "all":
        return reverse_word(word)
    if mode == "every_other" and index % 2 == 1:
        return reverse_word(word)
    if mode == "some" and secrets.randbelow(3) == 0:
        return reverse_word(word)
    return word
