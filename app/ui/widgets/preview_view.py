# app/ui/widgets/preview_view.py
import numpy as np
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def _ensure_contiguous_rgb(rgb: np.ndarray) -> np.ndarray:
    # Expect HxWx3, uint8, RGB; ensure C-contiguous for Qt
    if rgb.dtype != np.uint8:
        rgb = rgb.astype(np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("RGB must be HxWx3 uint8")
    return np.ascontiguousarray(rgb)


def _ensure_contiguous_gray(mask: np.ndarray) -> np.ndarray:
    # Accept HxW or HxWx1; binarize if needed, ensure uint8
    if mask.ndim == 3 and mask.shape[2] == 1:
        mask = mask[..., 0]

    # If the mask is binary {0,1}, scale it to {0, 255} for visibility
    if mask.max() <= 1.0:
        mask = (mask * 255.0).astype(np.uint8)
    elif mask.dtype != np.uint8:
        mask = np.clip(mask, 0, 255).astype(np.uint8)

    return np.ascontiguousarray(mask)


from PyQt5.QtGui import QPainter


class _ImageView(QGraphicsView):
    """Simple pan/zoom image view with fit-to-view toggle."""

    def __init__(self, title: str):
        super().__init__()
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        ...

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._item = QGraphicsPixmapItem()
        self._scene.addItem(self._item)
        self._fit = True  # start in fit mode
        self._title = QLabel(title)
        self._pix = None

    def title_widget(self) -> QLabel:
        return self._title

    def set_pixmap(self, pm: QPixmap):
        self._pix = pm
        self._item.setPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        if self._fit:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, ev):
        if self._pix is None or self._fit:
            super().wheelEvent(ev)
            return
        
        angle = ev.angleDelta().y()
        if angle == 0:
            return

        factor = 1.25 if angle > 0 else 0.8
        
        # --- THIS IS THE FIX ---
        # Don't zoom out if the image is already smaller than its original size.
        # The 'm11' attribute gives the horizontal scaling factor.
        if factor < 1.0 and self.transform().m11() < 1.0:
            return
        # --------------------

        self.scale(factor, factor)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._fit and self._pix is not None:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def toggle_fit(self, fit: bool = None):
        self._fit = (not self._fit) if fit is None else fit
        if self._pix is not None:
            if self._fit:
                self.setTransform(
                    self.transform().fromScale(1, 1)
                )  # reset scale matrix
                self.resetTransform()
                self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)


class PreviewView(QWidget):
    """
    Two synchronized panes: left = RGB, right = Mask (grayscale).
    - Double-click on a pane toggles Fit-to-View / Free Zoom.
    - Mouse wheel zoom when in Free Zoom.
    - Drag to pan.
    """

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        title = QLabel("Image Preview / Mask Preview")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight:bold; padding:4px 0;")
        root.addWidget(title)

        self.left = _ImageView("Image")
        self.right = _ImageView("Mask")

        # Titles above each pane
        row_titles = QHBoxLayout()
        row_titles.addWidget(self.left.title_widget(), 1, Qt.AlignCenter)
        row_titles.addWidget(self.right.title_widget(), 1, Qt.AlignCenter)
        root.addLayout(row_titles)

        row = QHBoxLayout()
        row.addWidget(self.left, 1)
        row.addWidget(self.right, 1)
        root.addLayout(row, 1)

        # Keep last arrays if needed
        self._rgb = None
        self._msk = None

        # Double-click toggles fit
        self.left.viewport().mouseDoubleClickEvent = self._mk_toggle(self.left)
        self.right.viewport().mouseDoubleClickEvent = self._mk_toggle(self.right)

    def _mk_toggle(self, view: _ImageView):
        def _handler(ev):
            if ev.button() == Qt.LeftButton:
                view.toggle_fit()
            # pass through to default (optional)
            QGraphicsView.mouseDoubleClickEvent(view, ev)

        return _handler

    def show_sample(self, rgb: np.ndarray, msk: np.ndarray):
        self._rgb = rgb
        self._msk = msk

        if rgb is None or msk is None:
            # Show placeholders
            ph = QPixmap(640, 480)
            ph.fill(Qt.darkGray)
            self.left.set_pixmap(ph)
            self.right.set_pixmap(ph)
            return

        # Prepare RGB pixmap
        rgb = _ensure_contiguous_rgb(rgb)
        h, w = rgb.shape[:2]
        qimg_rgb = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pm_rgb = QPixmap.fromImage(qimg_rgb.copy())  # copy to detach from numpy buffer
        self.left.set_pixmap(pm_rgb)

        # Prepare Mask pixmap (grayscale)
        m = _ensure_contiguous_gray(msk)
        if m.shape != (h, w):  # simple guard
            # If size mismatch, resize mask to image
            from PyQt5.QtGui import QImageReader

            m = np.ascontiguousarray(np.array(m))
        qimg_m = QImage(m.data, w, h, w, QImage.Format_Grayscale8)
        pm_m = QPixmap.fromImage(qimg_m.copy())
        self.right.set_pixmap(pm_m)
