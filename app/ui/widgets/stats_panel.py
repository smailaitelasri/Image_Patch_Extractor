# =============================
# app/ui/widgets/stats_panel.py
# =============================
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class StatsPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        self.lbl = QLabel("Stats: —")
        lay.addWidget(self.lbl)

    def update_stats(self, d: dict):
        # d keys: images, pairs, patches_total, kept_last, coverage_hist (optional)
        text = []
        for k in ["images", "pairs", "processed", "patches_total", "kept_last"]:
            if k in d:
                text.append(f"{k}: {d[k]}")
        self.lbl.setText("\n".join(text) if text else "Stats: —")
