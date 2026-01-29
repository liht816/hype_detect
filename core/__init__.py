"""
core package exports (единая точка импорта)
"""

from core.hype_calculator import HypeCalculator, HypeAnalysis

# Red Flags (если файл существует)
try:
    from core.red_flags_detector import RedFlagsDetector, RedFlagResult
except Exception:
    RedFlagsDetector = None  # type: ignore
    RedFlagResult = None     # type: ignore

# Alert Manager (если файл существует)
try:
    from core.alert_manager import AlertManager, AlertType
except Exception:
    AlertManager = None  # type: ignore
    AlertType = None     # type: ignore

# Prediction (если файл существует)
try:
    from core.prediction import PredictionEngine
except Exception:
    PredictionEngine = None  # type: ignore


__all__ = [
    "HypeCalculator",
    "HypeAnalysis",
    "RedFlagsDetector",
    "RedFlagResult",
    "AlertManager",
    "AlertType",
    "PredictionEngine",
]