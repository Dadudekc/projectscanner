# ProjectScanner

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

ProjectScanner is a lightweight tool for generating a structured overview of a codebase. It scans Python, Rust and JavaScript/TypeScript files and produces JSON reports that are easy to feed into language models or other automation systems. The project demonstrates multithreaded file processing, AST analysis and incremental caching.

## Key Features

- **Multi‑language parsing** – Python, Rust and JS/TS support
- **Concurrent scanning** – worker threads handle files in parallel
- **Incremental caching** – skip previously processed files
- **Agent categorisation** – classify Python classes by maturity level and type
- **ChatGPT context export** – minimal JSON payload for LLM prompts
- **Optional GUI** – browse reports with a small PyQt5 viewer

## Architecture Overview

```
CLI -> ProjectScanner -> MultibotManager -> BotWorker threads
                 |            |
                 |            +-- FileProcessor (hashing & caching)
                 |            |
                 |            +-- LanguageAnalyzer (AST parsing)
                 +-- ReportGenerator (JSON export)
```

The CLI creates a `ProjectScanner` which spawns `BotWorker` threads via `MultibotManager`. Each worker uses `LanguageAnalyzer` and `FileProcessor` to parse and cache results, then `ReportGenerator` merges everything into JSON.

## Setup

1. Clone this repository and install the package in editable mode:
   ```bash
   pip install -e .
   ```
2. (Optional) Install `PyQt5` if you want to use the GUI viewer:
   ```bash
   pip install PyQt5
   ```

## Usage

Run the scanner from a project directory:

```bash
project-scanner --project-root .
```

The command creates two files in the root:

- `project_analysis_<name>.json` – merged summary of all files
- `chatgpt_project_context_<name>.json` – reduced context for ChatGPT

Useful flags:

- `--categorize-agents` – add maturity/agent type details to classes
- `--generate-init` – automatically create `__init__.py` files
- `--no-chatgpt-context` – skip the ChatGPT context export
- `--output-dir` – directory to store generated JSON reports

To inspect the results visually, launch the GUI:

```bash
python -m projectscanner.gui <project_root>
```

## Running Tests

Tests are written with `pytest` and cover the core analysis logic. Execute:

```bash
pytest
```

## Contributing & License

Contributions are welcome via pull requests. This project is released under the [MIT License](LICENSE).

