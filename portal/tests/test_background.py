import pytest
from PySide6.QtGui import QColor
from portal.background import Background

def test_background_creation_checkered():
    bg = Background()
    assert bg.is_checkered is True
    assert bg.color is None

def test_background_creation_with_color():
    color = QColor("red")
    bg = Background(color)
    assert bg.is_checkered is False
    assert bg.color == color
