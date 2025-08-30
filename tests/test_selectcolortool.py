import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter

from portal.app import App
from portal.ui import MainWindow


@pytest.fixture
def app_and_window(qtbot):
    """Pytest fixture to create an App and a MainWindow."""
    app = App()
    window = MainWindow(app)
    qtbot.addWidget(window)
    # Start with a document
    app.new_document(100, 100)
    return app, window, window.canvas


def test_color_select_tool(app_and_window, qtbot):
    """
    Tests that the color select tool creates a selection correctly.
    """
    app, window, canvas = app_and_window

    # 1. Draw something to select
    painter = QPainter(app.document.layer_manager.active_layer.image)
    painter.fillRect(10, 10, 30, 30, QColor(Qt.red))
    painter.fillRect(50, 50, 30, 30, QColor(Qt.blue))
    painter.end()

    # 2. Select the color select tool
    app.set_tool("Select Color")

    # 3. Click on the red square
    pos = canvas.get_canvas_coords(QPoint(25, 25))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, pos)

    # 4. Check that the selection is created
    assert canvas.selection_shape is not None
    assert not canvas.selection_shape.isEmpty()
    assert canvas.selection_shape.contains(QPoint(25, 25))
    assert not canvas.selection_shape.contains(QPoint(65, 65))
