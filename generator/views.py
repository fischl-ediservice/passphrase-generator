import json
import secrets
from threading import RLock

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from core.entropy import stride_indices
from core.generator import (
    GeneratorConfig,
    generate_passphrase_from_selection,
)
from generator.models import Lookup, Word, GeneratorProfile

STANDARD_WORD_PATTERN = r"^[A-ZÄÖÜ]"
_WORD_POOL_SOURCE: tuple[dict, ...] | None = None
_WORD_POOL_CACHE: dict[tuple, tuple] = {}
_WORD_POOL_CACHE_LOCK = RLock()


def index(request):
    context = {
        "case_modes":    list(Lookup.objects.filter(type__code="case_mode",    is_active=True).values("code", "label")),
        "umlaut_modes":  list(Lookup.objects.filter(type__code="umlaut_mode",  is_active=True).values("code", "label")),
        "eszett_modes":  list(Lookup.objects.filter(type__code="eszett_mode",  is_active=True).values("code", "label")),
        "reverse_modes": list(Lookup.objects.filter(type__code="reverse_mode", is_active=True).values("code", "label")),
        "profiles":      list(GeneratorProfile.objects.order_by("name").values(
                             "id", "name", "word_count", "separator",
                             "min_length", "max_length", "is_default")),
    }
    return render(request, "generator/index.html", context)


@csrf_exempt
@require_POST
def generate(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Ungültige Anfrage."}, status=400)

    profile_id = data.get("profile_id")
    if profile_id:
        try:
            profile = GeneratorProfile.objects.get(id=profile_id)
            config  = profile.to_config()
            min_len = profile.min_length
            max_len = profile.max_length
        except GeneratorProfile.DoesNotExist:
            return JsonResponse({"error": "Profil nicht gefunden."}, status=404)
    else:
        sep_raw      = data.get("separator", "-")[:50]
        sep_complete = bool(data.get("separator_complete", False))
        if sep_complete or len(sep_raw) <= 1:
            sep_pool  = []
            separator = sep_raw
        else:
            sep_pool  = list(sep_raw)   # jedes Zeichen einzeln in den Pool
            separator = sep_pool[0]
        config = GeneratorConfig(
            word_count              = max(2, int(data.get("word_count", 4))),
            separator               = separator,
            separator_pool          = sep_pool,
            case_mode               = data.get("case_mode",    "lower"),
            umlaut_mode             = data.get("umlaut_mode",  "allow"),
            eszett_mode             = data.get("eszett_mode",  "allow"),
            reverse_mode            = data.get("reverse_mode", "off"),
            avoid_same_initial      = bool(data.get("avoid_same_initial", False)),
            syllable_shuffle_enabled= bool(data.get("syllable_shuffle", False)),
            digit_mode              = data.get("digit_mode", "off"),
            special_mode            = data.get("special_mode", "off"),
        )
        try:
            config.include_adult_words = _adult_words_unlocked(data)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=403)
        min_len = max(4, int(data.get("min_length", 6)))   # hart: niemals unter 4
        max_len = max(min_len, int(data.get("max_length", 12)))

    needs_syllables = (
        config.syllable_shuffle_enabled
        or config.digit_mode == "inject_syllable"
        or config.special_mode == "inject_syllable"
    )
    pool = _get_word_pool(min_len, max_len, config, needs_syllables)
    pool_size = len(pool)

    if pool_size < config.word_count:
        return JsonResponse({"error": "Zu wenige Wörter im Pool für diese Einstellungen."}, status=400)

    entries = _pick_pool_entries(pool, config, needs_syllables)
    words = [_entry_word(entry, needs_syllables) for entry in entries]
    syllables_map = (
        {entry["word"]: entry["syllables"] for entry in entries}
        if needs_syllables else None
    )

    result = generate_passphrase_from_selection(words, pool_size, config, syllables_map)
    return JsonResponse({
        "passphrase":    result.passphrase,
        "words":         result.words,
        "entropy_bits":  result.entropy_bits,
        "entropy_label": result.entropy_label,
        "pool_size":     result.pool_size,
    })


def _word_pool_cache_key(
    min_len: int,
    max_len: int,
    config: GeneratorConfig,
    include_syllables: bool,
) -> tuple:
    return (
        min_len,
        max_len,
        bool(config.syllable_shuffle_enabled),
        bool(include_syllables),
        bool(config.include_adult_words),
        bool(config.include_technical_words),
    )


def warm_word_pool_cache(force: bool = False) -> int:
    global _WORD_POOL_SOURCE
    with _WORD_POOL_CACHE_LOCK:
        if _WORD_POOL_SOURCE is not None and not force:
            return len(_WORD_POOL_SOURCE)

        _WORD_POOL_SOURCE = _query_word_pool_source()
        _WORD_POOL_CACHE.clear()
        return len(_WORD_POOL_SOURCE)


