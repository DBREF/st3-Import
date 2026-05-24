# st3-Importer – Bedienung und Konfiguration

## Übersicht

Der st3-Importer überführt Zusi-3-Streckendateien (`.st3`) in QGIS-Memory-Layer.
Pro importierter Datei entstehen zwei Layer:

| Layer-Name | Geometrietyp | Inhalt |
|---|---|---|
| `<stem> – Gleiskante` | LineString | Gleisabschnitte zwischen Knoten |
| `<stem> – Gleisknoten` | Point | Weichen, Modulgrenzen, Gleisenden |

`<stem>` ist der Dateiname der `.st3`-Datei ohne Erweiterung
(z. B. `Freudenstein_2025`).

Die eigentliche Konvertierungslogik liegt im Paket
`modules/external/st3_converter/` (Klasse `ST32QGISConverter`).
Das vorliegende Dokument beschreibt ausschließlich die Bedienoberfläche und
die Konfigurationsoptionen des Importers.

> **Technische Hintergründe** zu Algorithmus, Datenformat und Zielmodell
> sind in [st3-Import (Technisch).md](st3-Import%20(Technisch).md) dokumentiert.

---

## Voraussetzungen

| Komponente | Beschreibung |
|---|---|
| `modules/external/st3_converter/st3_converter.py` | Konverter-Modul; wird beim Öffnen des Dialogs automatisch geprüft |
| `lxml` | Python-Bibliothek für XML-Parsing (muss in der QGIS-Python-Umgebung verfügbar sein) |
| `pyproj` | Koordinatentransformation; erwartet die PROJ-Datendateien |
| PROJ-Daten (`de_adv_BETA2007.tif`) | Optional; wird aus `C:\OSGeo4W\share\proj` geladen, sofern vorhanden, für genaue DHDN↔WGS84-Transformation |

Ist der Konverter nicht verfügbar, erscheint beim Öffnen des Dialogs eine
Warnmeldung. Der Import-Menüeintrag bleibt sichtbar.

---

## Dialog öffnen

**Menü:** `📥 Daten/Pläne importieren…`

Der Dialog öffnet sich unabhängig von der aktuellen QGIS-Kartenansicht.
Er merkt sich die zuletzt verwendeten Einstellungen (Pfad, KBS-Codes,
Protokolloptionen) über den `SettingsManager`, sofern in den InfraQGIS-
Einstellungen „Dialogeinstellungen merken" aktiv ist.

---

## Format-Auswahl

Das Auswahlfeld **Format** zeigt alle verfügbaren Import-Module mit Version.
Derzeit steht ausschließlich das st3-Format zur Verfügung:

```
st3 (Zusi 3-Streckendatei) (v1.0.0)
```

---

## Datei- / Ordner-Auswahl

### Einzeldatei-Import (Standard)

- Der Eingabepfad zeigt auf eine einzelne `.st3`-Datei.
- „Durchsuchen…" öffnet einen Datei-Auswahldialog (Filter: `*.st3`).
- Beim ersten Öffnen wird das Zusi-3-Datenverzeichnis aus der Windows-Registry
  vorbelegt (`HKLM\SOFTWARE\Zusi3\DatenVerzeichnis`), sofern vorhanden.

### Batch-Import (Ordner)

Checkbox **„Ordner-Import (Batch-Verarbeitung aller st3-Dateien im Ordner)"**:

- Der Eingabepfad zeigt auf einen Ordner.
- Alle `.st3`-Dateien im Ordner werden nacheinander importiert.
- Zwei zusätzliche Optionen werden eingeblendet:

| Option | Beschreibung |
|---|---|
| **Unterordner einbeziehen (rekursive Suche)** | Durchsucht den Ordner und alle Unterordner; die Unterordner-Struktur wird als verschachtelte Layer-Gruppen abgebildet |
| **Alle Dateien in einem Layer zusammenführen** | Kanten und Knoten aller Dateien werden in je einem einzigen Layer zusammengefasst (Layer-Name = Ordnername); ansonsten erhält jede Datei eine eigene Untergruppe |

---

## Registerkarte „Allgemein"

### Quell-KBS automatisch erkennen

Ist diese Option aktiv (Standard: **ein**), liest der Konverter die UTM-Zone
aus dem `<UTM UTM_Zone="…">`-Element der `.st3`-Datei und leitet daraus den
Quell-EPSG ab (Formel: `32600 + Zone`, z. B. Zone 32 → EPSG:32632).

### Rückfall-KBS

EPSG-Code, der als Quell-KBS verwendet wird, wenn die automatische Erkennung
fehlschlägt (Standard: **32632**). Das Feld ist nur aktiv, solange
„Quell-KBS automatisch erkennen" eingeschaltet ist.

> Ist die automatische Erkennung deaktiviert, wird **kein** Fallback angewendet –
> Quell- und Ziel-KBS werden als identisch behandelt und keine Transformation
> durchgeführt.

### Ziel-KBS

EPSG-Code der Ziel-Koordinatenbezugssystems der erzeugten QGIS-Layer
(Standard: **31467** – DHDN/Gauß-Krüger Zone 3).

---

## Registerkarte „Protokoll"

| Option | Beschreibung |
|---|---|
| **Protokoll erstellen** | Schreibt eine `.log`-Datei neben der Quelldatei (bzw. im Quellordner beim Batch-Import). Dateiname: `<stem>_import.log` |
| **Protokoll nach Abschluss öffnen** | Öffnet die Protokolldatei automatisch nach dem Import; nur aktiv wenn „Protokoll erstellen" eingeschaltet ist |

