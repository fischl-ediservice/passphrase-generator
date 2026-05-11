"""
Filterlogik für deutsche Rohlisten. Kein Framework-Import.
"""
import re
import unicodedata
from dataclasses import dataclass, field

from core.phonetics import SyllableAnalyzer
from core.transforms import normalize_german_word

_REVERSE_PLURAL_UMLAUT = str.maketrans({
    "ä": "a", "ö": "o", "ü": "u",
    "Ä": "A", "Ö": "O", "Ü": "U",
})


def _reverse_plural_umlaut(word: str) -> str:
    return word.translate(_REVERSE_PLURAL_UMLAUT)


_PROTECTED_GERMAN_CHARS = str.maketrans({
    "ä": "\ue000", "ö": "\ue001", "ü": "\ue002",
    "Ä": "\ue003", "Ö": "\ue004", "Ü": "\ue005",
    "ß": "\ue006",
})
_RESTORE_GERMAN_CHARS = str.maketrans({
    "\ue000": "ä", "\ue001": "ö", "\ue002": "ü",
    "\ue003": "Ä", "\ue004": "Ö", "\ue005": "Ü",
    "\ue006": "ß",
})


def normalize_import_word(word: str) -> str:
    """Normalize source words while preserving German umlauts and ß."""
    protected = word.translate(_PROTECTED_GERMAN_CHARS)
    decomposed = unicodedata.normalize("NFKD", protected)
    without_accents = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    )
    restored = without_accents.translate(_RESTORE_GERMAN_CHARS)
    return normalize_german_word(restored)


@dataclass
class FilterConfig:
    min_length:          int = 4
    max_length:          int = 30
    allowed_extra_chars: str = "äöüÄÖÜß"
    min_unique_chars:    int = 3
    require_capitalized: bool = True
    banned_place_words:  frozenset = field(default_factory=frozenset)
    blocked_words:       frozenset = field(default_factory=frozenset)
    blocked_word_parts:  frozenset = field(default_factory=frozenset)
    blocked_case_sensitive_parts: frozenset = field(default_factory=frozenset)
    blocked_word_suffixes: frozenset = field(default_factory=frozenset)
    adult_word_parts:    frozenset = field(default_factory=frozenset)
    adult_case_sensitive_parts: frozenset = field(default_factory=frozenset)
    adult_word_suffixes: frozenset = field(default_factory=frozenset)
    technical_word_parts: frozenset = field(default_factory=frozenset)
    technical_case_sensitive_parts: frozenset = field(default_factory=frozenset)
    reject_patterns: list = field(default_factory=lambda: [
        r"^[A-ZÄÖÜ]{2,}$",
        r"\d",
        r"[-/\.]",
        r"[(){}\[\]<>\"\'@#$%^&*+=|~`]",
        r"^[a-zäöüß].*(est|tet|nde|ndem|nden|nder|ndes)$",
    ])
    flexion_suffixes: tuple = (
        "end", "ende", "endem", "enden", "ender", "endes",
        "test", "tet", "ten", "est", "et",
    )
    proper_noun_suffixes: tuple = (
        "erin", "erinnen", "ern", "ers",
        "burg", "stadt", "dorf", "bach",
        "heim", "hausen", "kirchen", "furt",
        "ingen", "stedt", "itz", "ow",
    )
    baseform_whitelist: frozenset = field(default_factory=lambda: frozenset({
        "ende", "legende", "wende", "binde", "rinde", "linde",
        "grenze", "sekunde", "stunde", "runde", "wunde", "kunde",
        "wunder", "kinder", "felder", "bilder", "lieder", "brüder",
        "mütter", "väter", "länder", "wälder", "bänder",
    }))


