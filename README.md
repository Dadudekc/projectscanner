## 🗂 `README.md`


```markdown
# 🔍 ProjectScanner — One-file Context Generator for LLMs & Devs

ProjectScanner is a **drop-in codebase analyzer** that generates high-level structural intelligence for LLMs like ChatGPT, Cursor, and Claude.

🪄 **Just drop `project_scanner.py` into any folder and run it.** It will:
- Detect all Python, Rust, JS, and TS files
- Extract functions, classes, routes, and complexity
- Generate:
  - `project_analysis.json` — developer-level overview
  - `chatgpt_project_context.json` — LLM-ready context prompt
Summary Judgment:
→ Use chatgpt_project_context.json when you want project-wide architectural moves.
→ Use project_analysis.json if you're doing targeted refactors or fast file-by-file tasking.
No setup. No boilerplate. Just insight.

---

## 🚀 Quick Start

### 1. Clone or copy the file

```bash
wget https://raw.githubusercontent.com/Dadudekc/projectscanner/main/ProjectScanner.py
```

### 2. Run it on your codebase

```bash
python project_scanner.py --project-root . --categorize-agents --generate-init
```

### 3. Results

- `project_analysis.json`: structural map of your codebase
- `chatgpt_project_context.json`: ready to paste into ChatGPT or Cursor

---

## 💡 Why Use This?

| For Developers         | For LLM Workflows               |
|------------------------|---------------------------------|
| Understand unknown codebases | Feed compressed project context |
| Detect structural drift | Boost prompt accuracy          |
| Auto-generate init files | Analyze agent maturity         |

---

## 🧰 Features

- ✅ **Single-file CLI** — drop into any repo
- 🚀 Async multithreaded scanning
- 📦 Auto `__init__.py` generation
- 🧠 Class maturity & agent-type classification
- ✨ Tree-sitter support (Rust, JS/TS, optional)
- 🧩 JSON & Jinja output for AI pipelines

---

## 🔌 Jinja Template Export (Optional)

```bash
python project_scanner.py --template context_template.j2 --output context.md
```

Your custom context will be rendered from any Jinja2 template.

---


And run it from anywhere:

```bash
project-scanner --project-root .
```

---

## 🛠 CLI Flags

| Flag                     | Description                                 |
|--------------------------|---------------------------------------------|
| `--project-root`         | Root directory to scan                      |
| `--ignore`               | Additional folders to exclude               |
| `--categorize-agents`    | Classify Python classes                     |
| `--generate-init`        | Generate `__init__.py` files                |
| `--no-chatgpt-context`   | Skip exporting `chatgpt_project_context.json` |
| `--template`             | Path to Jinja2 template                     |
| `--output`               | Path to render final context                |

---

## 🧠 What’s Next?

This project is free and open source. In the future:
- A browser-based dashboard
- LLM plugin mode (Cursor, OpenDevin, VSCode)
- Premium templates and agent context enrichment

---

## 🙏 Contributions Welcome

Issues, ideas, and PRs are all welcome.

---

## License

MIT
```

---

## 📦 `setup.py`

```python
# setup.py
from setuptools import setup

setup(
    name="project-scanner",
    version="0.1.0",
    py_modules=["project_scanner"],
    install_requires=[
        "jinja2",
        "tree_sitter ; platform_system != 'Windows'",  # optional for Rust/JS parsing
    ],
    entry_points={
        "console_scripts": [
            "project-scanner = project_scanner:main"
        ]
    },
    author="Your Name",
    description="Drop-in project scanner for generating LLM context and codebase intelligence.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_GITHUB/project-scanner",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
```

---

## 🧰 `pyproject.toml` (optional if using `setup.py`)

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

---

## ✅ Git Commit Suggestion

```bash
git add project_scanner.py setup.py pyproject.toml README.md
git commit -m "🚀 OSS Release: ProjectScanner v0.1 — drop-in LLM context generator"
```

