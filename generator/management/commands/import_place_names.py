"""
Importiert Ortsnamen aus lokalen GeoNames-Dumps und legt sie
als BannedWord (reason='ortsname') in der Datenbank ab.

Erwartete lokale Dateien: data/geonames/DE.zip oder data/geonames/DE.txt
Format: Tab-separierte Felder, Spalte 1 = Name, Spalte 3 = alternativer Name

Auch: AT (Österreich), CH (Schweiz), LI (Liechtenstein) optional.
"""
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from generator.models import BanReason, BannedWord

DEFAULT_GEONAMES_DIR = settings.BASE_DIR / "data" / "geonames"
COUNTRIES = ("DE", "AT", "CH", "LI")

# GeoNames feature codes die Ortsnamen bezeichnen
# https://www.geonames.org/export/codes.html
PLACE_FEATURE_CODES = frozenset({
    "PPL",   # populated place
    "PPLA",  "PPLA2", "PPLA3", "PPLA4",  # seat of first/second/third/fourth-order admin div
    "PPLC",  # capital of a political entity
    "PPLF",  # farm village
    "PPLG",  # seat of government
    "PPLL",  # populated locality
    "PPLQ",  # abandoned populated place
    "PPLR",  # religious populated place
    "PPLS",  # populated places
    "PPLW",  # destroyed populated place
    "PPLX",  # section of populated place
    "STLMT", # israeli settlement
    "ADM1",  "ADM2", "ADM3", "ADM4",  # administrative divisions
})


class Command(BaseCommand):
    help = "Importiert Ortsnamen (DE/AT/CH/LI) aus lokalen GeoNames-Dumps."

    def add_arguments(self, parser):
        parser.add_argument("--countries", nargs="+", default=["DE"],
                            choices=COUNTRIES,
                            help="Ländercodes (Standard: DE)")
        parser.add_argument("--source-dir", default=str(DEFAULT_GEONAMES_DIR),
                            help="Verzeichnis mit lokalen GeoNames-Dumps")
        parser.add_argument("--dry-run",   action="store_true")
        parser.add_argument("--min-len",   type=int, default=3,
                            help="Mindestlänge eines Ortsnamens (Standard: 3)")

    def handle(self, *args, **options):
        dry      = options["dry_run"]
        min_len  = options["min_len"]
        countries = options["countries"]
        source_dir = Path(options["source_dir"]).expanduser()

        if dry:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Keine Änderungen."))

        all_names: set[str] = set()

        for country in countries:
            self.stdout.write(f"Lade {country} aus {source_dir} …")
            names = self._load_names(source_dir, country, min_len)
            self.stdout.write(f"  {len(names):,} Ortsnamen gefunden")
            all_names.update(names)

        self.stdout.write(f"Gesamt einzigartig: {len(all_names):,}")

        if dry:
            sample = sorted(all_names)[:20]
            self.stdout.write("Beispiele: " + ", ".join(sample))
            return

        reason, _ = BanReason.objects.get_or_create(
            name="ortsname",
            defaults={"description": "Ortsname aus lokaler GeoNames-Kopie"},
        )

        # Bestehende Banned Words (ortsname) holen um Duplikate zu sparen
        existing = set(
            BannedWord.objects.filter(reason=reason).values_list("word", flat=True)
        )
        new_names = {n.lower() for n in all_names} - existing
        self.stdout.write(f"Neu hinzuzufügen: {len(new_names):,}")

        CHUNK = 500
        names_list = list(new_names)
        created = 0
        for i in range(0, len(names_list), CHUNK):
            chunk = names_list[i:i + CHUNK]
            with transaction.atomic():
                objs = [BannedWord(word=w, reason=reason) for w in chunk]
                BannedWord.objects.bulk_create(objs, ignore_conflicts=True)
                created += len(chunk)

        self.stdout.write(self.style.SUCCESS(
            f"✓ {created:,} Ortsnamen als BannedWord gespeichert."
        ))

    def _load_names(self, source_dir: Path, country: str, min_len: int) -> set[str]:
        zip_path = source_dir / f"{country}.zip"
        txt_path = source_dir / f"{country}.txt"

        if zip_path.exists():
            return self._load_zip(zip_path, country, min_len)
        if txt_path.exists():
            with txt_path.open(encoding="utf-8") as f:
                return self._parse_lines(f, min_len)
        raise CommandError(
            "Lokaler GeoNames-Dump nicht gefunden: "
            f"{zip_path} oder {txt_path}. Lege die Datei dort ab oder nutze --source-dir."
        )

    def _load_zip(self, zip_path: Path, country: str, min_len: int) -> set[str]:
        with zipfile.ZipFile(zip_path) as zf:
            filename = f"{country}.txt"
            if filename not in zf.namelist():
                raise CommandError(f"{zip_path} enthält keine Datei {filename}.")
            with zf.open(filename) as f:
                return self._parse_lines(
                    (raw_line.decode("utf-8") for raw_line in f),
                    min_len,
                )

    def _parse_lines(self, lines, min_len: int) -> set[str]:
        names: set[str] = set()
        for line in lines:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            feature_code = parts[7]
            if feature_code not in PLACE_FEATURE_CODES:
                continue
            # Haupt- und Alternativnamen
            main_name = parts[1].strip()
            alt_names = parts[3].strip()

            for name in [main_name] + (alt_names.split(",") if alt_names else []):
                name = name.strip()
                normalized = name.replace("-", "").replace(" ", "")
                if len(name) >= min_len and normalized.isalpha():
                    names.add(name)
        return names
