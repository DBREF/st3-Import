# st3-Import: cli.py
# Copyright (c) 2026 Fabian Schöpflin. Alle Rechte vorbehalten.

# --- Standardbibliotheken ---
import argparse
import sys
import traceback
from pathlib import Path

# Eigenes Verzeichnis (core/) aus sys.path entfernen, damit 'core' nicht als
# einzelnes Modul aufgelöst wird, sondern als Paket im Elternverzeichnis.
_this_dir = str(Path(__file__).resolve().parent)
_parent = str(Path(__file__).resolve().parent.parent)
sys.path = [p for p in sys.path if p != _this_dir]
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# --- Drittanbieter-Bibliotheken ---
import geopandas as gpd  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

# --- Module ---
from core.core import VERSION, Config, print  # noqa: E402


# EPSG-Auswahl
def select_epsg() -> int:
    """Auswahl des Ziel-EPSG-Codes."""
    print("\nZiel-Koordinatenbezugssystem (KBS) auswählen:")
    print()
    print("DHDN / Gauss-Krüger:")
    print("  1. EPSG:31467 - DHDN / 3-degree GK Zone 3 (9°E) [Standard]")
    print("  2. EPSG:31466 - DHDN / 3-degree GK Zone 2 (6°E)")
    print("  3. EPSG:31468 - DHDN / 3-degree GK Zone 4 (12°E)")
    print("  4. EPSG:31469 - DHDN / 3-degree GK Zone 5 (15°E)")
    print()
    print("DB_REF / Gauss-Krüger:")
    print("  5. EPSG:5682 - DB_REF / 3-degree GK Zone 2 (6°E)")
    print("  6. EPSG:5683 - DB_REF / 3-degree GK Zone 3 (9°E)")
    print("  7. EPSG:5684 - DB_REF / 3-degree GK Zone 4 (12°E)")
    print("  8. EPSG:5685 - DB_REF / 3-degree GK Zone 5 (15°E)")
    print()
    print("ETRS89 / UTM:")
    print("  9. EPSG:25832 - ETRS89 / UTM Zone 32N (6°E-12°E)")
    print(" 10. EPSG:25833 - ETRS89 / UTM Zone 33N (12°E-18°E)")
    print(" 11. EPSG:25831 - ETRS89 / UTM Zone 31N (0°E-6°E)")
    print()
    print("WGS84 / UTM:")
    print(" 12. EPSG:32632 - WGS84 / UTM Zone 32N (6°E-12°E)")
    print(" 13. EPSG:32633 - WGS84 / UTM Zone 33N (12°E-18°E)")
    print(" 14. EPSG:32631 - WGS84 / UTM Zone 31N (0°E-6°E)")
    print()
    print(" 15. Benutzerdefiniert (EPSG-Code manuell eingeben)")

    epsg_mapping = {
        "1": 31467,
        "2": 31466,
        "3": 31468,
        "4": 31469,
        "5": 5682,
        "6": 5683,
        "7": 5684,
        "8": 5685,
        "9": 25832,
        "10": 25833,
        "11": 25831,
        "12": 32632,
        "13": 32633,
        "14": 32631,
    }

    while True:
        choice = input("\nAuswahl [1]: ").strip() or "1"

        if choice in epsg_mapping:
            epsg_code = epsg_mapping[choice]
            print(f"  ✓ EPSG:{epsg_code} ausgewählt")
            return epsg_code
        elif choice == "15":
            while True:
                custom = input("  Bitte EPSG-Code eingeben (z.B. 31467): ").strip()
                if custom.isdigit():
                    epsg_code = int(custom)
                    print(f"  ✓ EPSG:{epsg_code} ausgewählt")
                    return epsg_code
                print("  [FEHLER] Ungültiger EPSG-Code")
        else:
            print("  [FEHLER] Ungültige Auswahl")


# Einstellungsmenü