Das Protokoll enthält:

- Zeitstempel aller Verarbeitungsschritte
- Anzahl erkannter Knoten und Kanten
- Alle Konvertierungswarnungen (Nulllängen-Elemente, hochgradige Vertices,
  Koordinatenabweichungen, isolierte Komponenten, geschlossene Schleifen)
- Fehlermeldungen mit vollständigem Traceback

---

## Importvorgang

Nach Klick auf **Importieren** läuft der Import mit einer Fortschrittsanzeige
(8 Schritte pro Datei). Der Import-Button ist während der Verarbeitung deaktiviert.
Abbrechen ist nicht möglich.

Bei **Erfolg** erscheint eine Meldung; ist „Protokoll nach Abschluss öffnen"
aktiv, öffnet sich die Log-Datei automatisch. Der Dialog schließt sich.

Bei **Fehler** bleibt der Dialog geöffnet; die Fehlermeldung verweist auf das
Protokoll.

---

## Layer-Struktur in QGIS

### Einzeldatei-Import

```
[Projektebene]
  └─ <stem>                    ← Layer-Gruppe (oben eingefügt)
       ├─ <stem> – Gleisknoten  ← Point-Layer
       └─ <stem> – Gleiskante   ← LineString-Layer
```

### Batch-Import (ohne „Zusammenführen")

```
[Projektebene]
  └─ <Ordnername>              ← übergeordnete Layer-Gruppe (oben eingefügt)
       ├─ <stem_1>
       │    ├─ <stem_1> – Gleisknoten
       │    └─ <stem_1> – Gleiskante
       ├─ <stem_2>
       │    ├─ ...
       ...
       └─ [<Unterordner>/]     ← nur bei „Unterordner einbeziehen"
            └─ <stem_n>
                 └─ ...
```

### Batch-Import mit „Zusammenführen"

```
[Projektebene]
  └─ <Ordnername>              ← Layer-Gruppe
       ├─ <Ordnername> – Gleisknoten  ← alle Knoten aller Dateien
       └─ <Ordnername> – Gleiskante   ← alle Kanten aller Dateien
```

Alle Layer sind QGIS-Memory-Layer (Typ `memory`); sie werden nicht
automatisch gespeichert. Zum dauerhaften Erhalt sind sie manuell in ein
GeoPackage oder eine andere Zieldatenbank zu exportieren.

---

## Einstellungen-Persistenz

Folgende Felder werden automatisch gespeichert und beim nächsten Öffnen
des Dialogs wiederhergestellt (Schlüssel: `InfraQGIS/import_external/last_settings`):

| Feld | gespeicherter Wert |
|---|---|
| Pfad | letzter Datei- oder Ordnerpfad |
| Batch-Modus | Checkbox-Zustand |
| Rekursiv | Checkbox-Zustand |
| Zusammenführen | Checkbox-Zustand |
| Quell-KBS auto | Checkbox-Zustand |
| Rückfall-EPSG | Eingabewert |
| Ziel-EPSG | Eingabewert |
| Protokoll erstellen | Checkbox-Zustand |
| Protokoll öffnen | Checkbox-Zustand |

Die Persistenz greift nur, wenn in den InfraQGIS-Einstellungen
`InfraQGIS/remember_dialog_settings = True` gesetzt ist.

---

## Programmatische Nutzung

Der Import kann auch ohne Dialog direkt aus Python aufgerufen werden.
Da `import` ein Python-Schlüsselwort ist, muss das Modul über `importlib` geladen werden
(so auch in `InfraQGIS.py` umgesetzt):

```python
import importlib

_mod = importlib.import_module(
    ".modules.import.import_external", package="InfraQGIS"
)
import_from_st3 = _mod.import_from_st3
import_batch_from_st3 = _mod.import_batch_from_st3

config = {
    "target_epsg": 31467,       # Ziel-KBS
    "auto_detect_crs": True,    # UTM-Zone aus <UTM> lesen
    "fallback_epsg": 32632,     # Fallback, falls Erkennung fehlschlägt
    "create_log_file": True,    # Protokoll neben der Quelldatei speichern
    "open_log_file": False,     # Protokoll nicht automatisch öffnen
}

# Einzeldatei
success, log_path = import_from_st3(
    r"C:\Zusi3\Routes\DB\Freudenstein\Freudenstein_2025.st3",
    plugin_instance=None,       # None erlaubt (kein QGIS-Dialog benötigt)
    config=config,
)

# Batch (Ordner)
config["recursive"] = True
config["merge"] = False
success, log_path = import_batch_from_st3(
    r"C:\Zusi3\Routes\DB\Freudenstein",
    plugin_instance=None,
    config=config,
)
```

> **Hinweis:** `plugin_instance` wird derzeit nicht aktiv verwendet; `None`
> ist ein gültiger Wert für den programmatischen Aufruf außerhalb von QGIS.

### Direktaufruf des Konverters

Für vollständige Unabhängigkeit von QGIS und dem Importer-Layer kann
`ST32QGISConverter` direkt verwendet werden:

```python
from modules.external.st3_converter.st3_converter import ST32QGISConverter

converter = ST32QGISConverter(
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

Die Attributfelder entsprechen den in [st3-Import (Technisch).md → Zielattribute](st3-Import%20(Technisch).md#zielattribute)
beschriebenen Feldern.
