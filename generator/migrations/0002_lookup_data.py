from django.db import migrations

LOOKUP_TYPES = [
    {"code": "language",       "label": "Sprache",          "description": "Sprache einer Wortliste"},
    {"code": "difficulty",     "label": "Schwierigkeit",    "description": "Schwierigkeitsgrad eines Wortes"},
    {"code": "origin",         "label": "Wortherkunft",     "description": "Etymologische Herkunft"},
    {"code": "part_of_speech", "label": "Wortart",          "description": "Grammatikalische Wortart"},
    {"code": "case_mode",      "label": "Schreibweise",     "description": "Groß-/Kleinschreibung im Generator"},
    {"code": "umlaut_mode",    "label": "Umlaut-Modus",     "description": "Umgang mit Umlauten"},
    {"code": "eszett_mode",    "label": "ß-Modus",          "description": "Umgang mit ß"},
    {"code": "reverse_mode",   "label": "Rückwärtsmodus",   "description": "Wörter rückwärts schreiben"},
    {"code": "wordlist_theme", "label": "Wortlisten-Thema", "description": "Thematische Kategorie einer Wortliste"},
]

LOOKUPS = {
    "language": [
        {"code": "de", "label": "Deutsch",     "vowels": "aeiouäöüy",           "pyphen_lang": "de_DE", "sort_order": 1},
        {"code": "en", "label": "Englisch",    "vowels": "aeiouy",              "pyphen_lang": "en_US", "sort_order": 2},
        {"code": "it", "label": "Italienisch", "vowels": "aeiou",               "pyphen_lang": "it_IT", "sort_order": 3},
        {"code": "es", "label": "Spanisch",    "vowels": "aeiouü",              "pyphen_lang": "es_ES", "sort_order": 4},
        {"code": "fr", "label": "Französisch", "vowels": "aeiouyéàèùâêîôûëïü", "pyphen_lang": "fr_FR", "sort_order": 5},
    ],
    "difficulty": [
        {"code": "any",     "label": "Beliebig",               "sort_order": 0},
        {"code": "easy",    "label": "Einfach",                "sort_order": 1},
        {"code": "normal",  "label": "Normal",                 "sort_order": 2},
        {"code": "hard",    "label": "Anspruchsvoll",          "sort_order": 3},
        {"code": "extreme", "label": "Sprachlicher Endgegner", "sort_order": 4},
    ],
    "origin": [
        {"code": "german",  "label": "Deutsch",     "sort_order": 1},
        {"code": "latin",   "label": "Lateinisch",  "sort_order": 2},
        {"code": "french",  "label": "Französisch", "sort_order": 3},
        {"code": "english", "label": "Englisch",    "sort_order": 4},
        {"code": "greek",   "label": "Griechisch",  "sort_order": 5},
        {"code": "other",   "label": "Sonstige",    "sort_order": 9},
    ],
    "part_of_speech": [
        {"code": "noun",      "label": "Nomen",    "sort_order": 1},
        {"code": "verb",      "label": "Verb",     "sort_order": 2},
        {"code": "adjective", "label": "Adjektiv", "sort_order": 3},
        {"code": "adverb",    "label": "Adverb",   "sort_order": 4},
        {"code": "other",     "label": "Sonstige", "sort_order": 9},
    ],
    "case_mode": [
        {"code": "lower",    "label": "Kleinschreibung",       "sort_order": 1},
        {"code": "upper",    "label": "Großschreibung",        "sort_order": 2},
        {"code": "title",    "label": "Erster Buchstabe groß", "sort_order": 3},
        {"code": "original", "label": "Original beibehalten",  "sort_order": 4},
    ],
    "umlaut_mode": [
        {"code": "allow",     "label": "Umlaute erlauben",                "sort_order": 1},
        {"code": "normalize", "label": "Umlaute normalisieren (ae/oe/ue)", "sort_order": 2},
        {"code": "exclude",   "label": "Umlaute ausschließen",            "sort_order": 3},
    ],
    "eszett_mode": [
        {"code": "allow",   "label": "ß erlauben", "sort_order": 1},
        {"code": "replace", "label": "ß → ss",     "sort_order": 2},
    ],
    "reverse_mode": [
        {"code": "off",         "label": "Aus",               "sort_order": 1},
        {"code": "some",        "label": "Einzelne Wörter",   "sort_order": 2},
        {"code": "every_other", "label": "Jedes zweite Wort", "sort_order": 3},
        {"code": "all",         "label": "Alle Wörter",       "sort_order": 4},
    ],
    "wordlist_theme": [
        {"code": "standard", "label": "Standard",        "sort_order": 1},
        {"code": "film",     "label": "Film & Serien",   "sort_order": 2},
        {"code": "pop",      "label": "Pop & Musik",     "sort_order": 3},
        {"code": "science",  "label": "Wissenschaft",    "sort_order": 4},
        {"code": "food",     "label": "Essen & Trinken", "sort_order": 5},
    ],
}


def load_lookups(apps, schema_editor):
    LookupType = apps.get_model("generator", "LookupType")
    Lookup     = apps.get_model("generator", "Lookup")
    for lt in LOOKUP_TYPES:
        obj = LookupType.objects.create(**lt)
        for entry in LOOKUPS.get(lt["code"], []):
            Lookup.objects.create(
                type         = obj,
                code         = entry["code"],
                label        = entry["label"],
                vowels       = entry.get("vowels", ""),
                extra_vowels = entry.get("extra_vowels", ""),
                pyphen_lang  = entry.get("pyphen_lang", ""),
                sort_order   = entry.get("sort_order", 0),
                is_active    = True,
            )


def unload_lookups(apps, schema_editor):
    apps.get_model("generator", "LookupType").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("generator", "0001_initial")]
    operations   = [migrations.RunPython(load_lookups, reverse_code=unload_lookups)]
