import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "passphrase_generator.settings")

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        raise unittest.SkipTest("psycopg is not installed in this environment")

import django
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

try:
    django.setup()
except ImproperlyConfigured as exc:
    raise unittest.SkipTest(str(exc))

from core.generator import GeneratorConfig
from generator.views import (
    _adult_words_unlocked,
    _get_word_pool,
    _pick_pool_entries,
    clear_word_pool_cache,
)


SOURCE = (
    {
        "word": "Alpha",
        "word_length": 5,
        "syllables": ["Al", "pha"],
        "syllable_shuffle_mode": "rotate",
        "adult_only": False,
        "is_technical": False,
    },
    {
        "word": "Beta",
        "word_length": 4,
        "syllables": ["Be", "ta"],
        "syllable_shuffle_mode": "unsuitable",
        "adult_only": False,
        "is_technical": False,
    },
    {
        "word": "Gamma",
        "word_length": 5,
        "syllables": ["Gam", "ma"],
        "syllable_shuffle_mode": "rotate",
        "adult_only": True,
        "is_technical": False,
    },
    {
        "word": "Delta",
        "word_length": 5,
        "syllables": ["Del", "ta"],
        "syllable_shuffle_mode": "rotate",
        "adult_only": False,
        "is_technical": True,
    },
)


class WordPoolCacheTests(unittest.TestCase):
    def setUp(self):
        clear_word_pool_cache(clear_source=True)

    def tearDown(self):
        clear_word_pool_cache(clear_source=True)

    def test_word_pool_source_is_loaded_once_and_filtered_in_memory(self):
        config = GeneratorConfig(word_count=2)
        with patch("generator.views._query_word_pool_source", return_value=SOURCE) as query:
            first = _get_word_pool(4, 5, config, include_syllables=False)
            second = _get_word_pool(4, 5, config, include_syllables=False)

        self.assertIs(first, second)
        self.assertEqual(first, ("Alpha", "Beta"))
        self.assertEqual(query.call_count, 1)

    def test_syllable_pool_cache_uses_word_and_syllables(self):
        config = GeneratorConfig(word_count=2, digit_mode="inject_syllable")

        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            pool = _get_word_pool(4, 5, config, include_syllables=True)

        self.assertEqual(pool[0], {"word": "Alpha", "syllables": ["Al", "pha"]})

    def test_syllable_shuffle_excludes_unsuitable_words_from_memory_pool(self):
        config = GeneratorConfig(word_count=1, syllable_shuffle_enabled=True)

        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            pool = _get_word_pool(4, 5, config, include_syllables=False)

        self.assertEqual(pool, ("Alpha",))

    def test_adult_words_are_excluded_until_explicitly_unlocked(self):
        config = GeneratorConfig(word_count=2)

        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            default_pool = _get_word_pool(4, 5, config, include_syllables=False)

        clear_word_pool_cache()
        config.include_adult_words = True
        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            adult_pool = _get_word_pool(4, 5, config, include_syllables=False)

        self.assertEqual(default_pool, ("Alpha", "Beta"))
        self.assertEqual(adult_pool, ("Alpha", "Beta", "Gamma"))

    def test_technical_words_are_excluded_until_explicitly_unlocked(self):
        config = GeneratorConfig(word_count=2)

        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            default_pool = _get_word_pool(4, 5, config, include_syllables=False)

        clear_word_pool_cache()
        config.include_technical_words = True
        with patch("generator.views._query_word_pool_source", return_value=SOURCE):
            technical_pool = _get_word_pool(4, 5, config, include_syllables=False)

        self.assertEqual(default_pool, ("Alpha", "Beta"))
        self.assertEqual(technical_pool, ("Alpha", "Beta", "Delta"))

    def test_pool_selection_uses_stride_offsets_in_order(self):
        pool = ("Alpha", "Beta", "Gamma")
        config = GeneratorConfig(word_count=2)

        with patch("generator.views.stride_indices", return_value=[2, 0]):
            entries = _pick_pool_entries(pool, config, include_syllables=False)

        self.assertEqual(entries, ["Gamma", "Alpha"])


class AdultUnlockTests(unittest.TestCase):
    @override_settings(ADULT_WORD_UNLOCK_PASSWORD="elternfrei")
    def test_adult_unlock_requires_matching_password(self):
        self.assertFalse(_adult_words_unlocked({}))
        self.assertTrue(_adult_words_unlocked({"adult_unlock_password": "elternfrei"}))
        with self.assertRaises(ValueError):
            _adult_words_unlocked({"adult_unlock_password": "falsch"})


if __name__ == "__main__":
    unittest.main()
