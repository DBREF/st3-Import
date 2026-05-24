# st3-Import: core.py
# Copyright (c) 2026 Fabian Schöpflin. Alle Rechte vorbehalten.

# --- Standardbibliotheken ---
import json
import logging
import sys
from pathlib import Path

# --- Version ---
VERSION = "1.0.0"

# --- QGIS-Erkennung ---
IN_QGIS = "qgis.core" in sys.modules

# --- Logging-System ---
logger = logging.getLogger("st3_converter")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Nicht an Root-Logger weitergeben


class _QgsMessageLogHandler(logging.Handler):
    """Leitet Logging-Nachrichten an QgsMessageLog weiter (nur in QGIS)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from qgis.core import Qgis, QgsMessageLog

            level_map = {
                logging.WARNING: Qgis.MessageLevel.Warning,
                logging.ERROR: Qgis.MessageLevel.Critical,
                logging.CRITICAL: Qgis.MessageLevel.Critical,
            }
            qgis_level = level_map.get(record.levelno, Qgis.MessageLevel.Info)
            QgsMessageLog.logMessage(
                self.format(record), "st3-Import", level=qgis_level
            )
        except Exception:  # noqa: BLE001
            pass


def _setup_logging() -> None:
    """Konfiguriert das Logging für CLI (stdout) und QGIS (QgsMessageLog)."""
    if logger.handlers:
        return

    formatter = logging.Formatter("%(message)s")

    _stdout = sys.stdout
    if hasattr(_stdout, "reconfigure"):
        try:
            _stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    stream_handler = logging.StreamHandler(_stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)

    if IN_QGIS:
        qgis_handler = _QgsMessageLogHandler()
        qgis_handler.setFormatter(formatter)
        qgis_handler.setLevel(logging.DEBUG)
        logger.addHandler(qgis_handler)


_setup_logging()


def print(*args, **kwargs) -> None:  # noqa: A001
    """Modul-weiter print()-Wrapper: routet alle Ausgaben durch das Logging-System.

    In CLI:  identisches Verhalten wie builtin print() via StreamHandler → stdout.
    In QGIS: zusätzliche Ausgabe in QgsMessageLog mit korrektem Level.
    """
    file = kwargs.get("file", None)
    msg = " ".join(str(a) for a in args) if args else ""
    if file is sys.stderr:
        logger.error(msg)
        return
    if "[WARNUNG]" in msg:
        logger.warning(msg.replace("[WARNUNG] ", "", 1))
    elif "[FEHLER]" in msg:
        logger.error(msg.replace("[FEHLER] ", "", 1))
    elif "[DEBUG]" in msg:
        logger.debug(msg.replace("  [DEBUG] ", "", 1).replace("[DEBUG] ", "", 1))
    else:
        logger.info(msg)


class Config:
    """Verwaltet die Einstellungen des st3-Konverters."""

    def __init__(self, config_file: Path = None):
        """Initialisiert die Konfiguration.

        Args:
            config_file: Pfad zur JSON-Konfigurationsdatei.
                        Bei None wird die Standard-Datei verwendet.
                        Bei False wird keine JSON-Datei geladen (nur Defaults).
        """
        self.settings = self._load_default_settings()

        if config_file is False:
            self.config_file = None
        else:
            if config_file is None:
                config_file = (
                    Path(__file__).parent.parent
                    / "config"
                    / "st3_converter_config.json"
                )
            self.config_file = config_file
            self.load()

    def _load_default_settings(self) -> dict:
        """Lädt die Standard-Einstellungen."""
        return {
            "auto_detect_crs": True,
            "fallback_epsg": 32632,
            "target_epsg": 31467,
            "create_log_file": True,
            "open_log_file": False,
        }

    def load(self):
        """Lädt die Einstellungen aus der JSON-Datei."""
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Laden der Config: {e}")

    def save(self):
        """Speichert die Einstellungen in die JSON-Datei."""
        if self.config_file is None:
            return
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"[OK] Einstellungen gespeichert: {self.config_file}")
        except Exception as e:
            print(f"[FEHLER] Fehler beim Speichern der Config: {e}")

    def get(self, key: str, default=None):
        """Gibt einen Einstellungswert zurück."""
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """Setzt einen Einstellungswert."""
        self.settings[key] = value
