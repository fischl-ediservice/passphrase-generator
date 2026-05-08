"""
Kern-Generator. Kein Framework-Import — nur stdlib + core.
"""
import secrets
from dataclasses import dataclass, field

from core.entropy import calculate_entropy, entropy_label, secure_sample, stride_sample
from core.transforms import (
    apply_case,
    apply_eszett,
    apply_special_chars,
    normalize_umlaut,
    reverse_word,
)


@dataclass
class GeneratorConfig:
    word_count:            int   = 4
    separator:             str   = "-"
    case_mode:             str   = "lower"    # lower | upper | title | original
    umlaut_mode:           str   = "allow"    # allow | normalize | exclude
    eszett_mode:           str   = "allow"    # allow | replace
    reverse_mode:          str   = "off"      # off | some | every_other | all
    special_chars_enabled: bool  = False
    special_char_rules:    list  = field(default_factory=list)  # [(source, target, weight)]
    avoid_same_initial:    bool  = False


@dataclass
class PassphraseResult:
    passphrase:    str
    words:         list[str]
    entropy_bits:  float
    entropy_label: str
    pool_size:     int


def generate_passphrase(words: list[str], config: GeneratorConfig) -> PassphraseResult:
    if len(words) < config.word_count:
        raise ValueError(
            f"Wortpool zu klein: {len(words)} Wörter, {config.word_count} benötigt."
        )

    pool_size   = len(words)
    selected    = _pick_words(words, config)
    transformed = [_transform(w, i, config) for i, w in enumerate(selected)]

    bits = calculate_entropy(pool_size, config.word_count)
    return PassphraseResult(
        passphrase    = config.separator.join(transformed),
        words         = transformed,
        entropy_bits  = bits,
        entropy_label = entropy_label(bits),
        pool_size     = pool_size,
    )


def _pick_words(words: list[str], config: GeneratorConfig) -> list[str]:
    # Stride-Sampling: gleichmäßige Abdeckung des Pools
    # dann aus dem Stride-Sample die finale Auswahl treffen
    sample_size = min(len(words), max(config.word_count * 10, 500))
    pool = stride_sample(words, sample_size)

    if not config.avoid_same_initial:
        return secure_sample(pool, config.word_count)
    for _ in range(20):
        candidate = secure_sample(pool, config.word_count)
        if len({w[0].lower() for w in candidate}) == len(candidate):
            return candidate
    return candidate  # type: ignore[return-value]


def _transform(word: str, index: int, config: GeneratorConfig) -> str:
    word = normalize_umlaut(word, config.umlaut_mode)
    word = apply_eszett(word, config.eszett_mode)
    if config.special_chars_enabled and config.special_char_rules:
        word = apply_special_chars(word, config.special_char_rules, secrets.randbelow)
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
