import argparse
import json
import logging
from pathlib import Path

from .scanner import ProjectScanner

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(
        description="Project scanner with agent categorization and incremental caching."
    )
    parser.add_argument("--project-root", default=".", help="Root directory to scan.")
    parser.add_argument("--ignore", nargs="*", default=[], help="Additional directories to ignore.")
    parser.add_argument(
        "--categorize-agents",
        action="store_true",
        help="Categorize Python classes into maturity level and agent type.",
    )
    parser.add_argument(
        "--no-chatgpt-context", action="store_true", help="Skip exporting ChatGPT context."
    )
    parser.add_argument(
        "--generate-init", action="store_true", help="Enable auto-generating __init__.py files."
    )
    args = parser.parse_args()

    scanner = ProjectScanner(project_root=args.project_root)
    scanner.additional_ignore_dirs = set(args.ignore)

    scanner.scan_project()

    if args.generate_init:
        scanner.generate_init_files(overwrite=True)

    if args.categorize_agents:
        scanner.categorize_agents()
        scanner.report_generator.save_report()
        logging.info(
            "✅ Agent categorization complete. Updated %s",
            scanner.report_generator.analysis_file,
        )

    if not args.no_chatgpt_context:
        scanner.export_chatgpt_context()
        logging.info("✅ ChatGPT context exported by default.")

        context_path = Path(args.project_root) / scanner.report_generator.context_file
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:  # pragma: no cover
                logger.error("❌ Error reading exported ChatGPT context: %s", e)


if __name__ == "__main__":  # pragma: no cover
    main()
