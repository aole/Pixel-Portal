from PySide6.QtCore import Signal, Qt, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QSlider,
    QSizePolicy,
)


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
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            return
        super().mouseReleaseEvent(event)


class LayerItemWidget(QWidget):
    visibility_toggled = Signal()
    onion_skin_toggled = Signal()
    # Emitted continuously as the slider moves
    opacity_preview_changed = Signal(int)
    # Emitted when the slider is released: (old_value, new_value)
    opacity_changed = Signal(int, int)

    def __init__(self, layer):
        super().__init__()
        self.layer = layer
        self._start_value = int(self.layer.opacity * 100)

        self.pixmap_visible = QPixmap("icons/layervisible.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_invisible = QPixmap("icons/layerinvisible.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_onion_enabled = QPixmap("icons/skinon.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_onion_disabled = QPixmap("icons/skinoff.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        icon_container = QWidget()
        icon_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(4)
        icon_layout.setAlignment(Qt.AlignCenter)

        self.visibility_icon = ClickableLabel()
        self.visibility_icon.setFixedSize(24, 24)
        self.visibility_icon.setAlignment(Qt.AlignCenter)
        self.visibility_icon.clicked.connect(self.on_visibility_clicked)
        icon_layout.addWidget(self.visibility_icon, alignment=Qt.AlignCenter)

        self.onion_icon = ClickableLabel()
        self.onion_icon.setFixedSize(24, 24)
        self.onion_icon.setToolTip("Toggle onion skin for this layer")
        self.onion_icon.clicked.connect(self.on_onion_clicked)
        self.onion_icon.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(self.onion_icon, alignment=Qt.AlignCenter)
        self.layout.addWidget(icon_container, alignment=Qt.AlignVCenter)

        thumbnail_container = QWidget()
        thumbnail_layout = QHBoxLayout(thumbnail_container)
        padding = 5
        thumbnail_layout.setContentsMargins(padding, padding, padding, padding)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedWidth(64)
        self.thumbnail.setFixedHeight(64)
        thumbnail_layout.addWidget(self.thumbnail)
        self.layout.addWidget(thumbnail_container)

        # Container for opacity controls and name
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Opacity row: percentage label + slider
        opacity_row = QHBoxLayout()
        opacity_row.setContentsMargins(0, 0, 0, 0)
        self.opacity_label = QLabel(f"{int(self.layer.opacity * 100)}%")
        opacity_row.addWidget(self.opacity_label)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.layer.opacity * 100))
        self.opacity_slider.setTracking(True)
        self.opacity_slider.setFixedHeight(22)
        self.opacity_slider.setStyleSheet(
            "QSlider::handle:horizontal { width: 16px; height: 16px; }"
        )
        self.opacity_slider.sliderPressed.connect(self.on_opacity_slider_pressed)
        self.opacity_slider.valueChanged.connect(self.on_opacity_slider_value_changed)
        self.opacity_slider.sliderReleased.connect(self.on_opacity_slider_released)
        opacity_row.addWidget(self.opacity_slider)
        info_layout.addLayout(opacity_row)

        # Layer name below the opacity controls
        self.label = EditableLabel(self.layer.name)
        self.label.name_changed.connect(self.on_name_changed)
        info_layout.addWidget(self.label)

        self.layout.addWidget(info_container)

        self.update_thumbnail()
        self.update_visibility_icon()
        self.update_onion_icon()
        self.layer.on_image_change.connect(self.update_thumbnail)
        self.layer.visibility_changed.connect(self.update_visibility_icon)
        self.layer.onion_skin_changed.connect(self.update_onion_icon)
        self.layer.name_changed.connect(self.label.setText)

    def on_name_changed(self, new_name):
        self.layer.name = new_name

    def on_opacity_slider_pressed(self):
        self._start_value = self.opacity_slider.value()

    def on_opacity_slider_value_changed(self, value):
        self.opacity_label.setText(f"{value}%")
        self.opacity_preview_changed.emit(value)

    def on_opacity_slider_released(self):
        value = self.opacity_slider.value()
        self.opacity_changed.emit(self._start_value, value)

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

        # Draw black border
        painter.setPen(QColor("black"))
        painter.drawRect(0, 0, width - 1, height - 1)

        # Draw white border
        painter.setPen(QColor("white"))
        painter.drawRect(1, 1, width - 3, height - 3)

        # The area for the image, inside the borders
        image_rect = bordered_pixmap.rect().adjusted(2, 2, -2, -2)

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

    def update_onion_icon(self, _enabled=None):
        if getattr(self.layer, "onion_skin_enabled", False):
            self.onion_icon.setPixmap(self.pixmap_onion_enabled)
        else:
            self.onion_icon.setPixmap(self.pixmap_onion_disabled)

    def on_onion_clicked(self):
        self.onion_skin_toggled.emit()
