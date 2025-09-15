from PySide6.QtGui import QColor


class Background:
    def __init__(self, color=None, image_path=None):
        self.color = color
        self.image_path = image_path

    @property
    def is_checkered(self):
        return self.color is None and self.image_path is None
