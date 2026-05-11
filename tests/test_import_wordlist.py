import os
import tempfile
import unittest
from pathlib import Path

try:
    import pyphen  # noqa: F401
except ModuleNotFoundError:
    raise unittest.SkipTest("pyphen is not installed in this environment")

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        raise unittest.SkipTest("psycopg is not installed in this environment")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "passphrase_generator.settings")

import django
from django.core.management.base import CommandError
from django.core.exceptions import ImproperlyConfigured

try:
    django.setup()
except ImproperlyConfigured as exc:
    raise unittest.SkipTest(str(exc))

from generator.management.commands.import_wordlist import Command


class ImportWordlistTests(unittest.TestCase):
    def test_command_has_no_remote_url_option(self):
        parser = Command().create_parser("manage.py", "import_wordlist")
        dests = {action.dest for action in parser._actions}

        self.assertIn("file", dests)
        self.assertNotIn("url", dests)

    def test_load_source_reads_local_file(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "words.txt"
            path.write_text("Alpha\nBeta\n", encoding="utf-8")

            lines = command._load_source(path)

        self.assertEqual(lines, ["Alpha\n", "Beta\n"])

    def test_missing_local_source_raises_command_error(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                command._load_source(Path(tmp) / "missing.txt")

    def test_load_reject_words_reads_local_case_insensitive_list(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reject.txt"
            path.write_text("# Kommentar\nNeuroute\n\nSeiher\n", encoding="utf-8")

            words = command._load_reject_words(path)

        self.assertEqual(words, frozenset({"neuroute", "seiher"}))

    def test_missing_reject_file_is_empty(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            words = command._load_reject_words(Path(tmp) / "missing.txt")

        self.assertEqual(words, frozenset())

    def test_load_sensitive_terms_splits_case_sensitive_entries(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sensitive.txt"
            path.write_text(
                (
                    "# Kommentar\nhard:Nazi\nhard:Hitler\nhard:case:SS\n"
                    "hard_suffix:sau\nadult:Scheiß\nadult_suffix:fix\n"
                ),
                encoding="utf-8",
            )

            (
                insensitive,
                case_sensitive,
                hard_suffixes,
                adult,
                adult_case,
                adult_suffixes,
            ) = command._load_sensitive_terms(path)

        self.assertEqual(insensitive, frozenset({"nazi", "hitler"}))
        self.assertEqual(case_sensitive, frozenset({"SS"}))
        self.assertEqual(hard_suffixes, frozenset({"sau"}))
        self.assertEqual(adult, frozenset({"scheiß"}))
        self.assertEqual(adult_case, frozenset())
        self.assertEqual(adult_suffixes, frozenset({"fix"}))

    def test_missing_sensitive_terms_file_is_empty(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            (
                insensitive,
                case_sensitive,
                hard_suffixes,
                adult,
                adult_case,
                adult_suffixes,
            ) = command._load_sensitive_terms(Path(tmp) / "missing.txt")

        self.assertEqual(insensitive, frozenset())
        self.assertEqual(case_sensitive, frozenset())
        self.assertEqual(hard_suffixes, frozenset())
        self.assertEqual(adult, frozenset())
        self.assertEqual(adult_case, frozenset())
        self.assertEqual(adult_suffixes, frozenset())

    def test_load_technical_terms_splits_case_sensitive_entries(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nerd.txt"
            path.write_text("# Kommentar\ncase:BVerf\nBundesamt\n", encoding="utf-8")

            insensitive, case_sensitive = command._load_technical_terms(path)

        self.assertEqual(insensitive, frozenset({"bundesamt"}))
        self.assertEqual(case_sensitive, frozenset({"BVerf"}))


if __name__ == "__main__":
    unittest.main()
