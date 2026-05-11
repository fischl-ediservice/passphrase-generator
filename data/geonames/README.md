# Lokale GeoNames-Dumps

Lege GeoNames-Dumps als lokale Kopie hier ab, zum Beispiel:

```text
data/geonames/DE.zip
data/geonames/AT.zip
data/geonames/CH.zip
data/geonames/LI.zip
```

Alternativ akzeptiert der Import auch entpackte `.txt`-Dateien mit gleichem Ländercode.
`python manage.py import_place_names` lädt keine Dumps aus dem Netzwerk nach.
