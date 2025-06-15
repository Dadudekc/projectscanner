import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Optional

from .language_analyzer import LanguageAnalyzer

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file hashing, ignoring and caching."""

    def __init__(self, project_root: Path, cache: Dict, cache_lock: threading.Lock, additional_ignore_dirs: set):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_dirs = additional_ignore_dirs

    def hash_file(self, file_path: Path) -> str:
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:  # pragma: no cover - I/O errors
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        venv_patterns = {
            "venv", "env", ".env", ".venv", "virtualenv",
            "ENV", "VENV", ".ENV", ".VENV",
            "python-env", "python-venv", "py-env", "py-venv",
            "envs", "conda-env", ".conda-env",
            ".poetry/venv", ".poetry-venv",
        }
        default_exclude_dirs = {
            "__pycache__", "node_modules", "migrations", "build",
            "target", ".git", "coverage", "chrome_profile",
        } | venv_patterns

        file_abs = file_path.resolve()
        try:
            if file_abs == Path(__file__).resolve():
                return True
        except NameError:  # pragma: no cover
            pass

        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_abs.relative_to(ignore_path)
                return True
            except ValueError:
                continue

        try:
            if any(p.name == "pyvenv.cfg" for p in file_abs.parents):
                return True
            for parent in file_abs.parents:
                if (parent / "bin" / "activate").exists() or (parent / "Scripts" / "activate.bat").exists():
                    return True
        except (OSError, PermissionError):
            pass

        if any(excluded in file_path.parts for excluded in default_exclude_dirs):
            return True
        path_str = str(file_abs).lower()
        if any(f"/{pattern}/" in path_str.replace("\\", "/") for pattern in venv_patterns):
            return True
        return False

    def process_file(self, file_path: Path, language_analyzer: LanguageAnalyzer) -> Optional[tuple]:
        file_hash_val = self.hash_file(file_path)
        relative_path = str(file_path.relative_to(self.project_root))
        with self.cache_lock:
            if relative_path in self.cache and self.cache[relative_path].get("hash") == file_hash_val:
                return None
        try:
            with file_path.open("r", encoding="utf-8") as f:
                source_code = f.read()
            analysis_result = language_analyzer.analyze_file(file_path, source_code)
            with self.cache_lock:
                self.cache[relative_path] = {"hash": file_hash_val}
            return (relative_path, analysis_result)
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Error analyzing %s: %s", file_path, exc)
            return None
