# ProjectScanner PRD

## Purpose
ProjectScanner is a lightweight tool for generating a structured overview of a codebase. It supports Python, Rust, JavaScript and TypeScript files and produces JSON reports suitable for other tools or language models.

## Problem Statement
Developers often need quick insight into unfamiliar repositories. Manually exploring source files is time consuming. ProjectScanner automates static analysis so teams can rapidly understand project structure and feed the data into automation workflows.

## Solution Overview
- Multi-language parsing using ASTs (Python) and optional tree-sitter parsers (Rust/JS/TS)
- Incremental caching to skip unchanged files
- Concurrent file processing via worker threads
- Agent categorisation of Python classes by maturity and type
- Export of simplified context for ChatGPT or other LLM prompts
- Optional PyQt5 GUI viewer for generated JSON

## Key Features
1. **Command-line interface** to scan projects and manage options
2. **Report generator** merges analysis results and writes JSON files
3. **Plugin-style language analyser** for multiple languages
4. **Support for generating `__init__.py` files** after analysis
5. **ChatGPT context export** for LLM integrations

## Non-Goals
- Runtime or dynamic code analysis
- Automatic code generation or refactoring
- Deep language-specific metrics beyond simple complexity counts

## Success Metrics
- CLI produces valid JSON summaries for supported languages
- All unit tests pass (`pytest`)
- Scanning a medium-sized project (100+ files) finishes within a few minutes on a typical laptop

## Future Enhancements
- Packaging optional tree-sitter grammars for Rust and JavaScript
- Support for additional languages via plugins
- More granular complexity metrics and lint-style suggestions
