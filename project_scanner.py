import os
import ast
import json
import hashlib
import threading
import queue
import logging
from pathlib import Path
from typing import Dict, Union, Optional, List, Any
import argparse

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")

# ---------------------------------
# Project Config / Cache File Setup
# ---------------------------------
CACHE_FILE = "dependency_cache.json"
# Faster to delete and have it rewrite the whole thing(dependency_cache.json)...ngl
# We'll store our final "project_analysis.json" and "chatgpt_project_context.json"
# in the project root, merging new data with old each time.


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""
    def __init__(self):
        """Initialize language analyzers and parsers."""
        self.rust_parser = self._init_tree_sitter_language("rust")
        self.js_parser = self._init_tree_sitter_language("javascript")

    def _init_tree_sitter_language(self, lang_name: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name (rust, javascript).
        Adjust grammar_paths to point at your compiled .so files if using tree-sitter.
        """
        if not Language or not Parser:
            logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",          # <-- Adjust as needed
            "javascript": "path/to/tree-sitter-javascript.so"  # <-- Adjust as needed
        }
        if lang_name not in grammar_paths:
            logger.warning(f"⚠️ No grammar path for {lang_name}. Skipping.")
            return None

        grammar_path = grammar_paths[lang_name]
        if not Path(grammar_path).exists():
            logger.warning(f"⚠️ {lang_name} grammar not found at {grammar_path}")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            return parser
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize tree-sitter {lang_name} parser: {e}")
            return None

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyzes source code based on file extension.

        Args:
            file_path: Path to the source file
            source_code: Contents of the source file

        Returns:
            Dict with structure {language, functions, classes, routes, complexity}
        """
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return self._analyze_python(source_code)
        elif suffix == ".rs" and self.rust_parser:
            return self._analyze_rust(source_code)
        elif suffix in [".js", ".ts"] and self.js_parser:
            return self._analyze_javascript(source_code)
        else:
            return {
                "language": suffix,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0
            }

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        tree = ast.parse(source_code)
        functions = []
        classes = {}
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

                # Route detection (Flask/FastAPI style) from existing logic
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            if decorator.args:
                                arg0 = decorator.args[0]
                                if isinstance(arg0, ast.Str):
                                    path_arg = arg0.s
                            # Check for "methods" kwarg
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, ast.List):
                                    extracted_methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Str):
                                            extracted_methods.append(elt.s.upper())
                                    if extracted_methods:
                                        methods = extracted_methods
                            for m in methods:
                                routes.append({"function": node.name, "method": m, "path": path_arg})

            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_parts = []
                        attr_node = base
                        while isinstance(attr_node, ast.Attribute):
                            base_parts.append(attr_node.attr)
                            attr_node = attr_node.value
                        if isinstance(attr_node, ast.Name):
                            base_parts.append(attr_node.id)
                        base_classes.append(".".join(reversed(base_parts)))
                    else:
                        base_classes.append(None)
                classes[node.name] = {
                    "methods": method_names,
                    "docstring": docstring,
                    "base_classes": base_classes
                }

        # Complexity = function count + sum of class methods
        complexity = len(functions) + sum(len(c["methods"]) for c in classes.values())
        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available)."""
        if not self.rust_parser:
            return {"language": ".rs", "functions": [], "classes": {}, "routes": [], "complexity": 0}

        tree = self.rust_parser.parse(bytes(source_code, "utf-8"))
        functions = []
        classes = {}

        def _traverse(node):
            if node.type == "function_item":
                fn_name_node = node.child_by_field_name("name")
                if fn_name_node:
                    functions.append(fn_name_node.text.decode("utf-8"))
            elif node.type == "struct_item":
                struct_name_node = node.child_by_field_name("name")
                if struct_name_node:
                    classes[struct_name_node.text.decode("utf-8")] = []
            elif node.type == "impl_item":
                impl_type_node = node.child_by_field_name("type")
                if impl_type_node:
                    impl_name = impl_type_node.text.decode("utf-8")
                    if impl_name not in classes:
                        classes[impl_name] = []
                    for child in node.children:
                        if child.type == "function_item":
                            method_node = child.child_by_field_name("name")
                            if method_node:
                                classes[impl_name].append(method_node.text.decode("utf-8"))
            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)
        complexity = len(functions) + sum(len(m) for m in classes.values())
        return {
            "language": ".rs",
            "functions": functions,
            "classes": classes,
            "routes": [],
            "complexity": complexity
        }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available)."""
        if not self.js_parser:
            return {"language": ".js", "functions": [], "classes": {}, "routes": [], "complexity": 0}

        tree = self.js_parser.parse(bytes(source_code, "utf-8"))
        root = tree.root_node
        functions = []
        classes = {}
        routes = []

        def get_node_text(node):
            return node.text.decode("utf-8")

        def _traverse(node):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    functions.append(get_node_text(name_node))
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    cls_name = get_node_text(name_node)
                    classes[cls_name] = []
            elif node.type == "lexical_declaration":
                # arrow functions, etc.
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if name_node and value_node and value_node.type == "arrow_function":
                            functions.append(get_node_text(name_node))
            elif node.type == "call_expression":
                if node.child_count >= 2:
                    callee_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if callee_node:
                        callee_text = get_node_text(callee_node)
                        parts = callee_text.split(".")
                        if len(parts) == 2:
                            obj, method = parts
                            if method.lower() in {"get", "post", "put", "delete", "patch"}:
                                path_str = "/unknown"
                                if args_node and args_node.child_count > 0:
                                    first_arg = args_node.child(0)
                                    if first_arg.type == "string":
                                        path_str = get_node_text(first_arg).strip('"\'')
                                routes.append({
                                    "object": obj,
                                    "method": method.upper(),
                                    "path": path_str
                                })
            for child in node.children:
                _traverse(child)

        _traverse(root)
        complexity = len(functions) + sum(len(v) for v in classes.values())
        return {
            "language": ".js",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }


