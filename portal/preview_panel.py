from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class PreviewPanel(QGroupBox):
    def __init__(self, app):
        super().__init__("Preview")
        self.app = app

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.preview_label)

        self.update_preview()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def update_preview(self):
        if self.app.document and self.preview_label.width() > 0:
            image = self.app.document.render()
            pixmap = QPixmap.fromImage(image)
            self.preview_label.setPixmap(pixmap.scaled(
                self.preview_label.width(),
                self.preview_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