def _query_word_pool_source() -> tuple[dict, ...]:
    return tuple(
        Word.objects
        .filter(word__regex=STANDARD_WORD_PATTERN)
        .order_by("word")
        .values(
            "word",
            "word_length",
            "syllables",
            "syllable_shuffle_mode",
            "adult_only",
            "is_technical",
        )
    )


def _get_word_pool(
    min_len: int,
    max_len: int,
    config: GeneratorConfig,
    include_syllables: bool,
) -> tuple:
    cache_key = _word_pool_cache_key(min_len, max_len, config, include_syllables)
    with _WORD_POOL_CACHE_LOCK:
        cached = _WORD_POOL_CACHE.get(cache_key)
        if cached is not None:
            return cached

        source = _WORD_POOL_SOURCE
        if source is None:
            warm_word_pool_cache()
            source = _WORD_POOL_SOURCE or ()

        rows = (
            row for row in source
            if min_len <= row["word_length"] <= max_len
            and (config.include_adult_words or not row["adult_only"])
            and (config.include_technical_words or not row["is_technical"])
            and (
                not config.syllable_shuffle_enabled
                or row["syllable_shuffle_mode"] != "unsuitable"
            )
        )
        pool = tuple(
            {"word": row["word"], "syllables": row["syllables"]}
            if include_syllables else row["word"]
            for row in rows
        )

        _WORD_POOL_CACHE[cache_key] = pool
        return pool


def clear_word_pool_cache(clear_source: bool = False) -> None:
    global _WORD_POOL_SOURCE
    with _WORD_POOL_CACHE_LOCK:
        _WORD_POOL_CACHE.clear()
        if clear_source:
            _WORD_POOL_SOURCE = None


def _adult_words_unlocked(data: dict) -> bool:
    password = str(data.get("adult_unlock_password", ""))
    if not password:
        return False
    expected = getattr(settings, "ADULT_WORD_UNLOCK_PASSWORD", "")
    if expected and secrets.compare_digest(password, expected):
        return True
    raise ValueError("Freischalt-Passwort für Adult-Wörter ist falsch.")


def _pick_pool_entries(pool: tuple, config: GeneratorConfig, include_syllables: bool) -> list:
    attempts = 20 if config.avoid_same_initial else 1
    entries = []

    for _ in range(attempts):
        offsets = stride_indices(len(pool), config.word_count)
        entries = [pool[offset] for offset in offsets]
        if not config.avoid_same_initial:
            return entries
        initials = {
            _entry_word(entry, include_syllables)[0].lower()
            for entry in entries
        }
        if len(initials) == len(entries):
            return entries

    return entries


def _entry_word(entry, include_syllables: bool) -> str:
    return entry["word"] if include_syllables else entry


@csrf_exempt
@require_POST
def save_profile(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Ungültige Anfrage."}, status=400)

    name = data.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Name darf nicht leer sein."}, status=400)
    if len(name) > 100:
        return JsonResponse({"error": "Name zu lang (max. 100 Zeichen)."}, status=400)

    # Lookup-Objekte auflösen
    def get_lookup(type_code, code, default=None):
        try:
            return Lookup.objects.get(type__code=type_code, code=code)
        except Lookup.DoesNotExist:
            return default

    word_count = max(2, min(20, int(data.get("word_count", 4))))
    min_len    = max(2, int(data.get("min_length", 4)))
    max_len    = max(min_len, int(data.get("max_length", 12)))

    profile, created = GeneratorProfile.objects.update_or_create(
        name=name,
        defaults=dict(
            word_count         = word_count,
            min_length         = min_len,
            max_length         = max_len,
            separator          = data.get("separator", "-")[:10],
            case_mode          = get_lookup("case_mode",    data.get("case_mode",    "lower")),
            umlaut_mode        = get_lookup("umlaut_mode",  data.get("umlaut_mode",  "allow")),
            eszett_mode        = get_lookup("eszett_mode",  data.get("eszett_mode",  "allow")),
            reverse_mode       = get_lookup("reverse_mode", data.get("reverse_mode", "off")),
            avoid_same_initial = bool(data.get("avoid_same_initial", False)),
            syllable_shuffle_enabled = bool(data.get("syllable_shuffle", False)),
            digit_mode         = data.get("digit_mode", "off")[:20],
            special_mode       = data.get("special_mode", "off")[:20],
            special_chars_enabled = data.get("special_mode", "off") != "off",
        ),
    )

    return JsonResponse({
        "id":      str(profile.id),
        "name":    profile.name,
        "created": created,
        "word_count": profile.word_count,
        "separator":  profile.separator,
        "min_length": profile.min_length,
        "max_length": profile.max_length,
    })


@csrf_exempt
@require_POST
def delete_profile(request, profile_id):
    try:
        profile = GeneratorProfile.objects.get(id=profile_id)
        name    = profile.name
        profile.delete()
        return JsonResponse({"deleted": name})
    except GeneratorProfile.DoesNotExist:
        return JsonResponse({"error": "Profil nicht gefunden."}, status=404)