def settings_menu(config: Config) -> Config:
    """Einstellungsmenü für die Konvertierungs-Konfiguration."""
    while True:
        print("\n" + "=" * 70)
        print("Einstellungen")
        print("=" * 70)

        print("\n1. Automatische CRS-Erkennung")
        auto_detect = config.get("auto_detect_crs", True)
        print(f"   Aktuell: {'Ja' if auto_detect else 'Nein'}")
        print("   (CRS wird automatisch aus der st3-Datei ausgelesen)")

        print("\n2. Rückfall-KBS")
        print(f"   Aktuell: EPSG:{config.get('fallback_epsg', 32632)}")
        print("   (wird verwendet, wenn die automatische CRS-Erkennung fehlschlägt)")

        print("\n3. Ziel-Koordinatenbezugssystem (KBS)")
        print(f"   Aktuell: EPSG:{config.get('target_epsg', 31467)}")
        print("   (KBS der erstellten Ausgabe-Layer)")

        print("\n4. Namen von Weichenknoten normalisieren")
        print(
            f"   Aktuell: {'Ja' if config.get('normalize_switch_names', True) else 'Nein'}"
        )
        print(
            "   (Entfernt W/EW/DKW-Präfixe und ESTW-Bereichskennziffern aus Signalnamen)"
        )

        print("\n5. Protokoll-Datei erstellen")
        print(f"   Aktuell: {'Ja' if config.get('create_log_file', True) else 'Nein'}")

        print("\n6. Protokoll nach Abschluss öffnen")
        open_log = config.get("open_log_file", False)
        print(f"   Aktuell: {'Ja' if open_log else 'Nein'}")

        print("\n7. Hüllkurve importieren")
        print(f"   Aktuell: {'Ja' if config.get('import_envelope', True) else 'Nein'}")
        print("   (Liest das <Huellkurve>-Polygon als Layer in das GeoPackage)")

        print("\n8. Einstellungen speichern")
        print("\n0. Zurück zum Hauptmenü")

        choice = input("\nAuswahl [0]: ").strip()

        if choice == "1":
            new_value = not config.get("auto_detect_crs", True)
            config.set("auto_detect_crs", new_value)
            print(f"  ✓ Automatische CRS-Erkennung: {'Ja' if new_value else 'Nein'}")
        elif choice == "2":
            epsg_code = select_epsg()
            config.set("fallback_epsg", epsg_code)
        elif choice == "3":
            epsg_code = select_epsg()
            config.set("target_epsg", epsg_code)
        elif choice == "4":
            new_value = not config.get("normalize_switch_names", True)
            config.set("normalize_switch_names", new_value)
            print(
                f"  ✓ Namen von Weichenknoten normalisieren: {'Ja' if new_value else 'Nein'}"
            )
        elif choice == "5":
            new_value = not config.get("create_log_file", True)
            config.set("create_log_file", new_value)
            print(f"  ✓ Protokoll-Datei erstellen: {'Ja' if new_value else 'Nein'}")
        elif choice == "6":
            new_value = not config.get("open_log_file", False)
            config.set("open_log_file", new_value)
            print(
                f"  ✓ Protokoll nach Abschluss öffnen: {'Ja' if new_value else 'Nein'}"
            )
        elif choice == "7":
            new_value = not config.get("import_envelope", True)
            config.set("import_envelope", new_value)
            print(f"  ✓ Hüllkurve importieren: {'Ja' if new_value else 'Nein'}")
        elif choice == "8":
            config.save()
        elif choice == "0" or not choice:
            break
        else:
            print("  [FEHLER] Ungültige Auswahl")

    return config


