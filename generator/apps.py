import logging
import os
import sys

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

_SKIP_WARMUP_COMMANDS = {
    "check",
    "clean_place_names",
    "collectstatic",
    "discover",
    "import_place_names",
    "import_wordlist",
    "makemigrations",
    "migrate",
    "normalize_words",
    "shell",
    "test",
}


class GeneratorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "generator"

    def ready(self):
        if _should_skip_word_pool_warmup():
            return
        try:
            from generator.views import warm_word_pool_cache

            total = warm_word_pool_cache()
            logger.info("Word pool cache warmed with %s entries.", total)
        except (OperationalError, ProgrammingError):
            logger.info("Word pool cache warmup skipped; database is not ready yet.")


def _should_skip_word_pool_warmup() -> bool:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if sys.argv and sys.argv[0] == "-c":
        return True
    if command in _SKIP_WARMUP_COMMANDS:
        return True
    return command == "runserver" and os.environ.get("RUN_MAIN") != "true"
