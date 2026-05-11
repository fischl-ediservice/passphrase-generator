import math
import unittest
from unittest.mock import patch

from core.generator import GeneratorConfig, _pick_words, generate_passphrase


class PickWordsTests(unittest.TestCase):
    def test_uses_full_pool_for_stride_sampling(self):
        words = ["alpha", "beta", "gamma", "delta", "epsilon"]
        config = GeneratorConfig(word_count=3)

        with patch("core.generator.stride_sample", return_value=["gamma", "alpha", "delta"]) as sample:
            result = _pick_words(words, config)

        self.assertEqual(result, ["gamma", "alpha", "delta"])
        sample.assert_called_once_with(words, 3)

    def test_avoid_same_initial_retries_until_initials_are_unique(self):
        words = ["alpha", "atom", "beta", "gamma"]
        config = GeneratorConfig(word_count=2, avoid_same_initial=True)

        with patch(
            "core.generator.stride_sample",
            side_effect=[["alpha", "atom"], ["alpha", "beta"]],
        ) as sample:
            result = _pick_words(words, config)

        self.assertEqual(result, ["alpha", "beta"])
        self.assertEqual(sample.call_count, 2)


class GeneratePassphraseTests(unittest.TestCase):
    def test_entropy_and_pool_size_use_the_full_valid_pool(self):
        words = [f"word{i}" for i in range(10)]
        config = GeneratorConfig(word_count=2, separator="-", case_mode="original")

        with patch("core.generator._pick_words", return_value=["word2", "word7"]):
            with patch("core.generator.apply_case_guarantee", side_effect=lambda w, *_: w):
                result = generate_passphrase(words, config)

        self.assertEqual(result.words, ["word2", "word7"])
        self.assertEqual(result.passphrase, "word2-word7")
        self.assertEqual(result.pool_size, 10)
        self.assertEqual(result.entropy_bits, round(2 * math.log2(10), 2))


if __name__ == "__main__":
    unittest.main()
