import pytest
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainterPath

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


def test_rectangle_select_tool(app_and_window, qtbot):
    """
    Tests that the rectangle select tool creates a selection correctly.
    """
    app, window, canvas = app_and_window

    # 1. Select the rectangle select tool
    app.set_tool("Select Rectangle")

    # 2. Draw a rectangle
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(90, 90))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 3. Check that the selection is created
    assert canvas.selection_shape is not None
    expected_rect = QRect(10, 10, 81, 81)
    assert canvas.selection_shape.boundingRect().toRect() == expected_rect
