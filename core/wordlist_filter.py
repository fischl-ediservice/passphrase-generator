"""
Filterlogik für deutsche Rohlisten. Kein Framework-Import.
"""
import re
from dataclasses import dataclass, field

from core.phonetics import SyllableAnalyzer
from core.transforms import normalize_german_word


@dataclass
class FilterConfig:
    min_length:          int = 4
    max_length:          int = 30
    allowed_extra_chars: str = "äöüÄÖÜß"
    min_unique_chars:    int = 3
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
        self._compiled  = [re.compile(p) for p in self.cfg.reject_patterns]
        self._syllables = SyllableAnalyzer(pyphen_lang)

    def filter_lines(self, lines: list[str]) -> dict:
        accepted, rejected = [], []
        seen: set[str] = set()
        for raw in lines:
            word = raw.strip()
            if not word:
                continue
            # Normalisieren vor der Bewertung — flektierte Formen auf Grundform
            word = normalize_german_word(word)
            if word in seen:
                rejected.append((word, "duplikat_nach_normalisierung"))
                continue
            ok, reason = self._evaluate(word)
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

    def _evaluate(self, word: str) -> tuple[bool, str]:
        if len(word) < self.cfg.min_length:
            return False, f"zu_kurz ({len(word)})"
        if len(word) > self.cfg.max_length:
            return False, f"zu_lang ({len(word)})"
        if not self._only_allowed_chars(word):
            return False, "unerlaubte_zeichen"
        for pat in self._compiled:
            if pat.search(word):
                return False, f"pattern:{pat.pattern[:40]}"
        if len(set(word.lower())) < self.cfg.min_unique_chars:
            return False, "zu_wenig_unique_zeichen"
        w_lower = word.lower()
        if word[0].islower():
            for suffix in self.cfg.flexion_suffixes:
                if w_lower.endswith(suffix) and len(word) > len(suffix) + 2:
                    if w_lower not in self.cfg.baseform_whitelist:
                        return False, f"flexion:{suffix}"
        if word[0].isupper():
            for suffix in self.cfg.proper_noun_suffixes:
                if w_lower.endswith(suffix) and len(word) > len(suffix) + 3:
                    return False, f"eigenname:{suffix}"
        return True, ""

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
            "reverse_suitable":      len(word) <= 8,
        }

    def _only_allowed_chars(self, word: str) -> bool:
        for ch in word:
            if ch.isalpha():
                continue
            if ch in self.cfg.allowed_extra_chars:
                continue
            return False
        return True


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
