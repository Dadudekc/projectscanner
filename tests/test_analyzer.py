import builtins
import json
import threading
from pathlib import Path

from projectscanner.language_analyzer import LanguageAnalyzer
from projectscanner.file_processor import FileProcessor
from projectscanner.scanner import ProjectScanner


def test_analyze_python_extracts_functions_classes_and_routes():
    source = '''
from flask import Flask
app = Flask(__name__)

@app.route("/foo", methods=["GET", "POST"])
def bar():
    pass

class MyClass(Base):
    """Doc"""
    def __init__(self):
        pass
    def run(self):
        pass

def foo():
    pass
'''
    analyzer = LanguageAnalyzer()
    result = analyzer.analyze_file(Path('dummy.py'), source)
    assert result["language"] == ".py"
    assert set(result["functions"]) >= {"bar", "foo"}
    assert "MyClass" in result["classes"]
    routes = result["routes"]
    assert any(r["function"] == "bar" and r["method"] == "GET" for r in routes)
    assert result["complexity"] == 6
    assert isinstance(result.get("lint"), list)


def test_file_processor_should_exclude_common_dirs(tmp_path):
    processor = FileProcessor(tmp_path, {}, threading.Lock(), set())
    assert processor.should_exclude(tmp_path / "venv" / "lib.py")
    assert processor.should_exclude(tmp_path / "node_modules" / "mod.js")
    assert processor.should_exclude(tmp_path / ".git" / "config")


def test_scanner_maturity_and_agent_type():
    scanner = ProjectScanner(project_root=".")
    mature = {
        "docstring": "A class",
        "methods": ["a", "b", "c", "d"],
        "base_classes": ["Base"],
    }
    proto = {"methods": [], "base_classes": [], "docstring": None}
    assert scanner._maturity_level("MyClass", mature) == "Core Asset"
    assert scanner._maturity_level("foo", proto) == "Kiddie Script"

    action = {"methods": ["run"], "docstring": ""}
    data = {"methods": [], "docstring": "transform input"}
    signal = {"methods": ["predict"], "docstring": ""}
    util = {"methods": [], "docstring": ""}
    assert scanner._agent_type("A", action) == "ActionAgent"
    assert scanner._agent_type("B", data) == "DataAgent"
    assert scanner._agent_type("C", signal) == "SignalAgent"
    assert scanner._agent_type("D", util) == "Utility"


def test_generate_init_and_chatgpt_export(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def foo():\n    pass\n")
    scanner = ProjectScanner(project_root=tmp_path)
    scanner.cache.clear()
    scanner.scan_project()
    scanner.generate_init_files()
    assert (pkg / "__init__.py").exists()

    scanner.export_chatgpt_context()
    context_file = scanner.output_dir / scanner.report_generator.context_file
    assert context_file.exists()
    data = json.loads(context_file.read_text())
    assert data["num_files_analyzed"] >= 1

