from PySide6.QtGui import QColor


class Background:
    def __init__(self, color=None):
        self.color = color

    @property
    def is_checkered(self):
        return self.color is None
