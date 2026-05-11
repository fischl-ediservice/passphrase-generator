"""
Kompatibilitätsimport für ältere generator.wordlist_filter-Nutzer.
Die aktive Filterlogik liegt in core.wordlist_filter.
"""
from core.phonetics import SyllableAnalyzer
from core.wordlist_filter import FilterConfig, WordlistFilter, print_filter_stats

__all__ = [
    "FilterConfig",
    "SyllableAnalyzer",
    "WordlistFilter",
    "print_filter_stats",
]
