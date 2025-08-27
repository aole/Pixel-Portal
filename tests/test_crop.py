import pytest
from PySide6.QtGui import QPainterPath
from PySide6.QtCore import QRect
from portal.app import App
from portal.ui import MainWindow

def test_crop_to_selection(qtbot):
    """Test the crop to selection functionality."""
    app = App()
    window = MainWindow(app)
    app.set_window(window)

    # Original document size
    assert app.document.width == 64
    assert app.document.height == 64

    # Create a selection
    selection_path = QPainterPath()
    selection_rect = QRect(10, 10, 20, 20)
    selection_path.addRect(selection_rect)
    window.canvas.selection_shape = selection_path

    # Crop to selection
    app.crop_to_selection()

    # Check that the document has been cropped
    assert app.document.width == 20
    assert app.document.height == 20

    # Check that the selection has been cleared
    assert window.canvas.selection_shape is None
