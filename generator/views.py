import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from core.generator import GeneratorConfig, generate_passphrase
from generator.models import Lookup, Word, GeneratorProfile


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
        config = GeneratorConfig(
            word_count         = max(2, min(10, int(data.get("word_count", 4)))),
            separator          = data.get("separator", "-")[:10],
            case_mode          = data.get("case_mode",    "lower"),
            umlaut_mode        = data.get("umlaut_mode",  "allow"),
            eszett_mode        = data.get("eszett_mode",  "allow"),
            reverse_mode       = data.get("reverse_mode", "off"),
            avoid_same_initial = bool(data.get("avoid_same_initial", False)),
        )
        min_len = max(2, int(data.get("min_length", 4)))
        max_len = max(min_len, int(data.get("max_length", 12)))

    words = list(
        Word.objects
        .filter(word_length__gte=min_len, word_length__lte=max_len)
        .order_by("?")
        .values_list("word", flat=True)[:8000]
    )

    if len(words) < config.word_count:
        return JsonResponse({"error": "Zu wenige Wörter im Pool für diese Einstellungen."}, status=400)

    result = generate_passphrase(words, config)
    return JsonResponse({
        "passphrase":    result.passphrase,
        "words":         result.words,
        "entropy_bits":  result.entropy_bits,
        "entropy_label": result.entropy_label,
        "pool_size":     result.pool_size,
    })


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

    word_count = max(2, min(10, int(data.get("word_count", 4))))
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
