# Lokale Wortlisten

Die deutsche Standard-Wortliste liegt als lokale Kopie hier:

```text
data/wordlists/de_standard.txt
```

`python manage.py import_wordlist` liest standardmäßig nur diese lokale Datei.
Der Import-Command lädt keine Wortliste aus GitHub, Gists oder anderen Remote-Quellen nach.

Der Import filtert die Liste streng: Kleinformen, erkannte Flexions-/Pluralformen
mit vorhandener Grundform sowie Ortsnamen und Ortsnamen-Ableitungen werden nicht
in den Generator-Wortbestand übernommen. Akzente außerhalb deutscher Umlaute
werden standardmäßig normalisiert, z.B. `Attaché` zu `Attache`; `ä`, `ö`, `ü`
und `ß` bleiben erhalten.

Zusätzlich wird `data/wordlists/de_reject.txt` als lokale Sperrliste gelesen.
Sie ist für formal gültige, aber praktisch unbrauchbare Wörter gedacht.

`data/wordlists/de_sensitive_terms.txt` enthält problematische Bestandteile wie
beleidigende, vulgäre oder extremistische Terme. Einträge sind standardmäßig
case-insensitiv. `hard:` wird beim Import vollständig verworfen, `adult:`
bleibt in der DB und wird im Generator standardmäßig ausgeblendet. `case:`
markiert innerhalb der Kategorie bewusst case-sensitive Bestandteile.
`hard_suffix:` verwirft nur Wörter mit dieser Endung, `adult_suffix:` markiert
nur Wörter mit dieser Endung.

`data/wordlists/de_nerd_terms.txt` enthält Fach- und Spezialbestandteile, die
zwar importiert, aber nicht im Standard-Pool angeboten werden.
