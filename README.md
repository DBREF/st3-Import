## st3-Import

Konverter für Zusi-3-Streckendateien (`.st3`) in ein topologisches Knoten-Kanten-Modell für QGIS.

**Funktionen:**

- Import von Einzel- oder Batch-Dateien (inkl. rekursiver Ordnerdurchsuche)
- Automatische KBS-Erkennung aus dem `<UTM UTM_Zone="…">`-Element (EPSG: 32600 + Zone)
- Optionale hochpräzise DHDN↔WGS84-Transformation via BETA2007-NTv2-Gitter (`de_adv_BETA2007.tif`)
- Topologie-basierte Knotenklassifikation: `Gleisende` (Grad 1), `Weiche` (Grad ≥ 3), `Modulgrenze` (Modulverweis)
- Erkennung und Normalisierung von Weichen-Signalnamen (EW, DKW, EKW)
- Propagation von Weichenbauform-Beschriftungen über BoundingR-Radius
- Kilometrierungsinterpolation entlang Kanten aus StrElement-km-Attributen
- Validierungswarnungen: Nulllängen-Elemente, hochgradige Vertices (Grad ≥ 5), Koordinatenabweichungen (> 5 cm), isolierte Komponenten, geschlossene Schleifen
- Batch-Modus mit optionalem Layer-Zusammenführen (alle Dateien in je einem Knoten- und Kanten-Layer)
- Logging in QGIS (`QgsMessageLog`) und Standalone (stdout)
- Ausführliches Konvertierungsprotokoll (`.log`-Datei neben der Quelldatei)

**Ausgabe pro importierter `.st3`-Datei:**

| Layer | Geometrietyp | Inhalt |
|---|---|---|
| `<stem> – Gleiskante` | LineString | Gleisabschnitte zwischen Knoten |
| `<stem> – Gleisknoten` | Point | Weichen, Modulgrenzen, Gleisenden |

`<stem>` entspricht dem Dateinamen der `.st3`-Datei ohne Erweiterung.  
Die erzeugten Layer sind QGIS-Memory-Layer und müssen manuell in ein GeoPackage o. ä. exportiert werden.

**Verzeichnisstruktur:**

```
  core/
    core.py               # Logging-System, Versionskonstante
  docs/
    Dokumentation.md      # Bedienungsanleitung und Konfigurationsreferenz
    Technische Dokumentation.md  # Algorithmus, Datenformat, Zielmodell
  files/
    GeoJSON/              # Exportierte GeoJSON-Dateien
    GeoPackage/           # Exportierte GeoPackage-Dateien
    KML/                  # Exportierte KML-Dateien
  st3_converter.py        # Hauptklasse st3Converter
```

**Abhängigkeiten:** `lxml`, `pyproj`

**Dokumentation:** [Dokumentation.md](docs/Dokumentation.md) · [Technische Dokumentation.md](docs/Technische%20Dokumentation.md)

**Verwendung (Standalone):**

```python
from st3_converter import st3Converter

converter = st3Converter(
    input_path="Strecke.st3",
    target_epsg=31467,       # Ziel-KBS: DHDN/GK Zone 3
    auto_detect_crs=True,    # UTM-Zone automatisch aus Datei lesen
)
nodes_features, edges_features = converter.convert()
```

**Verwendung in QGIS:**

Der Importer wird über **Menü → Daten/Pläne importieren…** aufgerufen und unterstützt Einzel- sowie Batch-Import mit konfigurierbaren KBS-Codes und optionaler Protokolldatei.

---

## Lizenz

Copyright © 2026 Fabian Schöpflin. Alle Rechte vorbehalten.  
Autor: Fabian Schöpflin  
Kontakt: Fabian.Schoepflin@infrageo.de
