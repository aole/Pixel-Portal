from .document import Document
from PySide6.QtCore import QObject, Signal

class App(QObject):
    tool_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.window = None
        self.document = Document(64, 64)
        self.tool = "Pen"

    def set_window(self, window):
        self.window = window

    def set_tool(self, tool):
        self.tool = tool
        self.tool_changed.emit(self.tool)

    def new_document(self, width, height):
        self.document = Document(width, height)

    def exit(self):
        if self.window:
            self.window.close()