class WordlistFilter:
    def __init__(self, config: FilterConfig | None = None, pyphen_lang: str = "de_DE"):
        self.cfg        = config or FilterConfig()
        if self.cfg.banned_place_words:
            self.cfg.banned_place_words = frozenset(
                word.lower() for word in self.cfg.banned_place_words
            )
        if self.cfg.blocked_words:
            self.cfg.blocked_words = frozenset(
                word.lower() for word in self.cfg.blocked_words
            )
        if self.cfg.blocked_word_parts:
            self.cfg.blocked_word_parts = frozenset(
                part.lower() for part in self.cfg.blocked_word_parts
            )
        if self.cfg.blocked_word_suffixes:
            self.cfg.blocked_word_suffixes = frozenset(
                suffix.lower() for suffix in self.cfg.blocked_word_suffixes
            )
        if self.cfg.adult_word_parts:
            self.cfg.adult_word_parts = frozenset(
                part.lower() for part in self.cfg.adult_word_parts
            )
        if self.cfg.adult_word_suffixes:
            self.cfg.adult_word_suffixes = frozenset(
                suffix.lower() for suffix in self.cfg.adult_word_suffixes
            )
        if self.cfg.technical_word_parts:
            self.cfg.technical_word_parts = frozenset(
                part.lower() for part in self.cfg.technical_word_parts
            )
        self._compiled  = [re.compile(p) for p in self.cfg.reject_patterns]
        self._syllables = SyllableAnalyzer(pyphen_lang)

    def filter_lines(self, lines: list[str]) -> dict:
        accepted, rejected = [], []
        seen: set[str] = set()
        prepared: list[str] = []
        for raw in lines:
            word = raw.strip()
            if not word:
                continue
            # Normalisieren vor der Bewertung — flektierte Formen auf Grundform
            prepared.append(normalize_import_word(word))

        source_words = frozenset(prepared)

        for word in prepared:
            if word in seen:
                rejected.append((word, "duplikat_nach_normalisierung"))
                continue
            ok, reason = self._evaluate(word, source_words)
            if ok:
                seen.add(word)
                accepted.append(self._enrich(word))
            else:
                rejected.append((word, reason))
        stats = {
            "total_input":     len(lines),
            "accepted":        len(accepted),
            "rejected":        len(rejected),
            "acceptance_rate": round(len(accepted) / max(len(lines), 1) * 100, 2),
        }
        return {"accepted": accepted, "rejected": rejected, "stats": stats}

    def _evaluate(self, word: str, source_words: frozenset[str] | None = None) -> tuple[bool, str]:
        if len(word) < self.cfg.min_length:
            return False, f"zu_kurz ({len(word)})"
        if len(word) > self.cfg.max_length:
            return False, f"zu_lang ({len(word)})"
        if not self._only_allowed_chars(word):
            return False, "unerlaubte_zeichen"
        if self.cfg.require_capitalized and word[0].islower():
            return False, "kein_standard_nomen"
        if word.lower() in self.cfg.blocked_words:
            return False, "lokale_sperrliste"
        sensitive_part = self._blocked_word_part(word)
        if sensitive_part:
            return False, f"sensibler_bestandteil:{sensitive_part}"
        for pat in self._compiled:
            if pat.search(word):
                return False, f"pattern:{pat.pattern[:40]}"
        if len(set(word.lower())) < self.cfg.min_unique_chars:
            return False, "zu_wenig_unique_zeichen"

        place_base = self._banned_place_base(word)
        if place_base:
            return False, f"ortsname:{place_base}"

        if source_words:
            base = self._known_inflection_base(word, source_words)
            if base:
                return False, f"flexion_basis:{base}"

            proper_base = self._known_proper_base(word, source_words)
            if proper_base:
                return False, f"eigenname_basis:{proper_base}"

        w_lower = word.lower()
        if word[0].islower():
            for suffix in self.cfg.flexion_suffixes:
                if w_lower.endswith(suffix) and len(word) > len(suffix) + 2:
                    if w_lower not in self.cfg.baseform_whitelist:
                        return False, f"flexion:{suffix}"
        if word[0].isupper() and w_lower.endswith("ens") and len(word) >= 4:
            if w_lower not in self.cfg.baseform_whitelist:
                return False, "flexion:ens"
        if word[0].isupper():
            for suffix in self.cfg.proper_noun_suffixes:
                if w_lower.endswith(suffix) and len(word) >= len(suffix) + 3:
                    return False, f"eigenname:{suffix}"
        return True, ""

    def _blocked_word_part(self, word: str) -> str | None:
        return _matching_word_part(
            word,
            self.cfg.blocked_word_parts,
            self.cfg.blocked_case_sensitive_parts,
        ) or _matching_word_suffix(word, self.cfg.blocked_word_suffixes)

    def _adult_word_part(self, word: str) -> str | None:
        return _matching_word_part(
            word,
            self.cfg.adult_word_parts,
            self.cfg.adult_case_sensitive_parts,
        ) or _matching_word_suffix(word, self.cfg.adult_word_suffixes)

    def _is_adult_only(self, word: str) -> bool:
        return self._adult_word_part(word) is not None

    def _technical_word_part(self, word: str) -> str | None:
        return _matching_word_part(
            word,
            self.cfg.technical_word_parts,
            self.cfg.technical_case_sensitive_parts,
        )

    def _is_technical(self, word: str) -> bool:
        return self._technical_word_part(word) is not None

    def _banned_place_base(self, word: str) -> str | None:
        places = self.cfg.banned_place_words
        if not places:
            return None
        lower = word.lower()
        if lower in places:
            return lower
        if lower.endswith("s") and lower[:-1] in places:
            return lower[:-1]
        if lower.endswith("er") and lower[:-2] in places:
            return lower[:-2]
        return None

    def _known_inflection_base(
        self,
        word: str,
        source_words: frozenset[str],
    ) -> str | None:
        if not word or not word[0].isupper():
            return None
        for base in self._inflection_base_candidates(word):
            if base != word and base in source_words:
                return base
        return None

    def _known_proper_base(
        self,
        word: str,
        source_words: frozenset[str],
    ) -> str | None:
        if not word or not word[0].isupper():
            return None
        lower = word.lower()
        candidates: list[str] = []
        if lower.endswith("s"):
            candidates.append(word[:-1])
        if lower.endswith("er"):
            candidates.append(word[:-2])

        # Orts-/Eigennamen-Komposita wie "Prerowstrom" erwischen, wenn die
        # Basisform ebenfalls in der Rohdatei steht.
        for end in range(self.cfg.min_length, max(self.cfg.min_length, len(word) - 2)):
            candidates.append(word[:end])

        for base in candidates:
            if (
                base
                and base != word
                and base in source_words
                and self._looks_like_proper_name(base)
            ):
                return base
        return None

    def _looks_like_proper_name(self, word: str) -> bool:
        lower = word.lower()
        if lower in self.cfg.banned_place_words:
            return True
        return any(
            lower.endswith(suffix) and len(word) >= len(suffix) + 3
            for suffix in self.cfg.proper_noun_suffixes
        )

    def _inflection_base_candidates(self, word: str) -> list[str]:
        lower = word.lower()
        candidates: list[str] = []

        def add(candidate: str) -> None:
            if len(candidate) >= self.cfg.min_length and candidate not in candidates:
                candidates.append(candidate)

        normalized = normalize_german_word(word)
        if normalized != word:
            add(normalized)

        if lower.endswith("ern"):
            add(word[:-3])
            add(word[:-1])
        if lower.endswith("ens"):
            add(word[:-3])
            add(word[:-2])
        if lower.endswith("en"):
            add(word[:-2])
            add(word[:-1])
        elif lower.endswith("n"):
            add(word[:-1])
        if lower.endswith("e"):
            stem = word[:-1]
            add(stem)
            add(_reverse_plural_umlaut(stem))
        if lower.endswith("s"):
            add(word[:-1])

        return candidates

    def _enrich(self, word: str) -> dict:
        parts    = self._syllables.split(word)
        suitable = self._syllables.is_shuffle_suitable(word)
        anchored = self._syllables.all_anchored(word)
        return {
            "word":                  word,
            "word_length":           len(word),
            "syllables":             parts,
            "syllable_count":        len(parts),
            "syllable_shuffle_mode": "rotate" if (suitable and anchored) else "unsuitable",
            "syllables_anchored":    anchored,
            "is_compound":           any(c.isupper() for c in word[1:]),
            "is_technical":          self._is_technical(word),
            "reverse_suitable":      len(word) <= 8,
            "adult_only":            self._is_adult_only(word),
        }

    def _only_allowed_chars(self, word: str) -> bool:
        for ch in word:
            if ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
                continue
            if ch in self.cfg.allowed_extra_chars:
                continue
            return False
        return True


def _matching_word_part(
    word: str,
    insensitive_parts: frozenset[str],
    case_sensitive_parts: frozenset[str],
) -> str | None:
    lower = word.lower()
    for part in insensitive_parts:
        if part and part in lower:
            return part
    for part in case_sensitive_parts:
        if part and part in word:
            return part
    return None


def _matching_word_suffix(word: str, suffixes: frozenset[str]) -> str | None:
    lower = word.lower()
    for suffix in suffixes:
        if suffix and lower.endswith(suffix):
            return suffix
    return None


def print_filter_stats(result: dict, show_rejected_sample: int = 10) -> None:
    s = result["stats"]
    print(f"\n{'='*52}")
    print(f"  Eingabe:        {s['total_input']:>8} Wörter")
    print(f"  Akzeptiert:     {s['accepted']:>8} Wörter")
    print(f"  Verworfen:      {s['rejected']:>8} Wörter")
    print(f"  Akzeptanzrate:  {s['acceptance_rate']:>7} %")
    print(f"{'='*52}")
    if show_rejected_sample and result["rejected"]:
        print(f"\nBeispiele verworfen (erste {show_rejected_sample}):")
        for word, reason in result["rejected"][:show_rejected_sample]:
            print(f"  {word:<35} → {reason}")
