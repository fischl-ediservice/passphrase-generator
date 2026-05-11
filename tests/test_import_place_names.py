import os
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "passphrase_generator.settings")

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        raise unittest.SkipTest("psycopg is not installed in this environment")

import django
from django.core.management.base import CommandError
from django.core.exceptions import ImproperlyConfigured

try:
    django.setup()
except ImproperlyConfigured as exc:
    raise unittest.SkipTest(str(exc))

from generator.management.commands.import_place_names import Command


def geonames_line(name: str, alt_names: str, feature_code: str) -> str:
    fields = ["1", name, "ascii", alt_names, "0", "0", "P", feature_code]
    return "\t".join(fields)


class ImportPlaceNamesTests(unittest.TestCase):
    def test_parse_lines_keeps_only_place_names_and_alpha_aliases(self):
        command = Command()
        lines = [
            geonames_line("Berlin", "Spreestadt,Berlin-Alt,City 123", "PPL"),
            geonames_line("Zug", "", "PPL"),
            geonames_line("AB", "", "PPL"),
            geonames_line("Brocken", "", "MT"),
        ]

        names = command._parse_lines(lines, min_len=3)

        self.assertEqual(names, {"Berlin", "Spreestadt", "Berlin-Alt", "Zug"})

    def test_load_names_reads_local_txt_dump(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DE.txt"
            path.write_text(geonames_line("Berlin", "Spreestadt", "PPL"), encoding="utf-8")

            names = command._load_names(Path(tmp), "DE", min_len=3)

        self.assertEqual(names, {"Berlin", "Spreestadt"})

    def test_load_names_reads_local_zip_dump(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DE.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("DE.txt", geonames_line("Berlin", "", "PPL"))

            names = command._load_names(Path(tmp), "DE", min_len=3)

        self.assertEqual(names, {"Berlin"})

    def test_missing_local_dump_raises_command_error(self):
        command = Command()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                command._load_names(Path(tmp), "DE", min_len=3)


if __name__ == "__main__":
    unittest.main()
