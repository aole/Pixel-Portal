from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class PreviewPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        self.layout.addWidget(self.preview_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.update_preview()

    def update_preview(self):
        if self.app.document:
            image = self.app.document.render()
            pixmap = QPixmap.fromImage(image)
            
            # If the image is larger than 128px in width or height, scale it down.
            if pixmap.width() > 128 or pixmap.height() > 128:
                pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.FastTransformation)

            self.preview_label.setPixmap(pixmap)
            self.preview_label.setFixedSize(pixmap.size())
