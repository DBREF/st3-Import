# st3_converter: st3_converter.py
# Copyright (c) 2026 Fabian Schöpflin. Alle Rechte vorbehalten.

# --- Standardbibliotheken ---
import math
import os
import re
from pathlib import Path

# PROJ-Datenpfad um OSGeo4W-Verzeichnis erweitern, BEVOR pyproj importiert wird,
# damit de_adv_BETA2007.tif bei der Initialisierung gefunden wird.
_osgeo4w_proj = Path(r"C:\OSGeo4W\share\proj")
if _osgeo4w_proj.is_dir() and (_osgeo4w_proj / "de_adv_BETA2007.tif").exists():
    _proj_data = os.environ.get("PROJ_DATA", "")
    if str(_osgeo4w_proj) not in _proj_data:
        os.environ["PROJ_DATA"] = str(_osgeo4w_proj) + (
            ";" + _proj_data if _proj_data else ""
        )

# --- Drittanbieter-Bibliotheken ---
from core.core import VERSION, logger  # noqa: F401
from lxml import etree as ET
from pyproj import Transformer

# Hilfsfunktionen


def _successor_side(connection: int, idx: int, direction: str) -> str:
    """'g' oder 'b' — Seite des idx-ten Nachfolgers, die an E anschließt.

    direction ∈ {"NORM", "GEGEN"}: an welcher Seite von E der Nachfolger hängt.
    Bit=0 → g-Seite des Nachfolgers schließt an; Bit=1 → b-Seite.
    """
    shift = idx + (8 if direction == "GEGEN" else 0)
    return "b" if (connection >> shift) & 1 else "g"


class _UnionFind:
    """Union-Find (Disjoint Set Union) mit Pfadkompression und Rang-Heuristik."""

    def __init__(self):
        self._parent: dict = {}
        self._rank: dict = {}

    def find(self, x):
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1


# Hauptklasse


