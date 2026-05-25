# st3-Import: Handbuch

**Version:** 1.0.0 
**Autor:** Fabian Schöpflin  
**Datum:** 25. Mai 2026

## Übersicht

`st3_converter.py` überführt Zusi-3-Streckendateien (`.st3`) in ein topologisches
Knoten-Kanten-Modell. Pro verarbeiteter Datei entstehen zwei Layer:

| Layer-Name | Geometrietyp | Inhalt |
|---|---|---|
| `Gleiskante` | LineString | Gleisabschnitte zwischen Knoten |
| `Gleisknoten` | Point | Weichen, Modulgrenzen, Gleisenden |
| `Hüllkurve` ¹ | Polygon | Umgrenzungspolygon des Streckenmoduls (Geländeformer) |

¹ Optional; nur wenn **Hüllkurve importieren** aktiv ist.

> **Knotenname bei Weichen:** Das Feld `knotenname` wird aus dem Signalnamen des
> Weichensignals (SignalTyp 2) normalisiert – Buchstaben-Präfixe wie `W`, `EW`, `DKW`
> werden entfernt, eine optionale DKW-Kennung (`A`, `B`, `A/B` …) beibehalten.
> Bei ESTW-Dateien wird eine vorangestellte numerische Bereichskennziffer
> (z. B. `44` in `44W1`) ebenfalls ignoriert, sodass `44W1` → `1` ergibt.
> Das Normalisieren lässt sich per `--no-normalize-switches` (CLI) oder per
> `normalize_switch_names=False` (Python-API) deaktivieren, um Signalnamen
> unverändert zu übernehmen.
> Details siehe [st3-Import (Technische Dokumentation).md](st3-Import%20%28Technische%20Dokumentation%29.md#namen-von-weichenknoten-normalisieren).

> **Betriebsstelle bei Weichen:** Trägt ein Weichensignal (SignalTyp 2) das Attribut
> `NameBetriebsstelle` (z. B. `Bickenbach`), wird dieser Wert im Knoten-Layer als `bst_name`
> gespeichert. Im Kanten-Layer erhalten die anliegenden Kanten die Felder `bst_von` und
> `bst_bis` aus dem jeweiligen Endknoten – analog zu `knotenname_von`/`knotenname_bis`.
> Grenzt eine Kante an einen Nicht-Weichen-Knoten, bleibt das Feld leer.

`st3Converter` ist auf zwei Wegen nutzbar:

- **CLI** (`core/cli.py`): Direkte Konvertierung zu GeoPackage (`.gpkg`)
- **Python-Bibliothek**: Direkte Einbindung in eigene Python-Skripte

> **Technische Hintergründe** zu Algorithmus, Datenformat und Zielmodell
> sind in [st3-Import (Technische Dokumentation).md](st3-Import%20%28Technische%20Dokumentation%29.md) dokumentiert.

---

## Voraussetzungen

| Komponente | Beschreibung |
|---|---|
| `st3_converter.py` | Konverter-Kernmodul (Klasse `st3Converter`) |
| `core/core.py` | Logging-Setup und `Config`-Klasse; lädt `config/st3_converter_config.json` |
| `config/st3_converter_config.json` | Persistente Standardeinstellungen (wird beim ersten Start automatisch angelegt, falls nicht vorhanden) |
| `lxml` | Python-Bibliothek für XML-Parsing (muss in der Python-Umgebung verfügbar sein) |
| `pyproj` | Koordinatentransformation; erwartet die PROJ-Datendateien |
| `geopandas`, `shapely` | Nur CLI: GeoPackage-Ausgabe |
| PROJ-Daten (`de_adv_BETA2007.tif`) | Optional; wird aus dem PROJ-Datenpfad geladen, sofern vorhanden, für genaue DHDN↔WGS84-Transformation |

---

## CLI

Das Einstiegsskript ist `core/cli.py`.

### Konfigurationsdatei

Alle Einstellungen werden dauerhaft in `config/st3_converter_config.json` gespeichert:

```json
{
    "auto_detect_crs": true,
    "fallback_epsg": 32632,
    "target_epsg": 31467,
    "normalize_switch_names": true,
    "import_envelope": true,
    "create_log_file": true,
    "open_log_file": false
}
```

Im interaktiven Modus können die Einstellungen über **Option 6 → Einstellungen speichern**
in diese Datei geschrieben werden.

### Interaktiver Modus

```
python core/cli.py
```

Führt einen menügesteuerten Eingabedialog (Eingabedatei, Ziel-KBS, Optionen). Die
Dateisuche läuft dreistufig: zunächst im Arbeitsverzeichnis, dann nach manuellem
Ordnerpfad, schließlich nach direkter Pfadangabe.

Im Einstellungsmenü (Hauptmenü-Option **2**) stehen folgende Optionen zur Verfügung:

| Option | Beschreibung |
|---|---|
| 1 | Quell-KBS automatisch erkennen (ein/aus) |
| 2 | Rückfall-KBS festlegen |
| 3 | Ziel-KBS festlegen |
| 4 | Namen von Weichenknoten normalisieren (ein/aus) |
| 5 | Protokoll erstellen (ein/aus) |
| 6 | Protokoll nach Abschluss öffnen (ein/aus) |
| 7 | Hüllkurve importieren (ein/aus) |
| 8 | Einstellungen in JSON-Datei speichern |
| 0 | Zurück |

### CLI-Modus

```
python core/cli.py -i <Eingabe.st3> -o <Ausgabe.gpkg> [Optionen]
```

| Argument | Beschreibung |
|---|---|
| `-i / --input DATEI` | Pfad zur `.st3`-Eingabedatei (Pflicht im CLI-Modus) |
| `-o / --output DATEI` | Pfad zur Ausgabe-GeoPackage-Datei (Pflicht im CLI-Modus) |
| `-e / --epsg CODE` | Ziel-KBS als EPSG-Code (Standard: 31467) |
| `--no-auto-detect` | Automatische CRS-Erkennung deaktivieren |
| `--fallback-epsg CODE` | Rückfall-KBS wenn Auto-Erkennung fehlschlägt (Standard: aus JSON-Config) |
| `--no-normalize-switches` | Weichenknoten-Normalisieren deaktivieren (Signalnamen unverändert übernehmen) |
| `--import-envelope` | Hüllkurve importieren (unabhängig von gespeicherter Config erzwingen) |
| `--no-import-envelope` | Hüllkurven-Import deaktivieren |
| `--open-log` | Protokoll nach Abschluss automatisch öffnen |
| `-v / --version` | Versionsnummer ausgeben |

Die Ausgabe ist ein GeoPackage mit den Layern `Gleiskante` (LineString) und
`Gleisknoten` (Point) — sowie optional `Hüllkurve` (Polygon) — im gewählten Ziel-KBS.

---

## Programmatische Nutzung

`st3Converter` kann direkt aus Python genutzt werden. Die von `convert()`
zurückgegebenen Feature-Dicts lassen sich in eigenen Skripten weiterverarbeiten.

```python
from st3_converter import st3Converter

converter = st3Converter(
    input_path=r"C:\...\Freudenstein_2025.st3",
    target_epsg=31467,
    auto_detect_crs=True,
)
nodes_features, edges_features = converter.convert()

# Warnungen auslesen
for w in converter.warnings:
    print(w)

# Feature-Struktur
# nodes_features: [{"geometry": (x, y), "attrs": {...}}, ...]
# edges_features: [{"geometry": [(x1,y1), (x2,y2), ...], "attrs": {...}}, ...]
```

Rückgabe von `convert()`:

| Variable | Typ | Beschreibung |
|---|---|---|
| `nodes_features` | `list[dict]` | Gleisknoten; `geometry` = `(x, y)`-Tupel, `attrs` = Attribut-Dict |
| `edges_features` | `list[dict]` | Gleiskanten; `geometry` = Liste von `(x, y)`-Tupeln, `attrs` = Attribut-Dict |

Die Attributfelder entsprechen den in [st3-Import (Technische Dokumentation).md → Zielattribute](st3-Import%20%28Technische%20Dokumentation%29.md#zielattribute)
beschriebenen Feldern.

### Direktaufruf der Hüllkurven-Konvertierung

```python
from convert.convert_envelope import convert_envelope

envelope_features = convert_envelope(
    input_path=r"C:\...\Freudenstein_2025.st3",
    target_epsg=31467,
    auto_detect_crs=True,
    fallback_epsg=32632,
)

# Leer, wenn kein <Huellkurve>-Element vorhanden
if envelope_features:
    feat = envelope_features[0]
    # feat["geometry"]: [(x1, y1), (x2, y2), ...] — Ring nicht geschlossen
    # feat["attrs"]:    {"id": 1, "streckenmodul": "Freudenstein_2025", "utm_zone": 32}
```