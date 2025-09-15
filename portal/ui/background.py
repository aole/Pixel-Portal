from enum import Enum

from PySide6.QtGui import QColor


class BackgroundImageMode(Enum):
    """Available display modes for background images."""

    STRETCH = "stretch"
    FIT = "fit"
    FILL = "fill"
    CENTER = "center"


class Background:
    def __init__(self, color=None, image_path=None, image_mode=None):
        self.color = color
        self.image_path = image_path
        if image_mode is not None and not isinstance(image_mode, BackgroundImageMode):
            try:
                image_mode = BackgroundImageMode(image_mode)
            except ValueError:
                image_mode = None
        self.image_mode = image_mode

    @property
    def is_checkered(self):
        return self.color is None and self.image_path is None
