import unittest
from unittest.mock import patch

from core.entropy import stride_sample


class StrideSampleTests(unittest.TestCase):
    def test_uses_shrinking_pool_length_for_wraparound(self):
        words = list("abcdefghij")

        with patch("core.entropy.secrets.randbelow", side_effect=[2, 4]):
            result = stride_sample(words, 4)

        self.assertEqual(result, ["c", "i", "f", "d"])

    def test_samples_directly_from_full_pool(self):
        words = list("abcdef")

        with patch("core.entropy.secrets.randbelow", side_effect=[1, 2]):
            result = stride_sample(words, 3)

        self.assertEqual(result, ["b", "f", "e"])


if __name__ == "__main__":
    unittest.main()
