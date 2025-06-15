import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Handles merging new analysis with old reports."""

    def __init__(self, project_root: Path, analysis: Dict[str, Dict]):
        self.project_root = project_root
        self.analysis = analysis

    # --- helper methods ---
    def load_existing_report(self, report_path: Path) -> Dict:
        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:  # pragma: no cover
                pass
        return {}

    def save_report(self):
        report_path = self.project_root / "project_analysis.json"
        existing_report = self.load_existing_report(report_path)
        merged = {**existing_report, **self.analysis}
        try:
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(merged, f, indent=4)
            logger.info("✅ Merged analysis saved to: %s", report_path)
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Error writing analysis report: %s", exc)

    def generate_init_files(self, overwrite: bool = True):
        for file, result in self.analysis.items():
            if result.get("language") != ".py":
                continue
            path = self.project_root / file
            if path.name == "__init__.py":
                continue
            pkg_dir = path.parent
            init_file = pkg_dir / "__init__.py"
            if init_file.exists() and not overwrite:
                continue
            try:
                init_file.touch(exist_ok=True)
            except Exception as exc:  # pragma: no cover
                logger.error("❌ Could not create %s: %s", init_file, exc)

    # --- ChatGPT context ---
    def load_existing_chatgpt_context(self, context_path: Path) -> Dict:
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:  # pragma: no cover
                pass
        return {}

    def export_chatgpt_context(self, template_path: str = None, output_path: str = None):
        context_path = self.project_root / (output_path or "chatgpt_project_context.json")
        if template_path is None:
            existing_context = self.load_existing_chatgpt_context(context_path)
            payload = {
                "project_root": str(self.project_root),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis,
            }
            merged = {**existing_context, **payload}
            try:
                with context_path.open("w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=4)
                logger.info("✅ Merged ChatGPT context saved to: %s", context_path)
            except Exception as exc:  # pragma: no cover
                logger.error("❌ Error writing ChatGPT context: %s", exc)
            return

        try:
            from jinja2 import Template
            with open(template_path, "r", encoding="utf-8") as tf:
                template_content = tf.read()
            t = Template(template_content)
            context_dict = {
                "project_root": str(self.project_root),
                "analysis": self.analysis,
                "num_files_analyzed": len(self.analysis),
            }
            rendered = t.render(context=context_dict)
            with context_path.open("w", encoding="utf-8") as outf:
                outf.write(rendered)
            logger.info("✅ Rendered ChatGPT context to: %s", output_path)
        except ImportError:
            logger.error("⚠️ Jinja2 not installed. Run `pip install jinja2` and re-try.")
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Error rendering Jinja template: %s", exc)