# ---------------------------------
# BotWorker & MultibotManager
# ---------------------------------
class BotWorker(threading.Thread):
    """
    A background worker that pulls file tasks from a queue,
    processes them, and appends results to results_list.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner, status_callback=None):
        super().__init__()
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            file_path = self.task_queue.get()
            if file_path is None:
                break
            result = self.scanner._process_file(file_path)
            if result is not None:
                self.results_list.append(result)
            if self.status_callback:
                self.status_callback(file_path, result)
            self.task_queue.task_done()

class MultibotManager:
    """Manages a pool of BotWorker threads."""
    def __init__(self, scanner, num_workers=4, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list = []
        self.scanner = scanner
        self.status_callback = status_callback
        self.workers = [
            BotWorker(self.task_queue, self.results_list, scanner, status_callback)
            for _ in range(num_workers)
        ]

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        self.task_queue.join()

    def stop_workers(self):
        for _ in self.workers:
            self.task_queue.put(None)


# ---------------------------------
# FileProcessor
# ---------------------------------
class FileProcessor:
    """Handles file hashing, ignoring, caching checks, etc."""
    def __init__(self, project_root: Path, cache: Dict, cache_lock: threading.Lock, additional_ignore_dirs: set):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_dirs = additional_ignore_dirs

    def hash_file(self, file_path: Path) -> str:
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """Exclude logic for venvs, node_modules, .git, etc."""
        # Common virtual environment patterns
        venv_patterns = {
            "venv", "env", ".env", ".venv", "virtualenv", 
            "ENV", "VENV", ".ENV", ".VENV",
            "python-env", "python-venv", "py-env", "py-venv",
            # Common Conda environment locations
            "envs", "conda-env", ".conda-env",
            # Poetry virtual environments
            ".poetry/venv", ".poetry-venv"
        }
        
        default_exclude_dirs = {
            "__pycache__", "node_modules", "migrations", "build",
            "target", ".git", "coverage", "chrome_profile"
        } | venv_patterns  # Merge with venv patterns
        
        file_abs = file_path.resolve()
        
        # Check if this is the scanner itself
        try:
            if file_abs == Path(__file__).resolve():
                return True
        except NameError:
            pass
            
        # Check additional ignore directories
        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_abs.relative_to(ignore_path)
                return True
            except ValueError:
                continue
                
        # Check for virtual environment indicators
        try:
            # Look for pyvenv.cfg or similar files that indicate a venv
            if any(p.name == "pyvenv.cfg" for p in file_abs.parents):
                return True
            
            # Look for bin/activate or Scripts/activate.bat
            for parent in file_abs.parents:
                if (parent / "bin" / "activate").exists() or \
                   (parent / "Scripts" / "activate.bat").exists():
                    return True
        except (OSError, PermissionError):
            # Handle permission errors gracefully
            pass
            
        # Check for excluded directory names in the path
        if any(excluded in file_path.parts for excluded in default_exclude_dirs):
            return True
            
        # Check for common virtual environment path patterns
        path_str = str(file_abs).lower()
        if any(f"/{pattern}/" in path_str.replace("\\", "/") 
               for pattern in venv_patterns):
            return True
            
        return False

    def process_file(self, file_path: Path, language_analyzer: LanguageAnalyzer) -> Optional[tuple]:
        """Analyzes a file if not in cache or changed, else returns None."""
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
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
            return None


# ---------------------------------
# ReportGenerator (Merges Old + New)
# ---------------------------------
class ReportGenerator:
    """Handles merging new analysis into existing project_analysis.json and chatgpt context."""

    def __init__(self, project_root: Path, analysis: Dict[str, Dict]):
        self.project_root = project_root
        self.analysis = analysis  # e.g. { 'subdir/file.py': {language:..., classes:...}, ... }

    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads any existing project_analysis.json to preserve old entries."""
        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing report {report_path}: {e}")
        return {}

    def save_report(self):
        """
        Merge new analysis results into old project_analysis.json, then write it out.
        Old data is kept; new files are added or updated.
        """
        report_path = self.project_root / "project_analysis.json"
        existing = self.load_existing_report(report_path)

        # Merge logic: new data overrides old entries with the same filename,
        # but preserves any old entries for files not in the current scan.
        merged = {**existing, **self.analysis}

        with report_path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)

        logger.info(f"✅ Project analysis updated and saved to {report_path}")

    def generate_init_files(self, overwrite: bool = True):
        """Auto-generate __init__.py for all Python packages based on self.analysis."""
        from collections import defaultdict
        package_modules = defaultdict(list)
        for rel_path in self.analysis.keys():
            if rel_path.endswith(".py"):
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue
                package_dir = file_path.parent
                module_name = file_path.stem
                package_modules[str(package_dir)].append(module_name)

        for package, modules in package_modules.items():
            package_path = self.project_root / package
            init_file = package_path / "__init__.py"
            package_path.mkdir(parents=True, exist_ok=True)

            lines = [
                "# AUTO-GENERATED __init__.py",
                "# DO NOT EDIT MANUALLY - changes may be overwritten\n"
            ]
            for module in sorted(modules):
                lines.append(f"from . import {module}")
            lines.append("\n__all__ = [")
            for module in sorted(modules):
                lines.append(f"    '{module}',")
            lines.append("]\n")
            content = "\n".join(lines)

            if overwrite or not init_file.exists():
                with init_file.open("w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"✅ Generated __init__.py in {package_path}")
            else:
                logger.info(f"ℹ️ Skipped {init_file} (already exists)")

    def load_existing_chatgpt_context(self, context_path: Path) -> Dict[str, Any]:
        """Load any existing chatgpt_project_context.json."""
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing ChatGPT context: {e}")
        return {}

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None):
        """
        Merges current analysis details with old chatgpt_project_context.json.
        Again, old keys remain unless overridden by new data.
        If no template, write JSON. Else use Jinja to render a custom format.
        """
        if not output_path:
            context_path = self.project_root / "chatgpt_project_context.json"
        else:
            context_path = Path(output_path)
        context_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Writing ChatGPT context to: {context_path}")


        # If no template, do direct JSON merging
        if not template_path:
            existing_context = self.load_existing_chatgpt_context(context_path)
            payload = {
                "project_root": str(self.project_root),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis
            }
            # New data overrides same keys, but preserves everything else.
            merged_context = {**existing_context, **payload}
            try:
                with context_path.open("w", encoding="utf-8") as f:
                    json.dump(merged_context, f, indent=4)
                logger.info(f"✅ Merged ChatGPT context saved to: {context_path}")
            except Exception as e:
                logger.error(f"❌ Error writing ChatGPT context: {e}")
            return

        # If we do have a template, we can still load old data, but we'll not attempt JSON merging.
        # We'll just produce a final rendered template containing the new analysis.
        try:
            from jinja2 import Template
            with open(template_path, "r", encoding="utf-8") as tf:
                template_content = tf.read()
            t = Template(template_content)

            # Could load existing context if you want. We'll skip that for Jinja scenario.
            context_dict = {
                "project_root": str(self.project_root),
                "analysis": self.analysis,
                "num_files_analyzed": len(self.analysis),
            }
            rendered = t.render(context=context_dict)
            with context_path.open("w", encoding="utf-8") as outf:
                outf.write(rendered)
            logger.info(f"✅ Rendered ChatGPT context to: {output_path}")
        except ImportError:
            logger.error("⚠️ Jinja2 not installed. Run `pip install jinja2` and re-try.")
        except Exception as e:
            logger.error(f"❌ Error rendering Jinja template: {e}")


