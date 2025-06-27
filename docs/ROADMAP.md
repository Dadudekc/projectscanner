# ProjectScanner Roadmap

## 0.1 - MVP (Done)
- Basic Python scanning with AST extraction
- Simple CLI and JSON report generation

## 0.2 - Caching & Concurrency (Done)
- Incremental caching of file hashes
- Multithreaded file processing via BotWorker threads

## 0.3 - Multi-language Support (Done)
- Optional tree-sitter parsers for Rust, JavaScript and TypeScript
- Initial complexity metrics

## 0.4 - GUI & Agent Categorisation (Done)
- PyQt5 viewer for analysis files
- Maturity level and agent type tagging for Python classes
- ChatGPT context export

## 0.5 - Upcoming
- Bundle tree-sitter grammar libraries for easier setup
- Plugin architecture for additional languages
- Improve complexity metrics and provide lint suggestions
- Add more CLI options for custom report locations

## 1.0 - Future Goals
- Integration with code hosting platforms (GitHub/GitLab)
- Automatic scheduling to scan large monorepos
- Richer web UI for browsing reports
