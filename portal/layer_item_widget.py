from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class LayerItemWidget(QWidget):
    def __init__(self, layer):
        super().__init__()
        self.layer = layer

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedWidth(32)
        self.thumbnail.setFixedHeight(32)
        self.layout.addWidget(self.thumbnail)

        self.label = QLabel(layer.name)
        self.layout.addWidget(self.label)

        self.update_thumbnail()
        self.layer.on_image_change.connect(self.update_thumbnail)

    def update_thumbnail(self):
        scaled_image = self.layer.image.scaled(32, 32)
        pixmap = QPixmap.fromImage(scaled_image)
        self.thumbnail.setPixmap(pixmap)
