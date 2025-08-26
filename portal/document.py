from PySide6.QtGui import QImage, QPainterPath
from PySide6.QtCore import QSize, Signal, QObject


class Document(QObject):
    selection_changed = Signal()

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height
        self.image = QImage(QSize(width, height), QImage.Format_ARGB32)
        self.image.fill("white")
        self.selection = QPainterPath()

    def set_selection(self, selection):
        self.selection = selection
        self.selection_changed.emit()
