# =============================
# app/ui/widgets/path_picker.py
# =============================
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog

class PathPicker(QWidget):
    def __init__(self, label: str = "Path"):
        super().__init__()
        self._path = ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel(label)
        self.edit = QLineEdit()
        self.btn = QPushButton("Browse…")
        lay.addWidget(self.lbl)
        lay.addWidget(self.edit)
        lay.addWidget(self.btn)
        self.btn.clicked.connect(self._browse)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder", ".")
        if d:
            self.set_path(d)

    def set_path(self, p: str):
        self._path = p or ""
        self.edit.setText(self._path)

    def path(self) -> str:
        return self.edit.text().strip()

