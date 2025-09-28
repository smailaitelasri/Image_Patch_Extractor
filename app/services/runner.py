# =============================
# services/runner.py
# =============================
"""
This module defines the QThread worker that runs the patch extraction process
in the background, allowing the UI to remain responsive.
"""

import glob
import os
import random

from PyQt5.QtCore import QThread, pyqtSignal

from app.domain.config_model import AppConfig
from app.domain.pairing import list_pairs
from app.domain.patch_extractor import ensure_dir, extract_patches_for_pair
from app.services.logging_bus import LogBus


class ExtractionRunner(QThread):
    """
    A QThread that runs the patch extraction process.

    Emits signals for progress, stats updates, previews, and completion.
    Can be paused, resumed, and cancelled.
    """

    sig_progress = pyqtSignal(int)  # percent
    sig_stats = pyqtSignal(dict)  # cumulative stats
    sig_preview = pyqtSignal(object, object)  # rgb, mask (numpy)
    sig_done = pyqtSignal(bool, str)

    def __init__(self, cfg: AppConfig, logbus: LogBus):
        """
        Initializes the runner.

        Args:
            cfg (AppConfig): The configuration for the extraction job.
            logbus (LogBus): The logging bus for sending log messages to the UI.
        """
        super().__init__()
        self.cfg = cfg
        self.logbus = logbus
        self._pause = False
        self._cancel = False

    def pause(self):
        """Pauses the execution loop."""
        self._pause = True
        self.logbus.log("Paused…")

    def resume(self):
        """Resumes a paused execution."""
        self._pause = False
        self.logbus.log("Resumed.")

    def cancel(self):
        """Requests cancellation of the execution loop."""
        self._cancel = True
        self.logbus.log("Cancel requested…")

    def run(self):
        """
        The main execution method of the thread.

        Iterates through image pairs, extracts patches, and emits signals.
        """
        try:
            random.seed(self.cfg.seed)
            images_dir = os.path.join(self.cfg.data_root,  "Image")
            masks_dir = os.path.join(self.cfg.data_root,  "Mask")
            pairs = list_pairs(images_dir, masks_dir, self.cfg.image_extensions)
            total_pairs = len(pairs)
            if total_pairs == 0:
                self.sig_done.emit(False, "No pairs to process.")
                return

            out_img = os.path.join(self.cfg.patch_root,  "Image")
            out_msk = os.path.join(self.cfg.patch_root,  "Mask")
            if not self.cfg.dry_run:
                ensure_dir(out_img)
                ensure_dir(out_msk)

            processed = 0
            patches_total = 0
            self.logbus.log(f"Starting on {total_pairs} pairs…")

            for ip, mp in pairs:
                if self._cancel:
                    self.sig_done.emit(False, "Cancelled.")
                    return
                while self._pause:
                    self.msleep(100)

                if self.cfg.dry_run:
                    # In a dry run, we can't know the stats without processing,
                    # but we can simulate the loop.
                    stats = {"total_coords": -1, "kept": -1, "coverage_mean": -1.0}
                    img, msk = None, None
                    kept = 0
                else:
                    c, stats, img, msk = extract_patches_for_pair(
                        ip,
                        mp,
                        out_img,
                        out_msk,
                        self.cfg.patch_size,
                        self.cfg.stride,
                        self.cfg.min_mask_ratio,
                        self.cfg.max_patches_per_image,
                        self.cfg.save_format,
                        include_borders=self.cfg.include_borders,
                        apply_ratio=self.cfg.apply_min_mask_ratio,
                    )
                    kept = c
                    patches_total += c

                processed += 1
                pct = int(100 * processed / total_pairs)
                self.sig_progress.emit(pct)
                self.sig_stats.emit(
                    {
                        "images": len(glob.glob(os.path.join(images_dir, "*"))),
                        "pairs": total_pairs,
                        "processed": processed,
                        "patches_total": patches_total,
                        "kept_last": kept,
                    }
                )
                if img is not None and msk is not None:
                    self.sig_preview.emit(img, msk)
                self.logbus.log(
                    f"Processed {os.path.basename(ip)} → kept {kept} patches"
                )

            self.sig_done.emit(True, f"Done. Total patches: {patches_total}")
        except Exception as e:
            self.logbus.log(f"<span style='color:#c00'>An error occurred: {e}</span>")
            self.sig_done.emit(False, f"Error: {e}")
