from PySide6.QtCore import QRect
from .document import Document

class App:
    def __init__(self):
        self.window = None
        self.document = Document(64, 64)

    def set_window(self, window):
        self.window = window

    def new_document(self, width, height):
        self.document = Document(width, height)

    def select_all(self):
        if self.document:
            self.document.selection = QRect(0, 0, self.document.width, self.document.height)
            if self.window and self.window.canvas:
                self.window.canvas.update()

    def select_none(self):
        if self.document:
            self.document.selection = None
            if self.window and self.window.canvas:
                self.window.canvas.update()

    def exit(self):
        if self.window:
            self.window.close()
