"""
This module defines the main window of the application, which provides the user interface
for configuring and running the patch extraction process.
"""

import os
import sys

from app.domain.config_model import AppConfig
from app.domain.pairing import list_pairs
from app.domain.patch_extractor import load_image, load_mask
from app.infrastructure.settings import AppSettings
from app.services.logging_bus import LogBus
from app.services.runner import ExtractionRunner
from app.ui.widgets.path_picker import PathPicker
from app.ui.widgets.preview_view import PreviewView
from app.ui.widgets.stats_panel import StatsPanel

# =============================
# app/ui/main_window.py
# =============================
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def load_stylesheet():
    """Load the QSS stylesheet from the assets folder."""
    qss_path = os.path.join(os.path.dirname(__file__), "assets", "style_params.qss")
    if not os.path.exists(qss_path):
        print(f"⚠️ Stylesheet not found at {qss_path}")
        return ""
    with open(qss_path, "r", encoding="utf-8") as f:
        return f.read()


class MainWindow(QMainWindow):
    """
    The main application window.

    This class builds the UI, connects signals to slots, handles user interactions,
    manages settings, and orchestrates the patch extraction process.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Patch Extractor")
        self.resize(1280, 800)

        self.settings = AppSettings()
        self.logbus = LogBus()

        self._build_ui()
        self._wire_signals()
        self._load_settings()

        self.runner = None

        # Apply stylesheet
        stylesheet = load_stylesheet()
        if stylesheet:
            self.setStyleSheet(stylesheet)

    # ---------------------- UI ----------------------
    def _build_ui(self):
        """Builds the main user interface."""
        central = QWidget(self)
        self.setCentralWidget(central)
        grid = QGridLayout(central)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(10)

        # Left controls
        self.left = QWidget()
        self.left.setObjectName("left_panel")  # For styling
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        self.data_root = PathPicker(label="Source Root")
        self.patch_root = PathPicker(label="Destination Root")

        self.patch_size = QSpinBox()
        self.patch_size.setRange(16, 4096)
        self.patch_size.setValue(256)
        self.stride = QSpinBox()
        self.stride.setRange(1, 4096)
        self.stride.setValue(256)
        self.min_mask_ratio = QDoubleSpinBox()
        self.min_mask_ratio.setRange(0.0, 1.0)
        self.min_mask_ratio.setSingleStep(0.05)
        self.min_mask_ratio.setValue(0.0)
        self.max_patches = QSpinBox()
        self.max_patches.setRange(0, 1000000)
        self.max_patches.setValue(0)
        self.save_fmt = QComboBox()
        self.save_fmt.addItems(["png", "jpg", "tif"])
        self.seed = QSpinBox()
        self.seed.setRange(0, 2**31 - 1)
        self.seed.setValue(123)
        self.image_extensions = QLineEdit()
        self.image_extensions.setText("*.jpg, *.jpeg, *.png, *.bmp, *.gif")

        self.cb_include_borders = QCheckBox(
            "Include right/bottom borders when not multiple of stride"
        )
        self.cb_apply_ratio_filter = QCheckBox(
            "Apply min-mask ratio filter (keep patches with coverage ≥ ratio)"
        )
        self.cb_apply_ratio_filter.setChecked(True)
        self.cb_dry_run = QCheckBox("Dry-run (analyze only, don’t write files)")

        def row(lbl, w):
            h = QHBoxLayout()
            h.addWidget(QLabel(lbl))
            h.addWidget(w)
            return h

        left_layout.addWidget(self.data_root)
        left_layout.addWidget(self.patch_root)
        left_layout.addLayout(row("Patch size:", self.patch_size))
        left_layout.addLayout(row("Stride:", self.stride))
        left_layout.addLayout(row("Min mask ratio:", self.min_mask_ratio))
        left_layout.addLayout(row("Max patches/image (0=all):", self.max_patches))
        left_layout.addLayout(row("Save format:", self.save_fmt))
        left_layout.addLayout(row("Random seed:", self.seed))
        left_layout.addLayout(row("Image Extensions:", self.image_extensions))
        left_layout.addWidget(self.cb_include_borders)
        left_layout.addWidget(self.cb_apply_ratio_filter)
        left_layout.addWidget(self.cb_dry_run)
        left_layout.addStretch(1)

        # Center preview
        self.preview = PreviewView()

        # Right: stats + log
        self.stats = StatsPanel()

        # Tab widget for logs and patch browser
        self.tabs = QTabWidget()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.patch_browser = QListWidget()
        self.tabs.addTab(self.log, "Logs")
        self.tabs.addTab(self.patch_browser, "Patch Browser")

        # Bottom run bar
        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("btn_start")
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setEnabled(False)
        self.btn_resume = QPushButton("Resume")
        self.btn_resume.setEnabled(False)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_open_out = QPushButton("Open Output")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        runbar = QHBoxLayout()
        for b in (
            self.btn_start,
            self.btn_pause,
            self.btn_resume,
            self.btn_cancel,
            self.btn_open_out,
        ):
            runbar.addWidget(b)
        runbar.addStretch(1)
        runbar.addWidget(self.progress)

        # Layout grid
        grid.addWidget(self.left, 0, 0, 2, 1)
        grid.addWidget(self.preview, 0, 1, 1, 1)
        grid.addWidget(self.stats, 1, 1, 1, 1)

        right = QVBoxLayout()
        w_right = QWidget()
        w_right.setLayout(right)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)
        # The label is now part of the tab, so we don't need a separate one.
        right.addWidget(self.tabs)
        grid.addWidget(w_right, 0, 2, 2, 1)

        grid.addLayout(runbar, 2, 0, 1, 3)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)

    def _wire_signals(self):
        """Connects UI element signals to corresponding slots."""
        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_resume.clicked.connect(self.on_resume)
        self.btn_cancel.clicked.connect(self.on_cancel)
        self.btn_open_out.clicked.connect(self.on_open_out)
        self.patch_browser.itemSelectionChanged.connect(self.on_patch_selected)

        self.logbus.sig_log.connect(self._append_log)

    def _append_log(self, text: str):
        """Appends a message to the log view."""
        self.log.append(text)

    # ---------------------- Settings ----------------------
    def _load_settings(self):
        """Loads the last used configuration from settings."""
        cfg = self.settings.load_last_config()
        if cfg:
            self.data_root.set_path(cfg.data_root)
            self.patch_root.set_path(cfg.patch_root)
            self.patch_size.setValue(cfg.patch_size)
            self.stride.setValue(cfg.stride)
            self.min_mask_ratio.setValue(cfg.min_mask_ratio)
            self.max_patches.setValue(cfg.max_patches_per_image)
            self.save_fmt.setCurrentText(cfg.save_format)
            self.seed.setValue(cfg.seed)
            self.image_extensions.setText(", ".join(cfg.image_extensions))
            self.cb_include_borders.setChecked(cfg.include_borders)
            self.cb_apply_ratio_filter.setChecked(cfg.apply_min_mask_ratio)

    def _gather_config(self) -> AppConfig:
        """Gathers the current configuration from the UI controls into an AppConfig object."""
        extensions = [
            ext.strip()
            for ext in self.image_extensions.text().split(",")
            if ext.strip()
        ]
        return AppConfig(
            data_root=self.data_root.path(),
            patch_root=self.patch_root.path(),
            patch_size=self.patch_size.value(),
            stride=self.stride.value(),
            min_mask_ratio=self.min_mask_ratio.value(),
            max_patches_per_image=self.max_patches.value(),
            save_format=self.save_fmt.currentText(),
            seed=self.seed.value(),
            image_extensions=extensions,
            include_borders=self.cb_include_borders.isChecked(),
            apply_min_mask_ratio=self.cb_apply_ratio_filter.isChecked(),
            dry_run=self.cb_dry_run.isChecked(),
        )

    # ---------------------- Actions ----------------------
    def on_start(self):
        """
        Starts the patch extraction process.

        Validates the configuration, pre-flights the data, and starts the runner thread.
        """
        cfg = self._gather_config()
        err = cfg.validate()
        if err:
            self._append_log(f"<span style='color:#c00'>Config error: {err}</span>")
            return

        # Simple preflight + sample preview
        images_dir = os.path.join(cfg.data_root, self.settings.image_folder_name())
        masks_dir = os.path.join(cfg.data_root, self.settings.mask_folder_name())
        pairs = list_pairs(images_dir, masks_dir, cfg.image_extensions)
        if not pairs:
            self._append_log(
                "<b>No pairs found.</b> Check data root, phase, and extensions."
            )
            return
        self._append_log(f"Found {len(pairs)} pairs. Starting…")

        self.settings.save_last_config(cfg)

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(0)

        self.runner = ExtractionRunner(cfg, self.logbus)
        self.runner.sig_progress.connect(self.progress.setValue)
        self.runner.sig_stats.connect(self.stats.update_stats)
        self.runner.sig_preview.connect(self.preview.show_sample)
        self.runner.sig_done.connect(self.on_done)
        self.runner.start()

    def on_pause(self):
        """Pauses the running extraction process."""
        if self.runner:
            self.runner.pause()
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(True)

    def on_resume(self):
        """Resumes a paused extraction process."""
        if self.runner:
            self.runner.resume()
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)

    def on_cancel(self):
        """Requests cancellation of the running extraction process."""
        if self.runner:
            self.runner.cancel()

    def on_done(self, ok: bool, msg: str):
        """
        Handles the completion of the extraction process.

        Args:
            ok (bool): True if the process completed successfully, False otherwise.
            msg (str): A status message from the runner.
        """
        self._append_log(msg)
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setValue(100 if ok else 0)
        if ok:
            self.populate_patch_browser()

    def on_open_out(self):
        """Opens the output directory in the system's file explorer."""
        cfg = self._gather_config()
        path = cfg.patch_root
        if os.path.isdir(path):
            # This is a bit of a hack to open the folder, as Qt doesn't have a direct way.
            # On Windows, this will open an explorer window.
            # On macOS/Linux, it might behave differently.
            # A more robust solution would use QDesktopServices.
            import subprocess

            if sys.platform == "win32":
                subprocess.run(["explorer", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            self._append_log("Output folder does not exist yet.")

    def populate_patch_browser(self):
        """Scans the output directory and populates the patch browser list."""
        self.patch_browser.clear()
        cfg = self._gather_config()
        patch_img_dir = os.path.join(cfg.patch_root, "Image")

        if not os.path.isdir(patch_img_dir):
            return

        try:
            patch_files = sorted(os.listdir(patch_img_dir))
            self.patch_browser.addItems(patch_files)
            self._append_log(f"Patch browser populated with {len(patch_files)} items.")
            if patch_files:
                self.tabs.setCurrentWidget(self.patch_browser)
        except Exception as e:
            self._append_log(
                f"<span style='color:#c00'>Error populating patch browser: {e}</span>"
            )

    def on_patch_selected(self):
        """Handles selection changes in the patch browser."""
        if not self.patch_browser.selectedItems():
            return

        item = self.patch_browser.selectedItems()[0]
        patch_filename = item.text()

        cfg = self._gather_config()
        patch_img_path = os.path.join(cfg.patch_root, "Image", patch_filename)
        patch_mask_path = os.path.join(cfg.patch_root, "Mask", patch_filename)

        if not os.path.exists(patch_img_path) or not os.path.exists(patch_mask_path):
            self._append_log(
                f"<span style='color:#c00'>Could not find patch pair for {patch_filename}</span>"
            )
            return

        try:
            img = load_image(patch_img_path)
            mask = load_mask(patch_mask_path)
            self.preview.show_sample(img, mask)
        except Exception as e:
            self._append_log(
                f"<span style='color:#c00'>Error loading patch preview: {e}</span>"
            )
