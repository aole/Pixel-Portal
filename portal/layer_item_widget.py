from PySide6.QtCore import Signal, Qt, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QStackedWidget


class NameLabel(QLabel):
    doubleClicked = Signal()

    def __init__(self, text):
        super().__init__(text)

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()


class EditableLabel(QWidget):
    name_changed = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.label = NameLabel(text)
        self.edit = QLineEdit(text)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.label)
        self.stack.addWidget(self.edit)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.stack)
        self.setLayout(self.layout)

        self.label.doubleClicked.connect(self.edit_name)
        self.edit.editingFinished.connect(self.finish_edit)

    def edit_name(self):
        self.stack.setCurrentWidget(self.edit)
        self.edit.setFocus()
        self.edit.selectAll()

    def finish_edit(self):
        self.stack.setCurrentWidget(self.label)
        new_name = self.edit.text()
        self.label.setText(new_name)
        self.name_changed.emit(new_name)

    def setText(self, text):
        self.label.setText(text)
        self.edit.setText(text)

    def text(self):
        return self.label.text()


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class LayerItemWidget(QWidget):
    visibility_toggled = Signal()

    def __init__(self, layer):
        super().__init__()
        self.layer = layer

        self.pixmap_visible = QPixmap("icons/layervisible.png").scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_invisible = QPixmap("icons/layerinvisible.png").scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        self.visibility_icon = ClickableLabel()
        self.visibility_icon.setFixedWidth(16)
        self.visibility_icon.setFixedHeight(16)
        self.visibility_icon.clicked.connect(self.on_visibility_clicked)
        self.layout.addWidget(self.visibility_icon)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedWidth(64)
        self.thumbnail.setFixedHeight(64)
        self.layout.addWidget(self.thumbnail)

        self.label = EditableLabel(self.layer.name)
        self.label.name_changed.connect(self.on_name_changed)
        self.layout.addWidget(self.label)

        self.update_thumbnail()
        self.update_visibility_icon()
        self.layer.on_image_change.connect(self.update_thumbnail)
        self.layer.visibility_changed.connect(self.update_visibility_icon)
        self.layer.name_changed.connect(self.label.setText)

    def on_name_changed(self, new_name):
        self.layer.name = new_name

    def update_thumbnail(self):
        # The size of the thumbnail label
        label_size = self.thumbnail.size()
        width = label_size.width()
        height = label_size.height()

        # Create a new pixmap to draw on
        bordered_pixmap = QPixmap(label_size)
        bordered_pixmap.fill(Qt.GlobalColor.transparent)

        # Create a painter
        painter = QPainter(bordered_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw white border
        painter.setPen(QColor("white"))
        painter.drawRect(0, 0, width - 1, height - 1)

        # Draw black border
        painter.setPen(QColor("black"))
        painter.drawRect(1, 1, width - 3, height - 3)

        # Calculate padding
        padding_x = int(width * 0.05)
        padding_y = int(height * 0.05)

        # The area for the image, inside the borders and padding
        image_rect = bordered_pixmap.rect().adjusted(2 + padding_x, 2 + padding_y, -2 - padding_x, -2 - padding_y)

        # Scale the layer image to fit inside the image_rect, keeping aspect ratio
        scaled_image = self.layer.image.scaled(
            image_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        pixmap_to_draw = QPixmap.fromImage(scaled_image)

        # Center the pixmap in the image_rect
        draw_rect = QRect(
            image_rect.left(),
            image_rect.top(),
            pixmap_to_draw.width(),
            pixmap_to_draw.height()
        )
        draw_rect.moveCenter(image_rect.center())

        painter.drawPixmap(draw_rect, pixmap_to_draw)

        painter.end()

        self.thumbnail.setPixmap(bordered_pixmap)

    def update_visibility_icon(self):
        if self.layer.visible:
            self.visibility_icon.setPixmap(self.pixmap_visible)
        else:
            self.visibility_icon.setPixmap(self.pixmap_invisible)

    def on_visibility_clicked(self):
        self.visibility_toggled.emit()
