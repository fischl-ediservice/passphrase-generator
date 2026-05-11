from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.wordlist_filter import FilterConfig, WordlistFilter, print_filter_stats
from generator.models import BannedWord, Wordlist, Word

DEFAULT_WORDLIST_FILE = settings.BASE_DIR / "data" / "wordlists" / "de_standard.txt"
DEFAULT_REJECT_FILE = settings.BASE_DIR / "data" / "wordlists" / "de_reject.txt"
DEFAULT_SENSITIVE_FILE = settings.BASE_DIR / "data" / "wordlists" / "de_sensitive_terms.txt"
DEFAULT_TECHNICAL_FILE = settings.BASE_DIR / "data" / "wordlists" / "de_nerd_terms.txt"


class Command(BaseCommand):
    help = "Importiert eine lokale deutsche Wortliste in die DB."

    def add_arguments(self, parser):
        parser.add_argument("--file",       default=str(DEFAULT_WORDLIST_FILE))
        parser.add_argument("--min-length", type=int, default=4)
        parser.add_argument("--max-length", type=int, default=30)
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument("--dry-run",    action="store_true")
        parser.add_argument("--replace",    action="store_true")
        parser.add_argument("--reject-file", default=str(DEFAULT_REJECT_FILE))
        parser.add_argument("--sensitive-file", default=str(DEFAULT_SENSITIVE_FILE))
        parser.add_argument("--technical-file", default=str(DEFAULT_TECHNICAL_FILE))

    def handle(self, *args, **options):
        source = Path(options["file"]).expanduser()
        lines  = self._load_source(source)
        banned_places = self._load_banned_places()
        blocked_words = self._load_reject_words(Path(options["reject_file"]).expanduser())
        (
            blocked_parts,
            blocked_case_parts,
            blocked_suffixes,
            adult_parts,
            adult_case_parts,
            adult_suffixes,
        ) = self._load_sensitive_terms(
            Path(options["sensitive_file"]).expanduser()
        )
        technical_parts, technical_case_parts = self._load_technical_terms(
            Path(options["technical_file"]).expanduser()
        )
        if banned_places:
            self.stdout.write(f"Ortsnamen-Banliste geladen: {len(banned_places):,}")
        if blocked_words:
            self.stdout.write(f"Lokale Sperrliste geladen: {len(blocked_words):,}")
        if blocked_parts or blocked_case_parts:
            self.stdout.write(
                "Hart gesperrte Bestandteile geladen: "
                f"{len(blocked_parts):,} case-insensitiv, {len(blocked_case_parts):,} case-sensitiv"
            )
        if blocked_suffixes:
            self.stdout.write(f"Hart gesperrte Endungen geladen: {len(blocked_suffixes):,}")
        if adult_parts or adult_case_parts:
            self.stdout.write(
                "Adult-Bestandteile geladen: "
                f"{len(adult_parts):,} case-insensitiv, {len(adult_case_parts):,} case-sensitiv"
            )
        if adult_suffixes:
            self.stdout.write(f"Adult-Endungen geladen: {len(adult_suffixes):,}")
        if technical_parts or technical_case_parts:
            self.stdout.write(
                "Nerd-/Fachbestandteile geladen: "
                f"{len(technical_parts):,} case-insensitiv, {len(technical_case_parts):,} case-sensitiv"
            )
        cfg    = FilterConfig(
            min_length=options["min_length"],
            max_length=options["max_length"],
            banned_place_words=banned_places,
            blocked_words=blocked_words,
            blocked_word_parts=blocked_parts,
            blocked_case_sensitive_parts=blocked_case_parts,
            blocked_word_suffixes=blocked_suffixes,
            adult_word_parts=adult_parts,
            adult_case_sensitive_parts=adult_case_parts,
            adult_word_suffixes=adult_suffixes,
            technical_word_parts=technical_parts,
            technical_case_sensitive_parts=technical_case_parts,
        )
        result = WordlistFilter(cfg).filter_lines(lines)
        print_filter_stats(result)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Nichts geschrieben."))
            return

        wordlist = self._get_or_create_wordlist(options["replace"], self._source_label(source))
        total    = self._bulk_import(wordlist, result["accepted"], options["batch_size"])
        self.stdout.write(
            self.style.SUCCESS(f"✓ {total} Wörter importiert in '{wordlist.name}'.")
        )
        self.stdout.write(
            self.style.WARNING("Web-Prozess danach neu starten, damit der Wortpool-Cache frisch ist.")
        )

    def _load_source(self, filepath: Path) -> list[str]:
        if not filepath.exists():
            raise CommandError(
                "Lokale Wortliste nicht gefunden: "
                f"{filepath}. Lege die Datei dort ab oder nutze --file."
            )
        if not filepath.is_file():
            raise CommandError(f"Pfad ist keine Datei: {filepath}")
        try:
            with filepath.open(encoding="utf-8") as f:
                return f.readlines()
        except OSError as e:
            raise CommandError(f"Datei nicht lesbar: {e}")

    def _source_label(self, filepath: Path) -> str:
        try:
            return str(filepath.resolve().relative_to(settings.BASE_DIR))
        except ValueError:
            return str(filepath)

    def _load_banned_places(self) -> frozenset[str]:
        return frozenset(
            BannedWord.objects
            .filter(reason__name="ortsname")
            .values_list("word", flat=True)
        )

    def _load_reject_words(self, filepath: Path) -> frozenset[str]:
        if not filepath.exists():
            return frozenset()
        if not filepath.is_file():
            raise CommandError(f"Pfad ist keine Datei: {filepath}")
        try:
            with filepath.open(encoding="utf-8") as f:
                return frozenset(
                    line.strip().lower()
                    for line in f
                    if line.strip() and not line.lstrip().startswith("#")
                )
        except OSError as e:
            raise CommandError(f"Sperrlisten-Datei nicht lesbar: {e}")

    def _load_sensitive_terms(
        self,
        filepath: Path,
    ) -> tuple[
        frozenset[str],
        frozenset[str],
        frozenset[str],
        frozenset[str],
        frozenset[str],
        frozenset[str],
    ]:
        if not filepath.exists():
            return frozenset(), frozenset(), frozenset(), frozenset(), frozenset(), frozenset()
        if not filepath.is_file():
            raise CommandError(f"Pfad ist keine Datei: {filepath}")
        insensitive: set[str] = set()
        case_sensitive: set[str] = set()
        suffixes: set[str] = set()
        adult: set[str] = set()
        adult_case_sensitive: set[str] = set()
        adult_suffixes: set[str] = set()
        try:
            with filepath.open(encoding="utf-8") as f:
                for line in f:
                    term = line.strip()
                    if not term or term.startswith("#"):
                        continue
                    if term.startswith("adult_suffix:"):
                        suffix = term.removeprefix("adult_suffix:").strip()
                        if suffix:
                            adult_suffixes.add(suffix.lower())
                        continue
                    if term.startswith("hard_suffix:"):
                        suffix = term.removeprefix("hard_suffix:").strip()
                        if suffix:
                            suffixes.add(suffix.lower())
                        continue
                    target = insensitive
                    case_target = case_sensitive
                    if term.startswith("adult:"):
                        target = adult
                        case_target = adult_case_sensitive
                        term = term.removeprefix("adult:").strip()
                    elif term.startswith("hard:"):
                        term = term.removeprefix("hard:").strip()
                    if term.startswith("case:"):
                        case_term = term.removeprefix("case:").strip()
                        if case_term:
                            case_target.add(case_term)
                    else:
                        target.add(term.lower())
        except OSError as e:
            raise CommandError(f"Sensitiv-Datei nicht lesbar: {e}")
        return (
            frozenset(insensitive),
            frozenset(case_sensitive),
            frozenset(suffixes),
            frozenset(adult),
            frozenset(adult_case_sensitive),
            frozenset(adult_suffixes),
        )

    def _load_technical_terms(self, filepath: Path) -> tuple[frozenset[str], frozenset[str]]:
        if not filepath.exists():
            return frozenset(), frozenset()
        if not filepath.is_file():
            raise CommandError(f"Pfad ist keine Datei: {filepath}")
        insensitive: set[str] = set()
        case_sensitive: set[str] = set()
        try:
            with filepath.open(encoding="utf-8") as f:
                for line in f:
                    term = line.strip()
                    if not term or term.startswith("#"):
                        continue
                    if term.startswith("case:"):
                        case_term = term.removeprefix("case:").strip()
                        if case_term:
                            case_sensitive.add(case_term)
                    else:
                        insensitive.add(term.lower())
        except OSError as e:
            raise CommandError(f"Nerd-/Fachdatei nicht lesbar: {e}")
        return frozenset(insensitive), frozenset(case_sensitive)

    def _get_or_create_wordlist(self, replace, source_label):
        from generator.models import Lookup
        name     = "Deutsch (Standard)"
        existing = Wordlist.objects.filter(name=name).first()
        if existing:
            if replace:
                existing.delete()
            else:
                if existing.source != source_label or not existing.description:
                    existing.source = source_label
                    existing.description = "Lokal importierte deutsche Wortliste"
                    existing.save(update_fields=["source", "description", "updated_at"])
                return existing
        language = Lookup.objects.get(type__code="language",      code="de")
        theme    = Lookup.objects.get(type__code="wordlist_theme", code="standard")
        return Wordlist.objects.create(
            name=name, language=language, theme=theme,
            source=source_label,
            description="Lokal importierte deutsche Wortliste",
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
                    is_technical          = e["is_technical"],
                    adult_only            = e["adult_only"],
                    reverse_suitable      = e["reverse_suitable"],
                )
                for e in batch
            ]
            with transaction.atomic():
                created = Word.objects.bulk_create(objects, ignore_conflicts=True)
            total += len(created)
            self.stdout.write(f"  Batch {idx}/{len(batches)}: {len(created)} Wörter")
        return total
