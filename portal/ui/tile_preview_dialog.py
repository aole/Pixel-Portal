from PySide6.QtWidgets import QDialog, QLabel, QSpinBox, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt


class TilePreviewDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Tile Preview")

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(3)
        self.cols_spin.valueChanged.connect(self.update_preview)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setValue(3)
        self.rows_spin.valueChanged.connect(self.update_preview)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Columns:"))
        controls_layout.addWidget(self.cols_spin)
        controls_layout.addWidget(QLabel("Rows:"))
        controls_layout.addWidget(self.rows_spin)

        layout = QVBoxLayout(self)
        layout.addLayout(controls_layout)
        layout.addWidget(self.preview_label)

        self.app.document_changed.connect(self.update_preview)
        if parent and hasattr(parent, "canvas"):
            parent.canvas.canvas_updated.connect(self.update_preview)

        self.update_preview()

    def update_preview(self):
        if not self.app.document:
            return

        image = self.app.document.render()
        cols = self.cols_spin.value()
        rows = self.rows_spin.value()
        width = image.width() * cols
        height = image.height() * rows

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        for y in range(rows):
            for x in range(cols):
                painter.drawImage(x * image.width(), y * image.height(), image)
        painter.end()

        self.preview_label.setPixmap(pixmap)
        self.preview_label.setFixedSize(pixmap.size())
        self.adjustSize()
