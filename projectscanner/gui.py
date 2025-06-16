import json
import sys
import re
from pathlib import Path
from PyQt5 import QtWidgets


class AnalysisViewer(QtWidgets.QMainWindow):
    """Simple viewer for ProjectScanner JSON outputs."""

    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = Path(project_root).resolve()
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", self.project_root.name)
        self.analysis_file = f"project_analysis_{name}.json"
        self.context_file = f"chatgpt_project_context_{name}.json"
        self.setWindowTitle("ProjectScanner Viewer")
        self.analysis_data = {}
        self.context_data = {}

        self.tabs = QtWidgets.QTabWidget()
        self.analysis_tree = QtWidgets.QTreeWidget()
        self.context_tree = QtWidgets.QTreeWidget()
        for tree in (self.analysis_tree, self.context_tree):
            tree.setHeaderHidden(True)
        self.tabs.addTab(self.analysis_tree, "Project Analysis")
        self.tabs.addTab(self.context_tree, "ChatGPT Context")

        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)

        save_analysis_btn = QtWidgets.QPushButton("Save Analysis As…")
        save_analysis_btn.clicked.connect(lambda: self.save_json(self.analysis_data))
        save_context_btn = QtWidgets.QPushButton("Save Context As…")
        save_context_btn.clicked.connect(lambda: self.save_json(self.context_data))

        btn_layout = QtWidgets.QHBoxLayout()
        for btn in (refresh_btn, save_analysis_btn, save_context_btn):
            btn_layout.addWidget(btn)
        btn_layout.addStretch(1)

        container = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(container)
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(btn_layout)
        self.setCentralWidget(container)

        self.refresh()

    def refresh(self):
        analysis_path = self.project_root / self.analysis_file
        context_path = self.project_root / self.context_file
        self.analysis_data = self.load_json(analysis_path)
        self.context_data = self.load_json(context_path)
        self.populate_tree(self.analysis_tree, self.analysis_data)
        self.populate_tree(self.context_tree, self.context_data)

    def load_json(self, path: Path):
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:  # pragma: no cover - GUI feedback
            return {"error": f"Failed to load {path}: {exc}"}

    def populate_tree(self, tree: QtWidgets.QTreeWidget, data):
        tree.clear()

        def add_items(parent, value):
            if isinstance(value, dict):
                for key, val in value.items():
                    item = QtWidgets.QTreeWidgetItem([str(key)])
                    parent.addChild(item)
                    add_items(item, val)
            elif isinstance(value, list):
                for i, val in enumerate(value):
                    item = QtWidgets.QTreeWidgetItem([f"[{i}]"])
                    parent.addChild(item)
                    add_items(item, val)
            else:
                item = QtWidgets.QTreeWidgetItem([str(value)])
                parent.addChild(item)

        root = QtWidgets.QTreeWidgetItem(["root"])
        add_items(root, data)
        tree.addTopLevelItem(root)
        tree.expandToDepth(1)

    def save_json(self, data):
        if not data:
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save JSON", str(self.project_root), "JSON Files (*.json)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)


def main():  # pragma: no cover - manual invocation only
    app = QtWidgets.QApplication(sys.argv)
    parser = QtWidgets.QCommandLineParser()
    parser.addHelpOption()
    parser.addPositionalArgument("project_root", "Project directory", "[project root]")
    parser.process(app)
    args = parser.positionalArguments()
    root = args[0] if args else "."
    viewer = AnalysisViewer(Path(root))
    viewer.resize(800, 600)
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    main()
