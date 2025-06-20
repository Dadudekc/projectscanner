# Validation Report

## Test Results

```
pytest -q
```
All tests pass (3 passed) with a few deprecation warnings from the Python `ast` module.

## Manual CLI Run

```
python project_scanner.py --project-root . --no-chatgpt-context
```
The scanner processed this repository and produced `project_analysis_projectscanner.json`.

Overall the core functionality works as expected. Rust and JavaScript parsing requires tree-sitter libraries which are not bundled, so those languages fall back to no-op parsing unless installed.

