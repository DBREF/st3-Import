# st3-Import: convert_envelope.py
# Copyright (c) 2026 Fabian Schöpflin. Alle Rechte vorbehalten.

# --- Standardbibliotheken ---
from pathlib import Path
from typing import Any

# --- Drittanbieter-Bibliotheken ---
from lxml import etree as ET
from pyproj import Transformer

# Transformer-Cache: {(source_epsg, target_epsg): Transformer}
# Verhindert wiederholte pyproj-DB-Lookups im Batch-Betrieb.
_TRANSFORMER_CACHE: dict = {}


def convert_envelope(
    input_path: str,
    target_epsg: int = 31467,
    auto_detect_crs: bool = True,
    fallback_epsg: int = 32632,
    _route_el: Any = None,
) -> list:
    """Liest die Hüllkurve aus einer st3-Datei und erstellt ein Polygon-Feature.

    Die Koordinaten werden identisch zu den StrElement-Koordinaten verarbeitet:
    absolute UTM-Koordinate = UTM_WE * 1000 + X bzw. UTM_NS * 1000 + Y.
    Anschließend erfolgt eine optionale Transformation in das Ziel-KBS.

    Parameter:
        input_path:      Pfad zur st3-Eingabedatei
        target_epsg:     EPSG-Code des Ziel-Koordinatenbezugssystems
        auto_detect_crs: Quell-KBS automatisch aus dem <UTM>-Element ermitteln
        fallback_epsg:   Rückfall-EPSG-Code, wenn die Auto-Erkennung fehlschlägt
        _route_el:       Interner Parameter: bereits geparstes lxml <Strecke>-Element.
                         Wenn übergeben, wird ET.parse() übersprungen (kein zweiter
                         Disk-Zugriff). Nur für den Aufruf aus import_external.py.

    Rückgabe:
        Liste mit 0 oder 1 Feature-Dict:
        [{"geometry": [(x, y), ...], "attrs": {"id": 1, "streckenmodul": str}}]

        Leer, wenn kein <Huellkurve>-Element vorhanden oder weniger als 3 Punkte.
    """
    input_path = Path(input_path)
    stem = input_path.stem

    if _route_el is not None:
        route = _route_el
    else:
        tree = ET.parse(str(input_path))
        root = tree.getroot()
        route = root.find("Strecke")
        if route is None:
            return []

    utm = route.find("UTM")
    if utm is None:
        return []

    utm_we = float(utm.get("UTM_WE", "0"))
    utm_ns = float(utm.get("UTM_NS", "0"))
    utm_zone = int(utm.get("UTM_Zone", "32"))
    source_epsg = (32600 + utm_zone) if auto_detect_crs else fallback_epsg

    huellkurve = route.find("Huellkurve")
    if huellkurve is None:
        return []

    base_x = utm_we * 1000.0
    base_y = utm_ns * 1000.0
    pts_utm = [
        (base_x + float(pt.get("X", "0")), base_y + float(pt.get("Y", "0")))
        for pt in huellkurve.findall("PunktXYZ")
    ]

    if len(pts_utm) < 3:
        return []

    if source_epsg != target_epsg:
        key = (source_epsg, target_epsg)
        if key not in _TRANSFORMER_CACHE:
            _TRANSFORMER_CACHE[key] = Transformer.from_crs(
                f"EPSG:{source_epsg}",
                f"EPSG:{target_epsg}",
                always_xy=True,
            )
        transformer = _TRANSFORMER_CACHE[key]
        xs = [p[0] for p in pts_utm]
        ys = [p[1] for p in pts_utm]
        txs, tys = transformer.transform(xs, ys)
        pts = list(zip(txs, tys))
    else:
        pts = pts_utm

    return [
        {
            "geometry": pts,
            "attrs": {
                "id": 1,
                "streckenmodul": stem,
                "utm_zone": utm_zone,
            },
        }
    ]
