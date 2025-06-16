"""ProjectScanner package."""
from .scanner import ProjectScanner
from .language_analyzer import LanguageAnalyzer
from .file_processor import FileProcessor
from .report_generator import ReportGenerator
from .bots import BotWorker, MultibotManager

try:
    from .gui import AnalysisViewer
except Exception:  # pragma: no cover - optional dependency
    AnalysisViewer = None

__all__ = [
    "ProjectScanner",
    "LanguageAnalyzer",
    "FileProcessor",
    "ReportGenerator",
    "BotWorker",
    "MultibotManager",
    "AnalysisViewer",
]
