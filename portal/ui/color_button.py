from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Qt


class ColorButton(QPushButton):
    rightClicked = Signal(QColor)

    def __init__(self, color, drawing_context):
        super().__init__()
        self.drawing_context = drawing_context
        self.setFixedSize(24, 24)
        self.clicked.connect(self.on_click)
        self.drawing_context.pen_color_changed.connect(self.update_active_state)
        self.set_color(color)
        self.update_active_state(self.drawing_context.pen_color)

    def set_color(self, color):
        if isinstance(color, QColor):
            self.color = color.name()
        else:
            self.color = color
        self.setToolTip(self.color)
        self.update_active_state(self.drawing_context.pen_color)

    def on_click(self):
        self.drawing_context.set_pen_color(QColor(self.color))

    def contextMenuEvent(self, event):
        self.rightClicked.emit(QColor(self.color))
        event.accept()

    def update_active_state(self, active_color):
        if QColor(self.color) == active_color:
            color = QColor(self.color)
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            border_color = "#000000" if brightness > 128 else "#FFFFFF"
            self.setStyleSheet(f"background-color: {self.color}; border: 2px solid {border_color};")
        else:
            self.setStyleSheet(f"background-color: {self.color}; border: none;")


class ActiveColorButton(QPushButton):
    def __init__(self, drawing_context):
        super().__init__()
        self.drawing_context = drawing_context
        self.setFixedSize(24, 24)
        self.clicked.connect(self.on_click)
        self.update_color(self.drawing_context.pen_color)
        self.drawing_context.pen_color_changed.connect(self.update_color)

    def on_click(self):
        color = QColorDialog.getColor(self.drawing_context.pen_color, self)
        if color.isValid():
            self.drawing_context.set_pen_color(color)

    def update_color(self, color):
        self.setStyleSheet(f"background-color: {color.name()}")
        self.setToolTip(color.name())
