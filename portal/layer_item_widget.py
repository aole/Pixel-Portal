from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class LayerItemWidget(QWidget):
    visibility_toggled = Signal()

    def __init__(self, layer):
        super().__init__()
        self.layer = layer

        self.pixmap_visible = QPixmap("icons/layervisible.png")
        self.pixmap_invisible = QPixmap("icons/layerinvisible.png")

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        self.visibility_icon = QLabel()
        self.layout.addWidget(self.visibility_icon)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedWidth(32)
        self.thumbnail.setFixedHeight(32)
        self.layout.addWidget(self.thumbnail)

        self.label = QLabel(layer.name)
        self.layout.addWidget(self.label)

        self.update_thumbnail()
        self.update_visibility_icon()
        self.layer.on_image_change.connect(self.update_thumbnail)
        self.layer.visibility_changed.connect(self.update_visibility_icon)

    def update_thumbnail(self):
        scaled_image = self.layer.image.scaled(32, 32)
        pixmap = QPixmap.fromImage(scaled_image)
        self.thumbnail.setPixmap(pixmap)

    def update_visibility_icon(self):
        if self.layer.visible:
            self.visibility_icon.setPixmap(self.pixmap_visible)
        else:
            self.visibility_icon.setPixmap(self.pixmap_invisible)

    def mousePressEvent(self, event):
        if event.button() == 1:  # Left mouse button
            if self.visibility_icon.geometry().contains(event.pos()):
                self.visibility_toggled.emit()
