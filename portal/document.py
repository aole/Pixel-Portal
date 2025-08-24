from PySide6.QtGui import QImage
from PySide6.QtCore import QSize

class Document:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.image = QImage(QSize(width, height), QImage.Format_ARGB32)
        self.image.fill("white")
