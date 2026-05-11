import unittest

from core.transforms import apply_case_guarantee, inject_digit, inject_special_char


class RecordingRng:
    def __init__(self, values):
        self.values = list(values)
        self.bounds = []

    def __call__(self, upper_bound):
        self.bounds.append(upper_bound)
        return self.values.pop(0)


class InjectDigitTests(unittest.TestCase):
    def test_syllable_injection_uses_global_syllable_count(self):
        words = ["alpha", "betagamma"]
        syllables = {
            "alpha": ["al", "pha"],
            "betagamma": ["be", "ta", "gam", "ma"],
        }
        rng = RecordingRng([4, 8])

        result = inject_digit(
            words,
            "inject_syllable",
            rng,
            syllables_map=syllables,
            original_words=words,
        )

        self.assertEqual(result, ["alpha", "betagam8ma"])
        self.assertEqual(rng.bounds, [6, 10])

    def test_syllable_injection_falls_back_to_word_when_no_map_exists(self):
        words = ["alpha", "beta"]
        rng = RecordingRng([1, 7])

        result = inject_digit(words, "inject_syllable", rng)

        self.assertEqual(result, ["alpha", "beta7"])
        self.assertEqual(rng.bounds, [2, 10])


class InjectSpecialCharTests(unittest.TestCase):
    RULES = [("a", "@", 1), ("s", "$", 1)]

    def test_replace_uses_special_replacement_table(self):
        words = ["saga", "beta"]
        rng = RecordingRng([0])

        result = inject_special_char(words, "replace", rng, rules=self.RULES)

        self.assertEqual(result, ["$aga", "beta"])
        self.assertEqual(rng.bounds, [4])

    def test_syllable_injection_uses_global_syllable_count(self):
        words = ["alpha", "betagamma"]
        syllables = {
            "alpha": ["al", "pha"],
            "betagamma": ["be", "ta", "gam", "ma"],
        }
        rng = RecordingRng([4, 1])

        result = inject_special_char(
            words,
            "inject_syllable",
            rng,
            rules=self.RULES,
            syllables_map=syllables,
            original_words=words,
        )

        self.assertEqual(result, ["alpha", "betagam$ma"])
        self.assertEqual(rng.bounds, [6, 2])

    def test_word_end_injection_adds_special_to_random_word(self):
        words = ["alpha", "beta"]
        rng = RecordingRng([0, 1])

        result = inject_special_char(words, "inject_word_end", rng, rules=self.RULES)

        self.assertEqual(result, ["alpha", "beta@"])
        self.assertEqual(rng.bounds, [2, 2])

    def test_phrase_injection_adds_special_as_own_token(self):
        words = ["alpha", "beta"]
        rng = RecordingRng([1, 0])

        result = inject_special_char(words, "inject_phrase", rng, rules=self.RULES)

        self.assertEqual(result, ["$", "alpha", "beta"])
        self.assertEqual(rng.bounds, [2, 2])


class CaseGuaranteeTests(unittest.TestCase):
    def test_does_not_expand_eszett_to_double_s(self):
        words = ["Großsägewerk"]
        rng = RecordingRng([2])

        result = apply_case_guarantee(words, "original", rng)

        self.assertEqual(result, ["GrOßsägewerk"])
        self.assertEqual(rng.bounds, [11])


if __name__ == "__main__":
    unittest.main()
