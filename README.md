# 🔑 Passphrase Generator

> Ein sprachlich intelligenter, kryptografisch sauberer Passphrasengenerator auf Basis deutscher Wörter.

Menschen sind keine Hashfunktionen mit Schuhen. Dieser Generator akzeptiert das.

---

## Warum?

Die meisten Passwortgeneratoren optimieren für Maschinen — unleserliche Zeichenketten, die niemand tippt oder sich merkt. Dieser Generator optimiert für **Menschen**: starke Passphrasen, die man wirklich behalten kann.

```
Naturstrom-Stahlwinkel-Sturmpionier-Waldbach
```

~74 Bit Entropie. Sprechbar. Merkbar. Kryptografisch sauber.

---

## Features

### Kryptografische Sicherheit
- Ausschließlich `secrets`-Modul (CSPRNG) — keine `random`, keine Timestamps
- **Stride-Sampling**: Fisher-Yates Shuffle → crypto-zufälliger Start `x` → crypto-zufällige Schrittlänge `y` → shrinking pool
- Gleichmäßige Abdeckung des Wortpools ohne Cluster

### Transformationen
| Feature | Beschreibung |
|---|---|
| **Silben-Shuffle** | Fisher-Yates über die Silben eines Wortes — Wörterbuchangriff stirbt |
| **Ziffer-Injektion** | 4 Modi: Buchstabenersatz, Silbengrenze, Wortende, Phrasenanfang/-ende |
| **Rückwärts-Modi** | Einzeln, jeden zweiten, zufällig oder alle |
| **Sonderzeichen** | Regelbasierte Substitution (a→@, s→$ …) mit Gewichtung |
| **Case-Garantie** | Immer ein zufälliger Buchstabe gegen den Modus geflippt |
| **Separator-Pool** | `§$%&/` → zufällig je Wortpaar, oder literal als vollständiger Trenner |

### Entropie-Anzeige
```
H = n × log₂(W)
```
- `n` = Anzahl Wörter
- `W` = Größe des Wortpools

Transformationen erhöhen die mathematische Entropie nicht — aber sie töten Wörterbuchangriffe auf die Ausgabe.

### Wortlisten
- Deutsche Wörter aus kuratierter Liste
- Strenge Filterung: keine Flexionsformen, keine Ortsnamen (GeoNames DE/AT/CH), keine Slurs
- Adult-Wörter: markiert, standardmäßig ausgeschlossen
- Fach-/Nerd-Begriffe: markiert, standardmäßig ausgeschlossen
- Silbenanalyse via `pyphen` beim Import

### Profile
- Einstellungen als benanntes Profil speichern
- Schnellzugriff über Profil-Karten in der UI

---

## Quickstart

### Voraussetzungen
- Docker & Docker Compose

### Start

```bash
git clone https://github.com/fischl-ediservice/passphrase-generator.git
cd passphrase-generator
docker compose up -d
```

### Wortliste importieren

```bash
docker compose exec web python manage.py import_wordlist
```

### Ortsnamen bereinigen (optional)

GeoNames-Dumps für DE, AT, CH herunterladen und unter `data/geonames/` ablegen, dann:

```bash
docker compose exec web python manage.py import_place_names
docker compose exec web python manage.py clean_place_names
```

### Öffnen

```
http://localhost:8000
```

---

## Entwicklung

### Stack
- **Python 3.14+** · **Django 6** · **PostgreSQL 17**
- `pyphen` für Silbenanalyse
- `secrets` für Kryptografie — sonst nichts Externes

### Tests

```bash
docker compose exec web pytest
```

### Linting

```bash
docker compose exec web ruff check .
docker compose exec web mypy .
```

### Projektstruktur

```
core/               # Framework-freier Kern (kompatibel mit CLI/PySide6)
│   entropy.py      # Stride-Sampling, Entropieberechnung
│   generator.py    # GeneratorConfig, generate_passphrase()
│   phonetics.py    # Silbenanalyse (SyllableAnalyzer)
│   transforms.py   # Alle Wort-Transformationen
│   wordlist_filter.py
│
generator/          # Django-App
│   models/         # Word, Wordlist, GeneratorProfile, UserWordFeedback …
│   views.py        # /generate, /profile/save, /profile/<id>/delete
│   templates/
│   management/commands/
│
data/
│   wordlists/      # de_standard.txt u.a.
│   geonames/       # GeoNames-Dumps (nicht im Repo, lokal ablegen)
│
tests/              # pytest
docs/               # Technische Spezifikation & Vision
```

---

## Entropie-Referenz

| Wörter | Pool ~5.000 | Pool ~8.000 | Einordnung |
|--------|-------------|-------------|------------|
| 4 | ~49 Bit | ~52 Bit | schwach |
| 6 | ~74 Bit | ~78 Bit | stark |
| 8 | ~98 Bit | ~104 Bit | sehr stark |
| 10 | ~123 Bit | ~130 Bit | paranoid |

Apple-Format (3×6, ~62 Zeichen): ~107 Bit — nicht merkbar.  
8 deutsche Wörter: ~104 Bit — sprechbar.

---

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL-Connection-String |
| `DJANGO_SECRET` | — | Django Secret Key (in Produktion ändern!) |
| `DEBUG` | `false` | Django Debug-Modus |
| `ADULT_WORD_UNLOCK_PASSWORD` | — | Passwort zum Freischalten des Adult-Wortpools |

---

## Lizenz

MIT — siehe `pyproject.toml`

---

## Philosophie

> Menschen merken sich Bilder, Geschichten und Sprachrhythmen —  
> keine SHA-256-Hashes.

Mehr dazu: [`docs/VISION_AND_DESIGN_PHILOSOPHY.md`](docs/VISION_AND_DESIGN_PHILOSOPHY.md)
