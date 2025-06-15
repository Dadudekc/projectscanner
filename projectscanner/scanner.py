import json
import logging
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Union

from .bots import MultibotManager
from .file_processor import FileProcessor
from .language_analyzer import LanguageAnalyzer
from .report_generator import ReportGenerator

CACHE_FILE = "dependency_cache.json"
logger = logging.getLogger(__name__)

class ProjectScanner:
    """Main orchestrator for analyzing projects."""

    def __init__(self, project_root: Union[str, Path] = "."):
        self.project_root = Path(project_root).resolve()
        self.analysis: Dict[str, Dict] = {}
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.additional_ignore_dirs = set()
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root,
            self.cache,
            self.cache_lock,
            self.additional_ignore_dirs,
        )
        self.report_generator = ReportGenerator(self.project_root, self.analysis)

    # --- Cache helpers ---
    def load_cache(self) -> Dict:
        cache_path = Path(CACHE_FILE)
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_cache(self):
        cache_path = Path(CACHE_FILE)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    # --- Main scanning ---
    def scan_project(self, progress_callback: Optional[callable] = None):
        logger.info("🔍 Scanning project: %s ...", self.project_root)
        file_extensions = {".py", ".rs", ".js", ".ts"}
        valid_files = []
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            if self.file_processor.should_exclude(root_path):
                continue
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() in file_extensions and not self.file_processor.should_exclude(file_path):
                    valid_files.append(file_path)

        total_files = len(valid_files)
        logger.info("📝 Found %s valid files for analysis.", total_files)

        previous_files = set(self.cache.keys())
        current_files = {str(f.relative_to(self.project_root)) for f in valid_files}
        moved_files = {}
        missing_files = previous_files - current_files

        for old_path in previous_files:
            old_hash = self.cache.get(old_path, {}).get("hash")
            if not old_hash:
                continue
            for new_path in current_files:
                new_file = self.project_root / new_path
                if self.file_processor.hash_file(new_file) == old_hash:
                    moved_files[old_path] = new_path
                    break

        for missing_file in missing_files:
            if missing_file not in moved_files:
                with self.cache_lock:
                    self.cache.pop(missing_file, None)

        for old_path, new_path in moved_files.items():
            with self.cache_lock:
                self.cache[new_path] = self.cache.pop(old_path)

        logger.info("⏱️  Processing files asynchronously...")
        num_workers = os.cpu_count() or 4
        manager = MultibotManager(
            scanner=self,
            num_workers=num_workers,
            status_callback=lambda fp, res: logger.info("Processed: %s", fp),
        )
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()

        processed_count = 0
        for result in manager.results_list:
            processed_count += 1
            if progress_callback:
                percent = int((processed_count / total_files) * 100)
                progress_callback(percent)
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        self.report_generator.save_report()
        self.save_cache()
        logger.info(
            "✅ Scan complete. Results merged into %s",
            self.project_root / "project_analysis.json",
        )

    def _process_file(self, file_path: Path):
        return self.file_processor.process_file(file_path, self.language_analyzer)

    # --- convenience methods ---
    def generate_init_files(self, overwrite: bool = True):
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None):
        self.report_generator.export_chatgpt_context(template_path, output_path)

    def categorize_agents(self):
        for file_path, result in self.analysis.items():
            if file_path.endswith(".py"):
                for class_name, class_data in result.get("classes", {}).items():
                    class_data["maturity"] = self._maturity_level(class_name, class_data)
                    class_data["agent_type"] = self._agent_type(class_name, class_data)

    def _maturity_level(self, class_name: str, class_data: Dict[str, any]) -> str:
        score = 0
        if class_data.get("docstring"):
            score += 1
        if len(class_data.get("methods", [])) > 3:
            score += 1
        if any(base for base in class_data.get("base_classes", []) if base not in ("object", None)):
            score += 1
        if class_name and class_name[0].isupper():
            score += 1
        levels = ["Kiddie Script", "Prototype", "Core Asset", "Core Asset"]
        return levels[min(score, 3)]

    def _agent_type(self, class_name: str, class_data: Dict[str, any]) -> str:
        doc = (class_data.get("docstring") or "").lower()
        methods = class_data.get("methods", [])
        if "run" in methods:
            return "ActionAgent"
        if "transform" in doc or "parse" in doc:
            return "DataAgent"
        if any(m in methods for m in ["predict", "analyze"]):
            return "SignalAgent"
        return "Utility"
