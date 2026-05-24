# st3_converter: core.py
# Copyright (c) 2026 Fabian Schöpflin. Alle Rechte vorbehalten.

# --- Standardbibliotheken ---
import logging
import sys

# --- Version ---
VERSION = "1.0.0"

# --- QGIS-Erkennung ---
IN_QGIS = "qgis.core" in sys.modules

# --- Logging-System ---
logger = logging.getLogger("st3_converter")
logger.setLevel(logging.DEBUG)
logger.propagate = False


class _QgsMessageLogHandler(logging.Handler):
    """Leitet Logging-Nachrichten an QgsMessageLog weiter."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from qgis.core import Qgis, QgsMessageLog

            level_map = {
                logging.DEBUG: Qgis.MessageLevel.Info,
                logging.INFO: Qgis.MessageLevel.Info,
                logging.WARNING: Qgis.MessageLevel.Warning,
                logging.ERROR: Qgis.MessageLevel.Critical,
                logging.CRITICAL: Qgis.MessageLevel.Critical,
            }
            level = level_map.get(record.levelno, Qgis.MessageLevel.Info)
            QgsMessageLog.logMessage(self.format(record), "st3_converter", level)
        except Exception:
            pass


_formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")

if IN_QGIS:
    _qgs_handler = _QgsMessageLogHandler()
    _qgs_handler.setFormatter(_formatter)
    logger.addHandler(_qgs_handler)
else:
    _stream_handler = logging.StreamHandler(sys.stdout)
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_stream_handler)
