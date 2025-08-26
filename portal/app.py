from .document import Document
from PySide6.QtGui import QPainterPath
from PySide6.QtCore import QRectF


class App:
    def __init__(self):
        self.window = None
        self.document = Document(64, 64)

    def set_window(self, window):
        self.window = window

    def new_document(self, width, height):
        self.document = Document(width, height)

    def select_all(self):
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self.document.width, self.document.height))
        self.document.set_selection(path)

    def select_none(self):
        self.document.set_selection(QPainterPath())

    def invert_selection(self):
        all_path = QPainterPath()
        all_path.addRect(QRectF(0, 0, self.document.width, self.document.height))
        new_selection = all_path.subtracted(self.document.selection)
        self.document.set_selection(new_selection)

    def exit(self):
        if self.window:
            self.window.close()
