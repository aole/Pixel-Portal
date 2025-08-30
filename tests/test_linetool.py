import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor

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


def test_line_tool(app_and_window, qtbot):
    """
    Tests that the line tool draws a line correctly.
    """
    app, window, canvas = app_and_window

    # 1. Select the line tool
    app.set_tool("Line")

    # 2. Draw a line
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(90, 90))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 3. Check that the line is drawn
    drawn_image = app.document.render()
    assert drawn_image.pixelColor(50, 50) == QColor(Qt.black)
    assert drawn_image.pixelColor(10, 10) == QColor(Qt.black)
    assert drawn_image.pixelColor(90, 90) == QColor(Qt.black)
    assert drawn_image.pixelColor(10, 90) == QColor(Qt.transparent)
