# ProjectScanner

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

ProjectScanner is a lightweight codebase analysis tool written in Python. It quickly scans a project directory, extracts high‑level structure and produces JSON reports that are easy to feed into language models or other automation tools.

Victor built this project to showcase the ability to orchestrate automation workflows around large code bases and LLM driven systems.

## Features

- **Multi‑language parsing** – supports Python, Rust and JavaScript/TypeScript files.
- **Asynchronous scanning** – uses worker threads to process files concurrently.
- **Caching** – remembers previous results to avoid unnecessary work.
- **Agent classification** – optional maturity and agent‑type scoring for Python classes.
- **ChatGPT context export** – generates a trimmed JSON payload for LLM prompts.
- **Optional GUI** – PyQt5 viewer for browsing the generated reports.

## Quick start

1. Install the package (edit `PYTHONPATH` or package as desired):
   ```bash
   pip install -e .
   ```
2. Run the scanner from the project root:
   ```bash
   project-scanner --project-root .
   ```
3. Two JSON files will be created:
   - `project_analysis_<name>.json` – merged summary of all files.
   - `chatgpt_project_context_<name>.json` – minimal context for LLM usage.

### Optional flags

- `--categorize-agents` – add maturity/agent type details to classes.
- `--generate-init` – auto create `__init__.py` files in packages.
- `--no-chatgpt-context` – skip LLM context export.

## Architecture

```
CLI -> ProjectScanner -> MultibotManager -> BotWorker threads
                 |            |
                 |            +-- FileProcessor (hashing & caching)
                 |            |
                 |            +-- LanguageAnalyzer (AST parsing)
                 +-- ReportGenerator (JSON export)
```

The CLI initializes `ProjectScanner`, which spawns multiple `BotWorker` threads via `MultibotManager`. Each worker hands a file to `LanguageAnalyzer` for AST parsing and `FileProcessor` for caching. `ReportGenerator` merges results and writes the final JSON reports.

## What this project demonstrates

- Practical use of AST parsing and code introspection.
- Thread‑based orchestration for I/O bound workloads.
- Clean JSON outputs for downstream automation or LLM prompts.

## Contributing & License

Issues and pull requests are welcome. This project is released under the [MIT License](LICENSE).
