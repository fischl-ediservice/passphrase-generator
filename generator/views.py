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
        "profiles":      list(GeneratorProfile.objects.values("id", "name", "word_count", "separator", "is_default")),
    }
    return render(request, "generator/index.html", context)


@csrf_exempt
@require_POST
def generate(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Ungültige Anfrage."}, status=400)

    config = GeneratorConfig(
        word_count   = max(2, min(10, int(data.get("word_count", 4)))),
        separator    = data.get("separator", "-")[:10],
        case_mode    = data.get("case_mode",    "lower"),
        umlaut_mode  = data.get("umlaut_mode",  "allow"),
        eszett_mode  = data.get("eszett_mode",  "allow"),
        reverse_mode = data.get("reverse_mode", "off"),
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
