"""
Silbenanalyse via pyphen. Einzige externe Abhängigkeit: pyphen.
"""
import pyphen

VOWELS = frozenset("aeiouäöüyAEIOUÄÖÜY")


class SyllableAnalyzer:
    def __init__(self, pyphen_lang: str = "de_DE"):
        self._dic = pyphen.Pyphen(lang=pyphen_lang)

    def split(self, word: str) -> list[str]:
        hyphenated = self._dic.inserted(word, hyphen="·")
        if not hyphenated:
            return [word]
        return hyphenated.split("·")

    def count(self, word: str) -> int:
        return len(self.split(word))

    def all_anchored(self, word: str) -> bool:
        return all(
            any(ch in VOWELS for ch in syllable)
            for syllable in self.split(word)
        )

    def is_shuffle_suitable(self, word: str) -> bool:
        parts = self.split(word)
        return (
            len(parts) >= 2
            and all(len(p) >= 2 for p in parts)
            and self.all_anchored(word)
        )
