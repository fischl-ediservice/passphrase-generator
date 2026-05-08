"""
Normalisiert flektierte Wortformen im bestehenden Wortbestand.

Für Substantive (Großbuchstabe) mit "-es"-Genitiv-Endung:
  "Hauses"           → stem "Haus"         → in DB → löschen
  "Sehnengewebes"    → stem "Sehnengeweb"  → nicht in DB
                     → stem+"e" "Sehnengewebe" → in DB → löschen
  "Sehereignisses"   → stem "Sehereigniss" → nicht in DB
                     → Doppelkonsonant → stem[:-1] "Sehereignis" → in DB → löschen
  "Stromwasserbades" → stem "Stromwasserbad" → in DB → löschen
                       (oder aktualisieren falls nicht vorhanden)
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.transforms import normalize_german_word
from generator.models import Word

_VOWELS = frozenset("aeiouäöüyAEIOUÄÖÜY")


def _candidate_bases(stem: str) -> list[str]:
    """Mögliche Grundformen für einen gegebenen Stamm, längste zuerst."""
    candidates = [stem]
    # Doppelter Endkonsonant (Ergebniss → Ergebnis, Flusss → Fluss)
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in _VOWELS:
        candidates.append(stem[:-1])
    # Stummes -e am Ende (Sehnengeweb → Sehnengewebe)
    candidates.append(stem + "e")
    return candidates


class Command(BaseCommand):
    help = "Normalisiert flektierte deutsche Wortformen in der Datenbank."

    def add_arguments(self, parser):
        parser.add_argument("--min-length", type=int, default=4)
        parser.add_argument("--batch-size", type=int, default=2000)
        parser.add_argument("--dry-run",    action="store_true")
        parser.add_argument("--verbose",    action="store_true")

    def handle(self, *args, **options):
        min_len    = options["min_length"]
        batch_size = options["batch_size"]
        dry        = options["dry_run"]
        verbose    = options["verbose"]

        if dry:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Keine Änderungen werden geschrieben."))

        candidates = (
            Word.objects
            .filter(word__iregex=r"^[A-ZÄÖÜ]")
            .filter(word__iregex=r"es$")
            .values_list("id", "word", "wordlist_id")
        )

        total   = candidates.count()
        updated = deleted = skipped = 0
        self.stdout.write(f"Kandidaten: {total:,} Wörter")

        ids_to_delete: list = []
        updates_todo:  list = []

        # Wortbestand pro Wortliste einladen (für Schnellsuche)
        existing: dict[int, set[str]] = {}
        offset = 0
        num_batches = -(-total // batch_size)

        while offset < total:
            batch = list(candidates[offset: offset + batch_size])
            offset += batch_size
            batch_num = offset // batch_size

            wl_ids = {row[2] for row in batch}
            for wl_id in wl_ids:
                if wl_id not in existing:
                    existing[wl_id] = set(
                        Word.objects
                        .filter(wordlist_id=wl_id)
                        .values_list("word", flat=True)
                    )

            for word_id, word, wordlist_id in batch:
                stem = normalize_german_word(word)

                if stem == word:
                    skipped += 1
                    continue

                if len(stem) < min_len:
                    ids_to_delete.append(word_id)
                    deleted += 1
                    if verbose:
                        self.stdout.write(f"  DEL  {word} (Stamm zu kurz: {stem!r})")
                    continue

                # Prüfe Kandidaten in Reihenfolge: bester Treffer gewinnt
                found_base: str | None = None
                for base in _candidate_bases(stem):
                    if base in existing[wordlist_id]:
                        found_base = base
                        break

                if found_base:
                    # Grundform bereits vorhanden → Duplikat löschen
                    ids_to_delete.append(word_id)
                    deleted += 1
                    if verbose:
                        self.stdout.write(f"  DEL  {word} → {found_base} (bereits in DB)")
                else:
                    # Grundform fehlt → auf besten Kandidaten aktualisieren
                    best = _candidate_bases(stem)[0]   # erster = konservativster
                    updates_todo.append((word_id, best))
                    existing[wordlist_id].add(best)
                    updated += 1
                    if verbose:
                        self.stdout.write(f"  UPD  {word} → {best}")

            self.stdout.write(
                f"  Batch {batch_num}/{num_batches}: "
                f"{updated} aktualisiert, {deleted} gelöscht, {skipped} unverändert"
            )

        if not dry:
            self._apply(ids_to_delete, updates_todo)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ {updated} normalisiert · {deleted} gelöscht · {skipped} unverändert"
        ))

    def _apply(self, ids_to_delete: list, updates: list) -> None:
        CHUNK = 5000
        for i in range(0, len(ids_to_delete), CHUNK):
            with transaction.atomic():
                Word.objects.filter(id__in=ids_to_delete[i:i + CHUNK]).delete()
        for word_id, new_word in updates:
            with transaction.atomic():
                Word.objects.filter(id=word_id).update(
                    word=new_word,
                    word_length=len(new_word),
                )
