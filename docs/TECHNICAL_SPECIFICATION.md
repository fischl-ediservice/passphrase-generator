# TECHNICAL_OVERVIEW.md

# Passphrase Generator

## Technical Overview

---

## Projektziel

Entwicklung eines sprachlich intelligenten Open-Source-Passphrasengenerators auf Basis von Python und Django.

### Fokus

- kryptografisch sichere Passphrasen
- hohe Merkfähigkeit
- sprachliche Struktur
- Offline-First
- Transparenz

---

## Technologien

### Sprache

- Python

### GUI

- Django

### Kryptografische Zufallsquelle

- Python secrets

### Nicht verwendet

- Zeitstempel
- pseudozufällige Eigenkonstruktionen
- nicht kryptografische RNGs

---

## Sicherheitsprinzipien

### Offline-First

- keine Cloud
- keine Telemetrie
- keine Passwortspeicherung
- keine externen APIs

### Open Source

- vollständige Transparenz
- auditierbar
- nachvollziehbare RNG-Logik
- nachvollziehbare Transformationen

---

## V1 Scope

### Generator-Kern

- kryptografisch sichere Wortauswahl
- konfigurierbare Wortanzahl
- Mindestwortlänge
- Maximalwortlänge
- optionale Trenner
- optionale Groß-/Kleinschreibung

---

### Wortlisten

- deutsche Wörter
- Filterung problematischer Einträge
- Markierung eingedeutschter Begriffe

---

### Wort-Metadaten-System

Jedes Wort erhält:

- Schwierigkeit
- Kategorie
- Herkunft
- Silbenanzahl
- Phonetik-Score
- Merkfähigkeit
- Reverse-Eignung
- Shuffle-Eignung
- Kompositum ja/nein
- Fachwort ja/nein

---

## Entropieanzeige

Die Entropie basiert primär auf der Größe der gültigen Wortmenge und der Anzahl der verwendeten Wörter.

### Formel

text H = n × log₂(W) 

Mit:

- H = geschätzte Entropie in Bit
- n = Anzahl gewählter Wörter
- W = Größe der gültigen Wortmenge

### Beispiel

- 8 Wörter
- Wortpool: 8.000 Wörter

Ergebnis:

- ca. 103 Bit Entropie

### Die primäre Sicherheit entsteht durch

- Wortanzahl
- Wortvielfalt
- kryptografisch sichere Auswahl

### Nicht primär durch

- Sonderzeicheninflation
- erzwungene Zeichensätze
- komplizierte Passwortregeln

### Zusätzliche Transformationen

Transformationen wie:

- Reverse-Modi
- Shuffle-Modi
- Sonderzeichenersetzungen

können die praktische Komplexität zusätzlich erhöhen, sind jedoch nicht der Hauptfaktor der Sicherheit.

### Projektphilosophie

Das Projekt priorisiert:

- reale Merkfähigkeit
- sprachliche Nutzbarkeit
- kryptografisch saubere Zufallsauswahl
- hohe praktische Sicherheit

statt künstlicher Komplexität.