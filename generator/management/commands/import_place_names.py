"""
Importiert deutsche Ortsnamen aus dem GeoNames-Dump und legt sie
als BannedWord (reason='ortsname') in der Datenbank ab.

Quelle: http://download.geonames.org/export/dump/DE.zip
Format: Tab-separierte Felder, Spalte 1 = Name, Spalte 3 = alternativer Name

Auch: AT (Österreich), CH (Schweiz), LI (Liechtenstein) optional.
"""
import io
import urllib.request
import zipfile
from django.core.management.base import BaseCommand
from django.db import transaction
from generator.models import BanReason, BannedWord

GEONAMES_URLS = {
    "DE": "https://download.geonames.org/export/dump/DE.zip",
    "AT": "https://download.geonames.org/export/dump/AT.zip",
    "CH": "https://download.geonames.org/export/dump/CH.zip",
}

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
    help = "Importiert Ortsnamen (DE/AT/CH) als BannedWords aus GeoNames."

    def add_arguments(self, parser):
        parser.add_argument("--countries", nargs="+", default=["DE"],
                            choices=list(GEONAMES_URLS.keys()),
                            help="Ländercodes (Standard: DE)")
        parser.add_argument("--dry-run",   action="store_true")
        parser.add_argument("--min-len",   type=int, default=3,
                            help="Mindestlänge eines Ortsnamens (Standard: 3)")

    def handle(self, *args, **options):
        dry      = options["dry_run"]
        min_len  = options["min_len"]
        countries = options["countries"]

        if dry:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Keine Änderungen."))

        reason, _ = BanReason.objects.get_or_create(
            name="ortsname",
            defaults={"description": "Ortsname aus GeoNames-Datenbank"},
        )

        all_names: set[str] = set()

        for country in countries:
            self.stdout.write(f"Lade {country} von GeoNames …")
            names = self._fetch_names(GEONAMES_URLS[country], country, min_len)
            self.stdout.write(f"  {len(names):,} Ortsnamen gefunden")
            all_names.update(names)

        self.stdout.write(f"Gesamt einzigartig: {len(all_names):,}")

        if dry:
            sample = sorted(all_names)[:20]
            self.stdout.write("Beispiele: " + ", ".join(sample))
            return

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

    def _fetch_names(self, url: str, country: str, min_len: int) -> set[str]:
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Fehler beim Download: {e}"))
            return set()

        names: set[str] = set()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            filename = f"{country}.txt"
            with zf.open(filename) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8").rstrip("\n")
                    parts = line.split("\t")
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
                        if len(name) >= min_len and name.replace("-", "").replace(" ", "").isalpha():
                            names.add(name)
        return names
