from .document import Document
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor


class App(QObject):
    tool_changed = Signal(str)
    pen_color_changed = Signal(QColor)

    def __init__(self):
        super().__init__()
        self.window = None
        self.document = Document(64, 64)
        self.tool = "Pen"
        self.pen_color = QColor("black")

    def set_window(self, window):
        self.window = window

    def set_tool(self, tool):
        self.tool = tool
        self.tool_changed.emit(self.tool)

    def set_pen_color(self, color_hex):
        self.pen_color = QColor(color_hex)
        self.pen_color_changed.emit(self.pen_color)

    def new_document(self, width, height):
        self.document = Document(width, height)

    def exit(self):
        if self.window:
            self.window.close()