# ---------------------------------
# ProjectScanner
# ---------------------------------
class ProjectScanner:
    """
    A universal project scanner that:
      - Identifies Python, Rust, JS, TS files.
      - Extracts functions, classes, routes, complexity.
      - Caches file hashes to skip unchanged files.
      - Detects moved files by matching file hashes.
      - Merges new analysis into existing project_analysis.json (preserving old entries).
      - Exports a merged ChatGPT context if requested (preserving old context data).
      - Processes files asynchronously with BotWorker threads.
      - Auto-generates __init__.py files for Python packages.
    """
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
            self.additional_ignore_dirs
        )
        self.report_generator = ReportGenerator(self.project_root, self.analysis)

    def load_cache(self) -> Dict:
        """Loads JSON cache from disk if present. Otherwise returns empty."""
        cache_path = Path(CACHE_FILE)
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_cache(self):
        """Writes the updated cache to disk."""
        cache_path = Path(CACHE_FILE)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    def scan_project(self, progress_callback: Optional[callable] = None):
        """
        Orchestrates the project scan:
        - Finds Python, Rust, JS, TS files with os.walk()
        - Excludes certain directories
        - Detects moved files by comparing cached hashes
        - Spawns multibot workers for concurrency
        - Merges new analysis with old project_analysis.json (preserving old data)
        - Writes/updates 'project_analysis.json' without overwriting unscanned files
        - Reports progress via progress_callback(percent)
        """
        logger.info(f"🔍 Scanning project: {self.project_root} ...")

        file_extensions = {'.py', '.rs', '.js', '.ts'}
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
        logger.info(f"📝 Found {total_files} valid files for analysis.")

        # Progress reporting: update every file processed
        processed_count = 0

        previous_files = set(self.cache.keys())
        current_files = {str(f.relative_to(self.project_root)) for f in valid_files}
        moved_files = {}
        missing_files = previous_files - current_files

        # Detect moved files by matching file hashes
        for old_path in previous_files:
            old_hash = self.cache.get(old_path, {}).get("hash")
            if not old_hash:
                continue
            for new_path in current_files:
                new_file = self.project_root / new_path
                if self.file_processor.hash_file(new_file) == old_hash:
                    moved_files[old_path] = new_path
                    break

        # Remove truly missing files from cache
        for missing_file in missing_files:
            if missing_file not in moved_files:
                with self.cache_lock:
                    if missing_file in self.cache:
                        del self.cache[missing_file]

        # Update cache for moved files
        for old_path, new_path in moved_files.items():
            with self.cache_lock:
                self.cache[new_path] = self.cache.pop(old_path)

        # Asynchronous processing
        logger.info("⏱️  Processing files asynchronously...")
        num_workers = os.cpu_count() or 4
        manager = MultibotManager(
            scanner=self,
            num_workers=num_workers,
            status_callback=lambda fp, res: logger.info(f"Processed: {fp}")
        )
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()

        # Update progress for each processed file
        for result in manager.results_list:
            processed_count += 1
            if progress_callback:
                percent = int((processed_count / total_files) * 100)
                progress_callback(percent)
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        # Merge & write final report + save updated cache
        self.report_generator.save_report() 
        self.save_cache()
        logger.info(f"✅ Scan complete. Results merged into {self.project_root / 'project_analysis.json'} (preserving existing file data)")


    def _process_file(self, file_path: Path):
        """Processes a file via FileProcessor, returning (relative_path, analysis_result)."""
        return self.file_processor.process_file(file_path, self.language_analyzer)

    def generate_init_files(self, overwrite: bool = True):
        """Generate __init__.py for python packages."""
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None):
        """Merges new analysis into old chatgpt_project_context.json or uses a Jinja template, preserving existing data."""
        self.report_generator.export_chatgpt_context(template_path, output_path)

    # ----- Agent Categorization -----
    def categorize_agents(self):
        """
        Loops over analyzed Python classes, assigning maturity & agent_type.
        """
        for file_path, result in self.analysis.items():
            if file_path.endswith(".py"):
                for class_name, class_data in result.get("classes", {}).items():
                    class_data["maturity"] = self._maturity_level(class_name, class_data)
                    class_data["agent_type"] = self._agent_type(class_name, class_data)

    def _maturity_level(self, class_name: str, class_data: Dict[str, Any]) -> str:
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

    def _agent_type(self, class_name: str, class_data: Dict[str, Any]) -> str:
        doc = (class_data.get("docstring") or "").lower()
        methods = class_data.get("methods", [])
        if "run" in methods:
            return "ActionAgent"
        if "transform" in doc or "parse" in doc:
            return "DataAgent"
        if any(m in methods for m in ["predict", "analyze"]):
            return "SignalAgent"
        return "Utility"