# GeoPackage-Hilfsfunktionen
def find_st3_files(directory) -> list:
    """Sucht nach .st3-Dateien im angegebenen Verzeichnis.

    Returns:
        Sortierte Liste von Path-Objekten zu gefundenen .st3-Dateien.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []
    return sorted(dir_path.glob("*.st3"))


def _write_gpkg(
    nodes_features: list,
    edges_features: list,
    output_path: str,
    target_epsg: int,
    envelope_features: list | None = None,
) -> None:
    """Schreibt Knoten- und Kanten-Features (sowie optional Hüllkurven) in ein GeoPackage.

    Args:
        nodes_features:    Liste von Feature-Dicts (geometry: Punkt-Tupel, attrs: dict)
        edges_features:    Liste von Feature-Dicts (geometry: Koordinatenliste, attrs: dict)
        output_path:       Pfad zur Ausgabe-GeoPackage-Datei
        target_epsg:       EPSG-Code des Ziel-KBS
        envelope_features: Optional — Liste von Hüllkurven-Feature-Dicts
    """
    crs = f"EPSG:{target_epsg}"

    # Knoten-Layer
    node_records = []
    for feat in nodes_features:
        record = dict(feat["attrs"])
        record["geometry"] = Point(feat["geometry"])
        node_records.append(record)

    # Kanten-Layer
    edge_records = []
    for feat in edges_features:
        record = dict(feat["attrs"])
        record["geometry"] = LineString(feat["geometry"])
        edge_records.append(record)

    gdf_nodes = gpd.GeoDataFrame(node_records, crs=crs)
    gdf_edges = gpd.GeoDataFrame(edge_records, crs=crs)

    gdf_nodes.to_file(output_path, layer="Gleisknoten", driver="GPKG")
    gdf_edges.to_file(output_path, layer="Gleiskante", driver="GPKG", mode="a")

    if envelope_features:
        env_records = []
        for feat in envelope_features:
            record = dict(feat["attrs"])
            pts = list(feat["geometry"])
            if pts and pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            record["geometry"] = Polygon(pts)
            env_records.append(record)
        gdf_env = gpd.GeoDataFrame(env_records, crs=crs)
        gdf_env.to_file(output_path, layer="Hüllkurve", driver="GPKG", mode="a")


# Hilfsfunktionen für interactive_mode
def _ask_output_and_confirm(input_file: Path, config: dict) -> tuple | None:
    """Fragt nach Ausgabedateiname, zeigt Zusammenfassung und bestätigt.

    Returns:
        (input_file, output_file, config) oder None bei Abbruch.
    """
    print("\nName der Ausgabedatei (GeoPackage):")
    default_name = input_file.stem + ".gpkg"
    output_name = input(f"   Dateiname [{default_name}]: ").strip() or default_name
    if not output_name.endswith(".gpkg"):
        output_name += ".gpkg"

    output_file = str(input_file.parent / output_name)
    print(f"\n✓ Ausgabedatei: {output_file}")

    print("\n" + "=" * 70)
    print("Zusammenfassung:")
    print(f"  Eingabe:      {input_file}")
    print(f"  Ausgabe:      {output_file}")
    print(f"  Ziel-KBS:     EPSG:{config.get('target_epsg', 31467)}")
    print(f"  Auto-CRS:     {'Ja' if config.get('auto_detect_crs', True) else 'Nein'}")
    print(f"  Rückfall-KBS: EPSG:{config.get('fallback_epsg', 32632)}")
    print(
        f"  WK normalisieren: {'Ja' if config.get('normalize_switch_names', True) else 'Nein'}"
    )
    print(f"  Hüllkurve:    {'Ja' if config.get('import_envelope', True) else 'Nein'}")
    print("=" * 70)

    confirm = input("\nKonvertierung starten? (j/n) [j]: ").strip().lower()
    if not confirm or confirm == "j":
        return input_file, output_file, config
    return None


# Interaktiver Modus
def interactive_mode() -> tuple | None:
    """Interaktiver Modus für die st3-Konvertierung.

    Rückgabe:
        (input_file, output_file, config) oder None bei Abbruch.
    """
    print("=" * 74)
    print(f"st3-Import - Version {VERSION}")
    print("Importiert Zusi-3-Streckendateien (.st3) als Knoten-Kanten-Modell")
    print("=" * 74)
    print()

    config = Config()

    print("Hauptmenü:")
    print("  1. Konvertierung starten")
    print("  2. Einstellungen")
    print("  3. Beenden")

    while True:
        choice = input("\nAuswahl [1]: ").strip() or "1"

        if choice == "1":
            break
        elif choice == "2":
            config = settings_menu(config)
            print("\n" + "=" * 70)
            print("Hauptmenü:")
            print("  1. Konvertierung starten")
            print("  2. Einstellungen")
            print("  3. Beenden")
        elif choice == "3":
            print("\nAuf Wiedersehen!")
            sys.exit(0)
        else:
            print("  [FEHLER] Ungültige Auswahl")

    print("\n" + "-" * 70)
    print(f"Aktuelle Einstellungen: Ziel-KBS = EPSG:{config.get('target_epsg', 31467)}")
    print("-" * 70)
    print()

    current_dir = Path.cwd()
    print(f"Suchverzeichnis: {current_dir}")
    print()

    # 1. Versuch: .st3-Dateien im aktuellen Verzeichnis suchen
    st3_files = find_st3_files(current_dir)

    if st3_files:
        print(f"✓ {len(st3_files)} .st3-Datei(en) gefunden:")
        for i, f in enumerate(st3_files, 1):
            print(f"  {i}. {f.name}")

        if len(st3_files) == 1:
            use_found = (
                input(f"\n'{st3_files[0].name}' verwenden? (j/n) [j]: ").strip().lower()
            )
            if not use_found or use_found == "j":
                return _ask_output_and_confirm(st3_files[0], config)
        else:
            selection = input(
                "\nDateinummer auswählen (oder Enter zum Überspringen): "
            ).strip()
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(st3_files):
                    return _ask_output_and_confirm(st3_files[idx], config)
                print("  [FEHLER] Ungültige Auswahl")

    # 2. Versuch: Ordner abfragen
    print("\n⚠ Keine .st3-Dateien im aktuellen Verzeichnis gefunden.")
    folder_input = input(
        "\nOrdner mit .st3-Dateien angeben (oder Enter zum Überspringen): "
    ).strip()

    if folder_input:
        folder_path = Path(folder_input)
        if folder_path.is_dir():
            st3_files = find_st3_files(folder_path)
            if st3_files:
                print(f"\n✓ {len(st3_files)} .st3-Datei(en) gefunden:")
                for i, f in enumerate(st3_files, 1):
                    print(f"  {i}. {f.name}")

                if len(st3_files) == 1:
                    use_found = (
                        input(f"\n'{st3_files[0].name}' verwenden? (j/n) [j]: ")
                        .strip()
                        .lower()
                    )
                    if not use_found or use_found == "j":
                        return _ask_output_and_confirm(st3_files[0], config)
                else:
                    selection = input("\nDateinummer auswählen: ").strip()
                    if selection.isdigit():
                        idx = int(selection) - 1
                        if 0 <= idx < len(st3_files):
                            return _ask_output_and_confirm(st3_files[idx], config)
                        print("  [FEHLER] Ungültige Auswahl")
            else:
                print(f"\n⚠ Keine .st3-Dateien gefunden in: {folder_input}")
        else:
            print(f"\n⚠ Ordner nicht gefunden: {folder_input}")

    # 3. Versuch: Datei direkt angeben
    print("\n" + "-" * 70)
    print("Bitte Datei direkt angeben:")
    print("-" * 70)

    while True:
        user_input = input("\nPfad zur .st3-Datei (oder Enter zum Abbrechen): ").strip()
        if not user_input:
            return None
        file_path = Path(user_input)
        if file_path.exists() and file_path.suffix.lower() == ".st3":
            return _ask_output_and_confirm(file_path, config)
        print(f"  [FEHLER] Datei nicht gefunden oder keine .st3-Datei: {user_input}")
        if input("  Erneut versuchen? (j/n): ").strip().lower() != "j":
            return None


# Einstiegspunkt


def main():
    """Hauptfunktion für das CLI."""
    # Lazy imports um zirkuläre Importe zu vermeiden
    from convert.convert_envelope import convert_envelope  # noqa: PLC0415
    from st3_converter import st3Converter  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description=(
            "Importiert Zusi-3-Streckendateien (.st3) als Knoten-Kanten-Modell "
            "in ein GeoPackage."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispielaufrufe:
  # Interaktiver Modus (ohne Parameter):
  %(prog)s
  # CLI-Modus (mit Parametern):
  %(prog)s -i Streckenmodul.st3 -o Ausgabe.gpkg
  %(prog)s -i Streckenmodul.st3 -o Ausgabe.gpkg -e 25832
  %(prog)s -i Streckenmodul.st3 -o Ausgabe.gpkg --no-auto-detect --fallback-epsg 31467
        """,
    )
    parser.add_argument(
        "-i", "--input", metavar="DATEI", help="Pfad zur .st3-Eingabedatei"
    )
    parser.add_argument(
        "-o", "--output", metavar="DATEI", help="Pfad zur Ausgabe-GeoPackage-Datei"
    )
    parser.add_argument(
        "-e",
        "--epsg",
        type=int,
        default=31467,
        metavar="CODE",
        help="EPSG-Code des Ziel-KBS (Standard: 31467)",
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Automatische CRS-Erkennung deaktivieren",
    )
    parser.add_argument(
        "--fallback-epsg",
        type=int,
        default=None,
        metavar="CODE",
        help="Rückfall-EPSG-Code wenn Auto-Erkennung fehlschlägt (Standard: 32632)",
    )
    parser.add_argument(
        "--no-normalize-switches",
        action="store_true",
        help="Normalisieren von Weichenknoten deaktivieren (Signalnamen unverändert übernehmen)",
    )
    parser.add_argument(
        "--import-envelope",
        action="store_true",
        default=None,
        help="Hüllkurven-Polygon aus der st3-Datei importieren und als Layer speichern",
    )
    parser.add_argument(
        "--no-import-envelope",
        action="store_true",
        help="Hüllkurven-Import deaktivieren",
    )
    parser.add_argument(
        "--open-log",
        action="store_true",
        help="Protokoll nach Abschluss automatisch öffnen",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {VERSION}"
    )

    args = parser.parse_args()

    if args.input or args.output:
        # CLI-Modus
        if not args.input or not args.output:
            print(
                "[FEHLER] Wenn Parameter angegeben werden, müssen sowohl "
                "-i/--input als auch -o/--output gesetzt sein.",
                file=sys.stderr,
            )
            sys.exit(1)

        input_file = Path(args.input)
        if not input_file.exists():
            print(
                f"[FEHLER] Eingabedatei nicht gefunden: {args.input}",
                file=sys.stderr,
            )
            sys.exit(1)

        _cfg = Config()
        import_envelope = (
            False
            if args.no_import_envelope
            else True
            if args.import_envelope
            else _cfg.get("import_envelope", True)
        )
        config = {
            "auto_detect_crs": not args.no_auto_detect,
            "fallback_epsg": args.fallback_epsg
            if args.fallback_epsg is not None
            else _cfg.get("fallback_epsg", 32632),
            "target_epsg": args.epsg,
            "normalize_switch_names": not args.no_normalize_switches,
            "import_envelope": import_envelope,
            "open_log_file": args.open_log,
        }

        try:
            converter = st3Converter(
                str(input_file),
                target_epsg=config["target_epsg"],
                auto_detect_crs=config["auto_detect_crs"],
                normalize_switch_names=config.get("normalize_switch_names", True),
            )
            nodes_features, edges_features = converter.convert()

            envelope_features = None
            if config.get("import_envelope", True):
                envelope_features = convert_envelope(
                    str(input_file),
                    target_epsg=config["target_epsg"],
                    auto_detect_crs=config["auto_detect_crs"],
                    fallback_epsg=config.get("fallback_epsg", 32632),
                )

            _write_gpkg(
                nodes_features,
                edges_features,
                args.output,
                config["target_epsg"],
                envelope_features=envelope_features or None,
            )
            for w in converter.warnings:
                print(f"[WARNUNG] {w}")
            env_info = (
                f", {len(envelope_features)} Hüllkurve(n)" if envelope_features else ""
            )
            print(
                f"\n[OK] {len(nodes_features)} Knoten, {len(edges_features)} Kanten"
                f"{env_info} → {args.output}"
            )
        except KeyboardInterrupt:
            print("\n[INFO] Konvertierung abgebrochen.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n[FEHLER] Konvertierung fehlgeschlagen: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

    else:
        # Interaktiver Modus
        while True:
            result = interactive_mode()
            if result is None:
                print("\nZurück zum Hauptmenü...")
                continue

            input_file, output_file, config = result

            try:
                converter = st3Converter(
                    str(input_file),
                    target_epsg=config["target_epsg"],
                    auto_detect_crs=config.get("auto_detect_crs", True),
                    normalize_switch_names=config.get("normalize_switch_names", True),
                )
                nodes_features, edges_features = converter.convert()

                envelope_features = None
                if config.get("import_envelope", True):
                    envelope_features = convert_envelope(
                        str(input_file),
                        target_epsg=config["target_epsg"],
                        auto_detect_crs=config.get("auto_detect_crs", True),
                        fallback_epsg=config.get("fallback_epsg", 32632),
                    )

                _write_gpkg(
                    nodes_features,
                    edges_features,
                    output_file,
                    config["target_epsg"],
                    envelope_features=envelope_features or None,
                )
                for w in converter.warnings:
                    print(f"[WARNUNG] {w}")
                env_info = (
                    f", {len(envelope_features)} Hüllkurve(n)"
                    if envelope_features
                    else ""
                )
                print("\n" + "=" * 70)
                print("Konvertierung abgeschlossen!")
                print(
                    f"  {len(nodes_features)} Knoten, {len(edges_features)} Kanten"
                    f"{env_info} → {output_file}"
                )
                print("=" * 70)
                input("\nDrücken Sie Enter, um zum Hauptmenü zurückzukehren...")
            except KeyboardInterrupt:
                print("\n\n[INFO] Konvertierung abgebrochen.")
                input("\nDrücken Sie Enter, um zum Hauptmenü zurückzukehren...")
            except Exception as e:
                print(f"\n[FEHLER] Konvertierung fehlgeschlagen: {e}", file=sys.stderr)
                traceback.print_exc()
                input("\nDrücken Sie Enter, um zum Hauptmenü zurückzukehren...")


if __name__ == "__main__":
    main()