class ST32QGISConverter:
    """Konvertiert eine Zusi-3-Streckendatei (.st3) in ein Knoten-Kanten-Modell.

    Rückgabe von convert():
        (nodes_features, edges_features): Listen von Feature-Dicts mit
        'geometry' (Koordinatenliste bzw. -punkt im Ziel-KBS) und 'attrs' (dict).
    """

    def __init__(
        self,
        input_path: str,
        target_epsg: int = 31467,
        auto_detect_crs: bool = True,
        progress_callback=None,
    ):
        self.input_path = Path(input_path)
        self.target_epsg = target_epsg
        self.auto_detect_crs = auto_detect_crs
        self._cb = progress_callback or (lambda cur, total, msg: None)
        self._stem = self.input_path.stem
        self.warnings: list = []

    # Public API

    def convert(self):
        """Führt die vollständige Konvertierung in 8 Schritten durch.

        Rückgabe:
            (nodes_features, edges_features) — Listen von Feature-Dicts
        """
        self._cb(0, 8, "Schritt 1: Lese XML…")
        elems, utm_epsg = self._parse_xml()
        logger.info(
            f"[{self._stem}] Schritt 1: {len(elems)} StrElemente (Quell-EPSG: {utm_epsg})"
        )

        self._cb(1, 8, "Schritt 2: Baue Topologie auf…")
        vertex_inc, uf = self._build_topology(elems)
        logger.info(f"[{self._stem}] Schritt 2: {len(vertex_inc)} Vertices")

        self._cb(2, 8, "Schritt 3: Registriere Modulgrenz-Vertices…")
        module_vertices = self._module_vertices(elems, uf)
        logger.info(
            f"[{self._stem}] Schritt 3: {len(module_vertices)} Modulgrenz-Vertices"
        )

        self._cb(3, 8, "Schritt 4: Klassifiziere Breakpoints…")
        bp_set, nodes_raw = self._classify_breakpoints(
            vertex_inc, module_vertices, elems, uf
        )
        logger.info(
            f"[{self._stem}] Schritt 4: {len(bp_set)} Breakpoint-Vertices, "
            f"{len(nodes_raw)} Knoten-Features"
        )

        self._cb(4, 8, "Schritt 5: Validiere Topologie…")
        self._validate_topology(elems, vertex_inc, uf, bp_set)

        self._cb(5, 8, "Schritt 6: Traversierung…")
        edges_raw = self._traverse_edges(elems, vertex_inc, uf, bp_set, nodes_raw)
        self._fill_node_km_from_edges(nodes_raw, edges_raw)
        logger.info(f"[{self._stem}] Schritt 6: {len(edges_raw)} Kanten")

        self._cb(6, 8, "Schritt 7: Koordinatentransformation…")
        source_epsg = utm_epsg if self.auto_detect_crs else self.target_epsg
        edges_tf, nodes_tf = self._transform_coordinates(
            edges_raw, nodes_raw, source_epsg
        )

        self._cb(7, 8, "Schritt 8: Erstelle Layer-Daten…")
        result = self._build_features(edges_tf, nodes_tf)
        self._cb(8, 8, "Abgeschlossen.")
        return result

    # Schritt 1 – XML einlesen und StrElemente sammeln

    def _parse_xml(self):
        tree = ET.parse(str(self.input_path))
        root = tree.getroot()
        route = root.find("Strecke")
        if route is None:
            raise ValueError(f"Kein <Strecke>-Element in {self.input_path}")

        utm = route.find("UTM")
        if utm is None:
            raise ValueError(f"Kein <UTM>-Element in {self.input_path}")

        utm_we = float(utm.get("UTM_WE", "0"))
        utm_ns = float(utm.get("UTM_NS", "0"))
        utm_zone = int(utm.get("UTM_Zone", "32"))
        utm_epsg = 32600 + utm_zone

        elems = {}
        for se in route.findall("StrElement"):
            nr_str = se.get("Nr")
            if nr_str is None:
                continue
            nr = int(nr_str)
            fkt = int(se.get("Fkt", "0"))
            if fkt & 2:  # Bit 1 = „Keine Gleisfunktion" → überspringen
                continue

            # ── Einmalig über alle Kindelemente iterieren (statt ~10× se.find) ──
            g_el = b_el = info_gegen = info_norm = nnm_el = ngm_el = None
            nach_norm_els: list = []
            nach_gegen_els: list = []
            signal_els: list = []
            for child in se:
                tag = child.tag
                if tag == "g":
                    g_el = child
                elif tag == "b":
                    b_el = child
                elif tag == "InfoGegenRichtung":
                    info_gegen = child
                    signal_els.extend(child.findall("Signal"))
                elif tag == "InfoNormRichtung":
                    info_norm = child
                    signal_els.extend(child.findall("Signal"))
                elif tag == "NachNorm":
                    nach_norm_els.append(child)
                elif tag == "NachGegen":
                    nach_gegen_els.append(child)
                elif tag == "NachNormModul":
                    nnm_el = child
                elif tag == "NachGegenModul":
                    ngm_el = child
                elif tag == "Signal":
                    signal_els.append(child)

            if g_el is None or b_el is None:
                continue

            gx = utm_we * 1000.0 + float(g_el.get("X", "0"))
            gy = utm_ns * 1000.0 + float(g_el.get("Y", "0"))
            bx = utm_we * 1000.0 + float(b_el.get("X", "0"))
            by = utm_ns * 1000.0 + float(b_el.get("Y", "0"))

            # Kilometrierung: InfoGegenRichtung, Fallback InfoNormRichtung
            km_val = None
            for info_el in (info_gegen, info_norm):
                if info_el is not None:
                    km_str = info_el.get("km", "")
                    if km_str:
                        try:
                            km_val = float(km_str)
                            break
                        except ValueError:
                            pass

            # Nachfolger im selben Modul
            nach_norm = [
                int(e.get("Nr")) for e in nach_norm_els if e.get("Nr") is not None
            ]
            nach_gegen = [
                int(e.get("Nr")) for e in nach_gegen_els if e.get("Nr") is not None
            ]

            # Modulverweise (NachNormModul / NachGegenModul)
            nach_norm_modul = None
            if nnm_el is not None:
                d = nnm_el.find("Datei")
                if d is not None:
                    fn = d.get("Dateiname", "")
                    if fn:
                        nach_norm_modul = Path(fn.replace("\\", "/")).stem or None

            nach_gegen_modul = None
            if ngm_el is not None:
                d = ngm_el.find("Datei")
                if d is not None:
                    fn = d.get("Dateiname", "")
                    if fn:
                        nach_gegen_modul = Path(fn.replace("\\", "/")).stem or None

            # Signale
            signals = []
            for sig in signal_els:
                sig_typ = sig.get("SignalTyp", "0")
                sig_name = sig.get("Signalname", "")
                frame_dateien = [
                    d_el.get("Dateiname", "")
                    for sf_el in sig.findall("SignalFrame")
                    for d_el in [sf_el.find("Datei")]
                    if d_el is not None and d_el.get("Dateiname", "")
                ]
                signals.append(
                    {
                        "typ": sig_typ,
                        "name": sig_name,
                        "frame_dateien": frame_dateien,
                        "bounding_r": float(sig.get("BoundingR", "0") or "0"),
                    }
                )

            connection = int(se.get("Anschluss", "0"))

            elems[nr] = {
                "nr": nr,
                "fkt": fkt,
                "g_coord": (gx, gy),
                "b_coord": (bx, by),
                "km": km_val,
                "nach_norm": nach_norm,
                "nach_gegen": nach_gegen,
                "nach_norm_modul": nach_norm_modul,
                "nach_gegen_modul": nach_gegen_modul,
                "signals": signals,
                "connection": connection,
            }

        return elems, utm_epsg

    # Schritt 2 – Element-Seiten-Topologie aufbauen (Union-Find)

    def _build_topology(self, elems):
        uf = _UnionFind()

        # Alle Element-Seiten initialisieren
        for nr in elems:
            uf.find((nr, "g"))
            uf.find((nr, "b"))

        for nr, elem in elems.items():
            connection = elem["connection"]
            for i, aft_nr in enumerate(elem["nach_norm"]):
                if aft_nr not in elems:
                    continue
                seite = _successor_side(connection, i, "NORM")
                uf.union((nr, "b"), (aft_nr, seite))
            for j, aft_nr in enumerate(elem["nach_gegen"]):
                if aft_nr not in elems:
                    continue
                seite = _successor_side(connection, j, "GEGEN")
                uf.union((nr, "g"), (aft_nr, seite))

        # vertex_inc[vertex_root] → [(elem_nr, seite), …]
        vertex_inc = {}
        for nr in elems:
            for side in ("g", "b"):
                root = uf.find((nr, side))
                if root not in vertex_inc:
                    vertex_inc[root] = []
                vertex_inc[root].append((nr, side))

        return vertex_inc, uf

    # Schritt 3 – Modulgrenz-Vertices registrieren

    def _module_vertices(self, elems, uf):
        """Rückgabe: dict vertex_id → nachbarmodul_stem"""
        module_vertices = {}
        for nr, elem in elems.items():
            if elem["nach_norm_modul"]:
                v = uf.find((nr, "b"))
                module_vertices[v] = elem["nach_norm_modul"]
            if elem["nach_gegen_modul"]:
                v = uf.find((nr, "g"))
                module_vertices[v] = elem["nach_gegen_modul"]
        return module_vertices

    # Schritt 4 – Breakpoints klassifizieren

    def _classify_breakpoints(self, vertex_inc, module_vertices, elems, uf):
        """Rückgabe: (bp_set, nodes_raw)
        bp_set:     set von Vertex-IDs, die Breakpoints sind
        nodes_raw: list von dicts — ein Eintrag pro Knoten-Feature
        """
        bp_set = set()
        nodes_raw = []

        for v, inc in vertex_inc.items():
            extent = len(inc)
            is_module = v in module_vertices

            # Knotentypen an diesem Vertex bestimmen
            typen = []
            if is_module:
                typen.append("Modulgrenze")
                if extent >= 3:
                    typen.append("Weiche")
            elif extent == 1:
                typen.append("Gleisende")
            elif extent >= 3:
                typen.append("Weiche")

            if not typen:
                continue  # Grad 2, kein Modulverweis → kein Breakpoint

            bp_set.add(v)

            # Repräsentatives Element (kleinste Nr)
            repr_nr = min(nr for (nr, _) in inc)
            repr_side = next(s for (nr, s) in inc if nr == repr_nr)
            repr_elem = elems[repr_nr]

            # Signal-Attribute (alle Elemente an diesem Vertex prüfen)
            signal_name = None
            knotenbeschr = ""
            knotenbeschr_r = 0.0
            for elem_nr, _ in inc:
                elem = elems.get(elem_nr, {})
                for sig in elem.get("signals", []):
                    if sig.get("typ") == "2":
                        if not signal_name:
                            signal_name = sig.get("name") or None
                        if not knotenbeschr:
                            for fd in sig.get("frame_dateien", []):
                                idx = fd.lower().find("_schienen")
                                if idx >= 0:
                                    knotenbeschr = (
                                        fd[:idx]
                                        .replace("\\", "/")
                                        .split("/")[-1]
                                        .strip("_")
                                    )
                                    knotenbeschr_r = sig.get("bounding_r", 0.0)
                                    break

            # Knotenname und Feature-Dict pro Typ anlegen
            suffix_map = {"Modulgrenze": "G", "Gleisende": "E"}
            for typ in typen:
                if signal_name:
                    if typ == "Weiche":
                        knotenname = self._normalize_switch_name(signal_name)
                    else:
                        knotenname = signal_name
                else:
                    suffix = suffix_map.get(typ, "X")
                    knotenname = f"{self._stem}_{repr_nr}{suffix}"

                nodes_raw.append(
                    {
                        "vertex": v,
                        "typ": typ,
                        "knotenname": knotenname,
                        "knotenbeschr": knotenbeschr,
                        "knotenbeschr_r": knotenbeschr_r,
                        "nr": repr_nr,
                        "km": repr_elem.get("km"),
                        "datei": self._stem,
                        "nachbarmodul": module_vertices.get(v, "")
                        if typ == "Modulgrenze"
                        else "",
                        "repr_side": repr_side,
                        "repr_coord_utm": repr_elem["g_coord"]
                        if repr_side == "g"
                        else repr_elem["b_coord"],
                    }
                )

        self._propagate_node_desc(nodes_raw)
        return bp_set, nodes_raw

    @staticmethod
    def _normalize_switch_name(signal_name: str) -> str:
        """Normalisiert einen Weichen-Signalnamen auf das Schema <Nr>[<DKW-Suffix>].

        Regeln:
        - Die erste Zahl im Namen wird extrahiert.
        - Ein optionaler DKW-Suffix (a, b, c, d, a/b, c/d) direkt nach der Zahl
          wird beibehalten und in Großbuchstaben umgewandelt.
        - Alle anderen Buchstaben davor und danach werden entfernt.
        - Kein Match → Signal-Name unverändert zurückgeben.

        Beispiele:
            "W 1"       → "1"
            "EW 135"    → "135"
            "DKW 3 A"   → "3A"
            "DKW 3 a/b" → "3A/B"
            "DKW 3 c/d" → "3C/D"
        """
        m = re.search(r"(\d+)\s*(a/b|c/d|[a-dA-D])?", signal_name, re.IGNORECASE)
        if not m:
            return signal_name
        number = m.group(1)
        suffix = m.group(2)
        if suffix:
            return number + suffix.upper().replace("/", "/")
        return number

    def _propagate_node_desc(self, nodes_raw: list) -> None:
        """Überträgt knotenbeschr von beschrifteten Weichenknoten auf benachbarte
        unbeschriftete Weichenknoten derselben Weichenbaugruppe (EKW/DKW).

        Grundlage: Das BoundingR-Attribut des Weichensignals umschließt alle
        Geometrierahmen der Baugruppe; jeder Weichenknoten innerhalb dieses
        Radius erhält dieselbe Bauform-Beschriftung, sofern er noch keine hat.
        """
        labeled = [
            kn
            for kn in nodes_raw
            if kn["typ"] == "Weiche"
            and kn["knotenbeschr"]
            and kn.get("knotenbeschr_r", 0.0) > 0.0
        ]
        if not labeled:
            return
        unlabeled = [
            kn for kn in nodes_raw if kn["typ"] == "Weiche" and not kn["knotenbeschr"]
        ]
        for src in labeled:
            sx, sy = src["repr_coord_utm"]
            r = src["knotenbeschr_r"]
            for tgt in unlabeled:
                if tgt["knotenbeschr"]:
                    continue
                tx, ty = tgt["repr_coord_utm"]
                if math.hypot(sx - tx, sy - ty) <= r:
                    tgt["knotenbeschr"] = src["knotenbeschr"]

    # Schritt 5 – Topologie-Validierung

    def _validate_topology(self, elems, vertex_inc, uf, bp_set):
        # Nulllängen-Elemente (g == b)
        for nr, elem in elems.items():
            gx, gy = elem["g_coord"]
            bx, by = elem["b_coord"]
            if math.isclose(gx, bx, abs_tol=1e-6) and math.isclose(
                gy, by, abs_tol=1e-6
            ):
                msg = f"Nulllängen-Element Nr={nr} (g≡b). Element wird übersprungen."
                self.warnings.append(msg)
                logger.warning(msg)

        # Hochgradige Vertices (Grad ≥ 5)
        for v, inc in vertex_inc.items():
            if len(inc) >= 5:
                repr_nr = min(nr for (nr, _) in inc)
                coord = elems[repr_nr]["g_coord"]
                msg = (
                    f"Hochgradiger Vertex Grad={len(inc)} "
                    f"bei Element Nr={repr_nr} (UTM: {coord[0]:.1f}, {coord[1]:.1f})."
                )
                self.warnings.append(msg)
                logger.warning(msg)

        # Koordinaten-Abweichung > 5 cm bei topologisch verbundenen Seiten
        for nr, elem in elems.items():
            for i, aft_nr in enumerate(elem["nach_norm"]):
                if aft_nr not in elems:
                    continue
                seite = _successor_side(elem["connection"], i, "NORM")
                coord_a = elem["b_coord"]
                coord_b = (
                    elems[aft_nr]["g_coord"]
                    if seite == "g"
                    else elems[aft_nr]["b_coord"]
                )
                dx = coord_a[0] - coord_b[0]
                dy = coord_a[1] - coord_b[1]
                if dx * dx + dy * dy > 0.0025:  # > 0.05 m (sqrt gespart)
                    dist = math.sqrt(dx * dx + dy * dy)
                    msg = (
                        f"Koordinatenabweichung {dist:.3f} m zwischen "
                        f"Element {nr}.b und Element {aft_nr}.{seite} "
                        f"(NachNorm[{i}])."
                    )
                    self.warnings.append(msg)
                    logger.warning(msg)

        # Isolierte Komponenten (Zusammenhangskomponenten ohne Gleisende/Modulgrenze)
        # Elemente-Ebene: Union-Find auf elem_nr
        elem_uf = _UnionFind()
        for nr in elems:
            elem_uf.find(nr)
        for v, inc in vertex_inc.items():
            nrs = [nr for (nr, _) in inc]
            for k in range(1, len(nrs)):
                elem_uf.union(nrs[0], nrs[k])

        comp_map: dict = {}
        for nr in elems:
            root = elem_uf.find(nr)
            comp_map.setdefault(root, []).append(nr)

        for comp_elems in comp_map.values():
            if len(comp_elems) < 2:
                continue
            has_bp = any(
                uf.find((nr, s)) in bp_set for nr in comp_elems for s in ("g", "b")
            )
            if not has_bp:
                msg = (
                    f"Isolierte Komponente ohne Gleisende/Modulgrenze: "
                    f"{len(comp_elems)} Elemente (erster: Nr={min(comp_elems)})."
                )
                self.warnings.append(msg)
                logger.warning(msg)

    # Schritt 6 – Graphtraversierung: Kanten bilden

    @staticmethod
    def _interpolate_km(elem_seq, pts_utm, elems):
        """Gibt (km_von, km_bis) für eine Kante zurück.

        Fehlende km-Werte werden linear aus den bekannten km-Werten der
        StrElemente interpoliert/extrapoliert, gewichtet nach kumulativer
        Bogenlänge. pts_utm[i] ist der Eintrittspunkt von elem_seq[i];
        pts_utm[-1] ist der Austrittspunkt des letzten Elements.

        Gibt (None, None) zurück, wenn keine km-Daten vorhanden.
        """
        # Kumulative Bogenlängen an den Eintrittspunkten der Elemente
        s = [0.0]
        for i in range(1, len(pts_utm)):
            dx = pts_utm[i][0] - pts_utm[i - 1][0]
            dy = pts_utm[i][1] - pts_utm[i - 1][1]
            s.append(s[-1] + math.sqrt(dx * dx + dy * dy))

        # Bekannte (Bogenlänge, km)-Paare aus den Elementen
        known = []
        for i, nr in enumerate(elem_seq):
            km = elems[nr].get("km")
            if km is not None:
                known.append((s[i], km))

        if not known:
            return None, None

        def _interp(pos):
            if len(known) == 1:
                return known[0][1]
            if pos <= known[0][0]:
                l0, k0 = known[0]
                l1, k1 = known[1]
                dl = l1 - l0
                return k0 if dl == 0 else k0 + (pos - l0) * (k1 - k0) / dl
            if pos >= known[-1][0]:
                l0, k0 = known[-2]
                l1, k1 = known[-1]
                dl = l1 - l0
                return k1 if dl == 0 else k1 + (pos - l1) * (k1 - k0) / dl
            for j in range(len(known) - 1):
                l0, k0 = known[j]
                l1, k1 = known[j + 1]
                if l0 <= pos <= l1:
                    dl = l1 - l0
                    return k0 if dl == 0 else k0 + (pos - l0) * (k1 - k0) / dl
            return None

        km_von = elems[elem_seq[0]].get("km")
        if km_von is None:
            km_von = _interp(0.0)

        km_bis = elems[elem_seq[-1]].get("km")
        if km_bis is None:
            km_bis = _interp(s[-1])

        return km_von, km_bis

    @staticmethod
    def _fill_node_km_from_edges(nodes_raw, edges_raw):
        """Füllt fehlende Knoten-km aus den km_von/km_bis der anliegenden Kanten."""
        name_to_km: dict = {}
        for edge in edges_raw:
            if edge["knotenname_von"] and edge["km_von"] is not None:
                name_to_km.setdefault(edge["knotenname_von"], edge["km_von"])
            if edge["knotenname_bis"] and edge["km_bis"] is not None:
                name_to_km.setdefault(edge["knotenname_bis"], edge["km_bis"])
        for kn in nodes_raw:
            if kn["km"] is None:
                kn["km"] = name_to_km.get(kn["knotenname"])

    def _traverse_edges(self, elems, vertex_inc, uf, bp_set, nodes_raw):
        """Baut Kanten durch Walk-Traversierung auf.

        Rückgabe: Liste von Kanten-Dicts mit UTM-Koordinaten.
        """
        # Knotenname-Lookup: vertex_id → knotenname (Weiche hat Vorrang)
        v_to_name: dict = {}
        for kn in nodes_raw:
            v = kn["vertex"]
            if v not in v_to_name or kn["typ"] == "Weiche":
                v_to_name[v] = kn["knotenname"]

        visited: set = set()  # besuchte elem_nr
        kanten = []
        kante_id = 1

        # Walk von jedem Breakpoint aus
        for bp_v in bp_set:
            for elem_nr, entry_side in vertex_inc[bp_v]:
                if elem_nr in visited:
                    continue
                result = self._walk(
                    elem_nr, entry_side, elems, vertex_inc, uf, bp_set, visited
                )
                if result is None:
                    continue
                elem_seq, pts_utm, exit_v = result
                km_von, km_bis = self._interpolate_km(elem_seq, pts_utm, elems)
                kanten.append(
                    {
                        "id": kante_id,
                        "elem_sequence": elem_seq,
                        "pts_utm": pts_utm,
                        "knotenname_von": v_to_name.get(bp_v),
                        "knotenname_bis": v_to_name.get(exit_v),
                        "km_von": km_von,
                        "km_bis": km_bis,
                        "strelemente_anz": len(elem_seq),
                        "strelement_von": elem_seq[0],
                        "strelement_bis": elem_seq[-1],
                    }
                )
                kante_id += 1

        # Reine Zyklen (unbesuchte Elemente → keine Breakpoints in Komponente)
        for nr in elems:
            if nr in visited:
                continue
            result = self._walk_cycle(nr, "g", elems, vertex_inc, uf, bp_set, visited)
            if result is None:
                continue
            elem_seq, pts_utm = result
            msg = (
                f"Geschlossene Schleife erkannt: {len(elem_seq)} Elemente "
                f"(erster: Nr={elem_seq[0]}). knotenname_von/bis=NULL."
            )
            self.warnings.append(msg)
            logger.warning(msg)
            km_von, km_bis = self._interpolate_km(elem_seq, pts_utm, elems)
            kanten.append(
                {
                    "id": kante_id,
                    "elem_sequence": elem_seq,
                    "pts_utm": pts_utm,
                    "knotenname_von": None,
                    "knotenname_bis": None,
                    "km_von": km_von,
                    "km_bis": km_bis,
                    "strelemente_anz": len(elem_seq),
                    "strelement_von": elem_seq[0],
                    "strelement_bis": elem_seq[-1],
                }
            )
            kante_id += 1

        return kanten

    def _walk(self, start_elem, entry_side, elems, vertex_inc, uf, bp_set, visited):
        """Walk von start_elem (Eintritt entry_side) bis zum nächsten Breakpoint.

        Rückgabe: (elem_seq, pts_utm, exit_v) oder None wenn bereits besucht.
        """
        elem_seq = []
        pts_utm = []

        # Eintrittskoordinate des ersten Elements als Startpunkt
        pts_utm.append(
            elems[start_elem]["g_coord"]
            if entry_side == "g"
            else elems[start_elem]["b_coord"]
        )

        current_elem = start_elem
        current_entry = entry_side
        exit_v = None

        while True:
            if current_elem in visited:
                break
            visited.add(current_elem)
            elem_seq.append(current_elem)

            exit_side = "b" if current_entry == "g" else "g"
            pts_utm.append(
                elems[current_elem]["g_coord"]
                if exit_side == "g"
                else elems[current_elem]["b_coord"]
            )
            exit_v = uf.find((current_elem, exit_side))

            if exit_v in bp_set:
                break

            # Grad-2-Fortsetzung: das andere Element am exit_v
            next_step = next(
                (
                    (nr, s)
                    for (nr, s) in vertex_inc[exit_v]
                    if nr != current_elem or s != exit_side
                ),
                None,
            )
            if next_step is None:
                break  # Topologisch offenes Ende (kein Breakpoint erkannt)
            current_elem, current_entry = next_step

        if not elem_seq:
            return None
        return elem_seq, pts_utm, exit_v

    def _walk_cycle(
        self, start_elem, entry_side, elems, vertex_inc, uf, bp_set, visited
    ):
        """Walk für reine Zyklen (alle Vertices Grad 2, kein Breakpoint in Komponente).

        Rückgabe: (elem_seq, pts_utm) oder None wenn bereits besucht.
        """
        if start_elem in visited:
            return None

        elem_seq = []
        pts_utm = []

        pts_utm.append(
            elems[start_elem]["g_coord"]
            if entry_side == "g"
            else elems[start_elem]["b_coord"]
        )

        current_elem = start_elem
        current_entry = entry_side

        while True:
            if current_elem in visited:
                break
            visited.add(current_elem)
            elem_seq.append(current_elem)

            exit_side = "b" if current_entry == "g" else "g"
            pts_utm.append(
                elems[current_elem]["g_coord"]
                if exit_side == "g"
                else elems[current_elem]["b_coord"]
            )
            exit_v = uf.find((current_elem, exit_side))

            if exit_v in bp_set:
                break
            next_step = next(
                (
                    (nr, s)
                    for (nr, s) in vertex_inc[exit_v]
                    if nr != current_elem or s != exit_side
                ),
                None,
            )
            if next_step is None:
                break
            current_elem, current_entry = next_step

        if not elem_seq:
            return None
        return elem_seq, pts_utm

    # Schritt 7 – Koordinatentransformation (Bulk)

    def _transform_coordinates(self, edges_raw, nodes_raw, source_epsg):
        """Transformiert alle Koordinaten von source_epsg nach self.target_epsg."""
        if source_epsg == self.target_epsg:
            transformer = None
        else:
            transformer = Transformer.from_crs(
                f"EPSG:{source_epsg}",
                f"EPSG:{self.target_epsg}",
                always_xy=True,
            )

        def _tf_point(xy):
            if transformer is None:
                return xy
            x, y = transformer.transform(xy[0], xy[1])
            return (x, y)

        def _tf_pts(pts):
            if transformer is None:
                return pts
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            txs, tys = transformer.transform(xs, ys)
            return list(zip(txs, tys))

        # In-Place: vermeidet vollständige Dict-Kopie pro Feature
        for k in edges_raw:
            k["pts"] = _tf_pts(k["pts_utm"])
        for kn in nodes_raw:
            kn["coord"] = _tf_point(kn["repr_coord_utm"])
        return edges_raw, nodes_raw

    # Schritt 8 – Layer-Ausgabe

    def _build_features(self, edges_tf, nodes_tf):
        """Wandelt interne Feature-Dicts in standardisierte Ausgabe-Dicts um.

        Rückgabe:
            (nodes_out, edges_out): Listen von Feature-Dicts mit
            'geometry' und 'attrs'.
        """
        edges_out = []
        for k in edges_tf:
            edges_out.append(
                {
                    "geometry": k["pts"],  # list of (x, y)
                    "attrs": {
                        "id": k["id"],
                        "knotenname_von": k["knotenname_von"],
                        "knotenname_bis": k["knotenname_bis"],
                        "km_von": k["km_von"],
                        "km_bis": k["km_bis"],
                        "strelemente_anz": k["strelemente_anz"],
                        "strelement_von": k["strelement_von"],
                        "strelement_bis": k["strelement_bis"],
                    },
                }
            )

        nodes_out = []
        for i, kn in enumerate(nodes_tf, 1):
            nodes_out.append(
                {
                    "geometry": kn["coord"],  # (x, y)
                    "attrs": {
                        "id": i,
                        "knotenname": kn["knotenname"],
                        "typ": kn["typ"],
                        "knotenbeschr": kn["knotenbeschr"],
                        "nr": kn["nr"],
                        "km": kn["km"],
                        "datei": kn["datei"],
                        "nachbarmodul": kn["nachbarmodul"],
                    },
                }
            )

        return nodes_out, edges_out
