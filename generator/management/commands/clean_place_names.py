"""
Löscht Wörter aus dem Wortbestand die als Ortsnamen (BannedWord reason=ortsname)
markiert sind. Vergleich case-insensitiv.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from generator.models import BannedWord, Word


class Command(BaseCommand):
    help = "Entfernt Ortsnamen aus dem Wortbestand."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",  action="store_true")
        parser.add_argument("--verbose",  action="store_true")

    def handle(self, *args, **options):
        dry     = options["dry_run"]
        verbose = options["verbose"]

        if dry:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Keine Änderungen."))

        banned = set(
            BannedWord.objects
            .filter(reason__name="ortsname")
            .values_list("word", flat=True)
        )
        self.stdout.write(f"Ortsnamen in Ban-Liste: {len(banned):,}")

        # Case-insensitiver Abgleich: Wörter deren Kleinschreibung gebannt ist
        to_delete = list(
            Word.objects
            .filter(word__iregex=r"^[A-ZÄÖÜ]")   # nur Substantive (Großschreibung)
            .values_list("id", "word")
        )

        hit_ids = [
            wid for wid, word in to_delete
            if word.lower() in banned
        ]

        self.stdout.write(f"Treffer im Wortbestand: {len(hit_ids):,}")

        if verbose:
            hit_words = [w for _, w in to_delete if w.lower() in banned]
            for w in sorted(hit_words)[:30]:
                self.stdout.write(f"  {w}")
            if len(hit_words) > 30:
                self.stdout.write(f"  … und {len(hit_words) - 30} weitere")

        if not dry and hit_ids:
            CHUNK = 5000
            deleted = 0
            for i in range(0, len(hit_ids), CHUNK):
                with transaction.atomic():
                    deleted += Word.objects.filter(id__in=hit_ids[i:i + CHUNK]).delete()[0]
            self.stdout.write(self.style.SUCCESS(f"✓ {deleted:,} Ortsnamen aus Wortbestand gelöscht."))
