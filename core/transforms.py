"""
Zustandslose Wort-Transformationen. Kein Framework-Import.
"""

_UMLAUT_MAP = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
})

_ESZETT_MAP = str.maketrans({"ß": "ss"})


def apply_case(word: str, mode: str) -> str:
    if mode == "lower":
        return word.lower()
    if mode == "upper":
        return word.upper()
    if mode == "title":
        return word.capitalize()
    return word  # original


def normalize_umlaut(word: str, mode: str) -> str:
    if mode in ("normalize", "exclude"):
        return word.translate(_UMLAUT_MAP)
    return word  # allow


def apply_eszett(word: str, mode: str) -> str:
    if mode == "replace":
        return word.translate(_ESZETT_MAP)
    return word


def reverse_word(word: str) -> str:
    return word[::-1]


def apply_special_chars(
    word: str,
    rules: list[tuple[str, str, int]],
    rng_func,
) -> str:
    if not rules:
        return word
    result = list(word)
    for i, ch in enumerate(result):
        matching = [(t, w) for s, t, w in rules if s == ch.lower()]
        if not matching:
            continue
        total_weight = sum(w for _, w in matching) + 10
        roll = rng_func(total_weight)
        cumulative = 0
        for target, weight in matching:
            cumulative += weight
            if roll < cumulative:
                result[i] = target
                break
    return "".join(result)
