# TECHNICAL_SPECIFICATION.md

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
- Datenimporte aus lokalen Kopien unter `data/`, nicht aus Remote-Quellen

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

### Wortauswahl

- alle gültigen Wörter bilden den logischen Auswahlpool
- Startposition `x` wird mit `secrets.randbelow` gewählt
- Schrittlänge `y` wird mit `secrets.randbelow` gewählt
- nach jeder Entnahme schrumpft der Pool
- die nächste Position wird gegen die neue Poolgröße gerechnet
- bei Überlauf wird am Anfang des geschrumpften Pools weitergelesen
- der Web-Prozess lädt den Wortbestand beim Start einmal aus der DB
- gefilterte Wortpools werden danach aus diesem Speicherbestand abgeleitet
- nach einem Wortlistenimport ist ein Neustart des Web-Prozesses empfohlen

---

### Wortlisten

- deutsche Wörter
- strenge Importfilterung problematischer Einträge, Flexionsformen und Ortsnamen
- Adult-Wörter bleiben markiert in der DB, sind aber standardmäßig vom Pool ausgeschlossen
- harte Slurs und direkte Beleidigungen werden beim Import vollständig verworfen
- nicht-deutsche Akzente werden beim Import normalisiert, deutsche Umlaute bleiben erhalten
- Fach-/Nerd-Wörter bleiben markiert in der DB, sind aber standardmäßig vom Pool ausgeschlossen
- Markierung eingedeutschter Begriffe
- Import aus lokaler Datei `data/wordlists/de_standard.txt`

### Ortsnamen-Banliste

- Import aus lokalen GeoNames-Dumps unter `data/geonames/`
- unterstützt `.zip`-Dumps und entpackte `.txt`-Dateien
- kein Download während des Management-Commands

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
- Zifferninjektion

können die praktische Komplexität zusätzlich erhöhen, sind jedoch nicht der Hauptfaktor der Sicherheit.

### Silbenbasierte Zifferninjektion

- alle Silben der ausgewählten Wörter werden gezählt
- die Ziel-Silbe wird mit `secrets.randbelow(Gesamtsilbenzahl)` gewählt
- die Ziffer wird an der Silbengrenze des global gewählten Silben-Slots eingefügt

### Sonderzeichen-Injektion

- nutzt die gleiche Modus-Logik wie Zifferninjektion
- unterstützt Buchstabenersetzung, Silbengrenze, Wortende und Phrasenanfang/-ende
- die konkrete Ersetzung bzw. das konkrete Sonderzeichen wird kryptografisch zufällig gewählt
- Standardtabelle enthält u.a. `a→@` und `s→$`

### Projektphilosophie

Das Projekt priorisiert:

- reale Merkfähigkeit
- sprachliche Nutzbarkeit
- kryptografisch saubere Zufallsauswahl
- hohe praktische Sicherheit

statt künstlicher Komplexität.
