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


_LETTER_TO_DIGIT: dict[str, str] = {
    'a': '4', 'e': '3', 'i': '1', 'o': '0',
    's': '5', 'b': '6', 't': '7', 'g': '9', 'l': '1',
}

_LETTER_TO_SPECIAL: tuple[tuple[str, str, int], ...] = (
    ("a", "@", 10),
    ("s", "$", 10),
    ("e", "€", 7),
    ("i", "!", 7),
    ("t", "+", 6),
    ("l", "|", 5),
    ("o", "°", 4),
    ("ß", "§", 4),
)


def apply_case_guarantee(words: list[str], case_mode: str, rng_func) -> list[str]:
    """Setzt genau einen zufälligen Buchstaben — immer, kein Retry.
    upper-Modus: einen lowern. Alle anderen: einen uppern."""
    def transformed_char(ch: str) -> str:
        return ch.lower() if case_mode == "upper" else ch.upper()

    candidates = [
        (wi, ci)
        for wi, w in enumerate(words)
        for ci, c in enumerate(w)
        if c.isalpha()
        and len(transformed_char(c)) == 1
    ]
    if not candidates:
        return words
    words = list(words)
    wi, ci = candidates[rng_func(len(candidates))]
    w = words[wi]
    ch = transformed_char(w[ci])
    words[wi] = w[:ci] + ch + w[ci + 1:]
    return words


def inject_digit(
    words: list[str],
    mode: str,
    rng_func,
    syllables_map: dict[str, list[str]] | None = None,
    original_words: list[str] | None = None,
) -> list[str]:
    """
    Fügt genau eine Ziffer ein.

    Modi:
      replace          – einen mappbaren Buchstaben durch Ziffer ersetzen (o→0 …)
      inject_syllable  – zwischen zwei beliebige Silbengrenzen der Phrase (inkl. Wortenden)
      inject_word_end  – ans Ende eines zufälligen Wortes anhängen
      inject_phrase    – als eigenes Token an Start oder Ende der Phrase
    """
    words = list(words)

    if mode == "replace":
        candidates = [
            (wi, ci, _LETTER_TO_DIGIT[c.lower()])
            for wi, w in enumerate(words)
            for ci, c in enumerate(w)
            if c.lower() in _LETTER_TO_DIGIT
        ]
        if candidates:
            wi, ci, d = candidates[rng_func(len(candidates))]
            w = words[wi]
            words[wi] = w[:ci] + d + w[ci + 1:]

    elif mode == "inject_syllable":
        boundary = _pick_syllable_boundary(words, syllables_map, original_words, rng_func)
        digit = str(rng_func(10))
        if boundary:
            wi, char_pos = boundary
            w = words[wi]
            words[wi] = w[:char_pos] + digit + w[char_pos:]
        else:
            # Fallback: ans Wortende
            wi = rng_func(len(words))
            words[wi] += digit

    elif mode == "inject_word_end":
        digit = str(rng_func(10))
        wi = rng_func(len(words))
        words[wi] += digit

    elif mode == "inject_phrase":
        digit = str(rng_func(10))
        if rng_func(2) == 0:
            words.insert(0, digit)
        else:
            words.append(digit)

    return words


def inject_special_char(
    words: list[str],
    mode: str,
    rng_func,
    rules: list[tuple[str, str, int]] | None = None,
    syllables_map: dict[str, list[str]] | None = None,
    original_words: list[str] | None = None,
) -> list[str]:
    """
    Fügt genau ein Sonderzeichen ein oder ersetzt genau einen geeigneten Buchstaben.

    Modi:
      replace          – einen mappbaren Buchstaben durch Sonderzeichen ersetzen (a→@ …)
      inject_syllable  – zwischen zwei beliebige Silbengrenzen der Phrase
      inject_word_end  – ans Ende eines zufälligen Wortes anhängen
      inject_phrase    – als eigenes Token an Start oder Ende der Phrase
    """
    if mode == "off":
        return words

    words = list(words)
    replacement_rules = rules or list(_LETTER_TO_SPECIAL)

    if mode == "replace":
        candidates = [
            (wi, ci, target, weight)
            for wi, w in enumerate(words)
            for ci, c in enumerate(w)
            for source, target, weight in replacement_rules
            if c.lower() == source
        ]
        if candidates:
            total_weight = sum(weight for *_, weight in candidates)
            roll = rng_func(total_weight)
            cumulative = 0
            for wi, ci, target, weight in candidates:
                cumulative += weight
                if roll < cumulative:
                    word = words[wi]
                    words[wi] = word[:ci] + target + word[ci + 1:]
                    break

    elif mode == "inject_syllable":
        boundary = _pick_syllable_boundary(words, syllables_map, original_words, rng_func)
        special = _pick_special_char(replacement_rules, rng_func)
        if boundary:
            wi, char_pos = boundary
            word = words[wi]
            words[wi] = word[:char_pos] + special + word[char_pos:]
        else:
            wi = rng_func(len(words))
            words[wi] += special

    elif mode == "inject_word_end":
        special = _pick_special_char(replacement_rules, rng_func)
        wi = rng_func(len(words))
        words[wi] += special

    elif mode == "inject_phrase":
        special = _pick_special_char(replacement_rules, rng_func)
        if rng_func(2) == 0:
            words.insert(0, special)
        else:
            words.append(special)

    return words


def _pick_special_char(rules: list[tuple[str, str, int]], rng_func) -> str:
    targets = [(target, weight) for _, target, weight in rules]
    total_weight = sum(weight for _, weight in targets)
    roll = rng_func(total_weight)
    cumulative = 0
    for target, weight in targets:
        cumulative += weight
        if roll < cumulative:
            return target
    return targets[-1][0]


def _pick_syllable_boundary(
    words: list[str],
    syllables_map: dict[str, list[str]] | None,
    original_words: list[str] | None,
    rng_func,
) -> tuple[int, int] | None:
    entries: list[tuple[int, str, list[str]]] = []
    total_syllables = 0
    orig = original_words or words

    for wi, (word, orig_word) in enumerate(zip(words, orig)):
        syllables = (syllables_map or {}).get(orig_word) or [orig_word]
        entries.append((wi, word, syllables))
        total_syllables += len(syllables)

    if total_syllables == 0:
        return None

    target = rng_func(total_syllables)
    seen = 0
    for wi, word, syllables in entries:
        if target < seen + len(syllables):
            syllable_index = target - seen
            char_pos = sum(len(s) for s in syllables[: syllable_index + 1])
            return wi, min(char_pos, len(word))
        seen += len(syllables)
    return None


def shuffle_syllables(word: str, syllables: list[str], rng_func) -> str:
    """
    Fisher-Yates shuffle der Silben eines Wortes.
    Gibt das Wort unverändert zurück wenn < 2 Silben vorhanden.
    """
    if len(syllables) < 2:
        return word
    parts = list(syllables)
    n = len(parts)
    for i in range(n - 1, 0, -1):
        j = rng_func(i + 1)
        parts[i], parts[j] = parts[j], parts[i]
    return "".join(parts)


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
