import urllib.request
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from generator.models import Wordlist, Word
from core.wordlist_filter import FilterConfig, WordlistFilter, print_filter_stats

RAW_URL = (
    "https://gist.github.com/MarvinJWendt/"
    "2f4f4154b8ae218600eb091a5706b5f4/raw/"
    "36b70dd6be330aa61cd4d4cdfda6234dcb0b8784/wordlist-german.txt"
)


class Command(BaseCommand):
    help = "Importiert eine deutsche Wortliste in die DB."

    def add_arguments(self, parser):
        parser.add_argument("--url",        default=RAW_URL)
        parser.add_argument("--file",       default=None)
        parser.add_argument("--min-length", type=int, default=4)
        parser.add_argument("--max-length", type=int, default=30)
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument("--dry-run",    action="store_true")
        parser.add_argument("--replace",    action="store_true")

    def handle(self, *args, **options):
        lines  = self._load_source(options["file"], options["url"])
        cfg    = FilterConfig(min_length=options["min_length"], max_length=options["max_length"])
        result = WordlistFilter(cfg).filter_lines(lines)
        print_filter_stats(result)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Nichts geschrieben."))
            return

        wordlist = self._get_or_create_wordlist(options["replace"])
        total    = self._bulk_import(wordlist, result["accepted"], options["batch_size"])
        self.stdout.write(self.style.SUCCESS(f"✓ {total} Wörter importiert in '{wordlist.name}'."))

    def _load_source(self, filepath, url):
        if filepath:
            try:
                with open(filepath, encoding="utf-8") as f:
                    return f.readlines()
            except OSError as e:
                raise CommandError(f"Datei nicht lesbar: {e}")
        try:
            with urllib.request.urlopen(url) as r:
                return r.read().decode("utf-8").splitlines()
        except Exception as e:
            raise CommandError(f"Download fehlgeschlagen: {e}")

    def _get_or_create_wordlist(self, replace):
        from generator.models import Lookup
        name     = "Deutsch (Standard)"
        existing = Wordlist.objects.filter(name=name).first()
        if existing:
            if replace:
                existing.delete()
            else:
                return existing
        language = Lookup.objects.get(type__code="language",      code="de")
        theme    = Lookup.objects.get(type__code="wordlist_theme", code="standard")
        return Wordlist.objects.create(
            name=name, language=language, theme=theme,
            source=RAW_URL,
            description="Automatisch importiert aus MarvinJWendt/wordlist-german",
        )

    def _bulk_import(self, wordlist, accepted, batch_size):
        total   = 0
        batches = [accepted[i:i+batch_size] for i in range(0, len(accepted), batch_size)]
        for idx, batch in enumerate(batches, 1):
            objects = [
                Word(
                    wordlist              = wordlist,
                    word                  = e["word"],
                    word_length           = e["word_length"],
                    syllables             = e["syllables"],
                    syllable_count        = e["syllable_count"],
                    syllable_shuffle_mode = e["syllable_shuffle_mode"],
                    syllables_anchored    = e["syllables_anchored"],
                    is_compound           = e["is_compound"],
                    reverse_suitable      = e["reverse_suitable"],
                )
                for e in batch
            ]
            with transaction.atomic():
                created = Word.objects.bulk_create(objects, ignore_conflicts=True)
            total += len(created)
            self.stdout.write(f"  Batch {idx}/{len(batches)}: {len(created)} Wörter")
        return total
