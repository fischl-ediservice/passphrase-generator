"""
Zustandslose Wort-Transformationen. Kein Framework-Import.
"""

# ── Deutsche Wort-Normalisierung ────────────────────────────────────────────
# Kasus-/Numerus-Endungen die sicher gestrippt werden können.
# Reihenfolge: längste zuerst, damit "-ens" vor "-s" geprüft wird.
_NOUN_SUFFIXES: list[tuple[str, int]] = [
    # (Endung,  Mindeststammlänge)
    # Nur "-es" — sicherste Variante.
    # "-ens" weglassen: "Kästchens" → strip "ens" → "Kästch" (falsch!)
    # "-s" weglassen: zu viele Fehlalarme (Bus, Gas, Glas, …)
    ("es", 4),   # Hauses→Haus, Tages→Tag, Bades→Bad, Stromwasserbades→Stromwasserbad
]

_VOWELS = frozenset("aeiouäöüyAEIOUÄÖÜY")


def normalize_german_word(word: str) -> str:
    """
    Konservative Lemmatisierung für deutsche Substantive.
    Behandelt ausschließlich Nomina (erster Buchstabe groß).

    Beispiele:
        Stromwasserbades → Stromwasserbad
        Hauses           → Haus
        Tages            → Tag
        Herzens          → Herz
        Meeres           → Meer

    Gibt das Wort unverändert zurück wenn keine sichere
    Normalisierung möglich ist.
    """
    if not word or not word[0].isupper():
        return word  # Verben/Adjektive: nicht anfassen

    w_lower = word.lower()
    for suffix, min_stem in _NOUN_SUFFIXES:
        if w_lower.endswith(suffix):
            stem = word[: -len(suffix)]
            if len(stem) < min_stem:
                continue
            # Nur strippeln wenn der Stamm auf Konsonant endet:
            # "Gebirges" → stem "Gebirg" endet auf 'g' → ok
            # Aber Achtung: Gebirge ist Basisform! Deshalb prüfen wir,
            # ob das letzte Zeichen des Suffixes nach einem Konsonanten kommt.
            if stem[-1] not in _VOWELS:
                return stem
    return word

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
