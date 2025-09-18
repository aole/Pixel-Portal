"""Non-modal dialog for configuring the crop rectangle."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class CropDialog(QDialog):
    """Allow users to fine tune crop bounds while the tool is active."""

    rect_changed = Signal(QRect)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Crop Canvas")
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._updating = False

        layout = QVBoxLayout(self)

        description = QLabel(
            "Drag the on-canvas handles or enter exact values to crop or expand "
            "the canvas."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form_layout = QFormLayout()
        self.left_spin = QSpinBox(self)
        self.left_spin.setRange(-65535, 65535)
        self.left_spin.setAccelerated(True)
        form_layout.addRow("Left", self.left_spin)

        self.top_spin = QSpinBox(self)
        self.top_spin.setRange(-65535, 65535)
        self.top_spin.setAccelerated(True)
        form_layout.addRow("Top", self.top_spin)

        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(1, 65535)
        self.width_spin.setAccelerated(True)
        form_layout.addRow("Width", self.width_spin)

        self.height_spin = QSpinBox(self)
        self.height_spin.setRange(1, 65535)
        self.height_spin.setAccelerated(True)
        form_layout.addRow("Height", self.height_spin)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        for spin in (self.left_spin, self.top_spin, self.width_spin, self.height_spin):
            spin.valueChanged.connect(self._emit_rect_changed)

    # ------------------------------------------------------------------
    def set_rect(self, rect: QRect) -> None:
        """Update spin boxes without triggering value-changed callbacks."""

        width = max(1, rect.width())
        height = max(1, rect.height())

        self._updating = True
        try:
            self.left_spin.setValue(rect.x())
            self.top_spin.setValue(rect.y())
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    def _emit_rect_changed(self) -> None:
        if self._updating:
            return

        rect = QRect(
            self.left_spin.value(),
            self.top_spin.value(),
            max(1, self.width_spin.value()),
            max(1, self.height_spin.value()),
        )
        self.rect_changed.emit(rect)


__all__ = ["CropDialog"]