# ---------------------------------
# CLI Usage
# ---------------------------------
def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Project scanner with agent categorization and incremental caching.")
    parser.add_argument("--project-root", default=".", help="Root directory to scan.")
    parser.add_argument("--ignore", nargs="*", default=[], help="Additional directories to ignore.")
    parser.add_argument("--categorize-agents", action="store_true", help="Categorize Python classes into maturity level and agent type.")
    parser.add_argument("--no-chatgpt-context", action="store_true", help="Skip exporting ChatGPT context.")
    parser.add_argument("--generate-init", action="store_true", help="Enable auto-generating __init__.py files.")
    args = parser.parse_args()

    scanner = ProjectScanner(project_root=args.project_root)
    scanner.additional_ignore_dirs = set(args.ignore)

    scanner.scan_project()

    if args.generate_init:
        scanner.generate_init_files(overwrite=True)

    if args.categorize_agents:
        scanner.categorize_agents()
        scanner.report_generator.save_report()
        logging.info("✅ Agent categorization complete. Updated project_analysis.json.")

    if not args.no_chatgpt_context:
        scanner.export_chatgpt_context()
        logging.info("✅ ChatGPT context exported by default.")

        # Output merged ChatGPT context to stdout
        context_path = Path(args.project_root) / "chatgpt_project_context.json"
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    chatgpt_context = json.load(f)
            except Exception as e:
                logger.error(f"❌ Error reading exported ChatGPT context: {e}")

if __name__ == "__main__":
    main()

