import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from portal.ui import MainWindow
from portal.app import App
from PySide6.QtGui import QColor, QMouseEvent

import pytest

@pytest.fixture
def app_and_window(qtbot):
    """Pytest fixture to create an App and a MainWindow."""
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    window.show()
    qtbot.addWidget(window)
    return app, window, window.canvas

def test_picker_tool_pick_color(app_and_window):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document and fill it with blue
    app.new_document(32, 32)
    blue = QColor("blue")
    app.document.layer_manager.active_layer.image.fill(blue)

    # 2. Get the picker tool
    picker_tool = canvas.tools["Picker"]

    # 3. Call pick_color with a coordinate
    picker_tool.pick_color(QPoint(10, 10))

    # 4. Check that the color has been picked
    assert app.pen_color == blue

def test_picker_tool_switches_back(app_and_window):
    app, window, canvas = app_and_window

    # 1. Set the initial tool to Pen
    app.set_tool("Pen")
    assert app.tool == "Pen"

    # 2. Switch to the Picker tool
    app.set_tool("Picker")
    assert app.tool == "Picker"
    assert app.previous_tool == "Pen"

    # 3. Simulate a mouse release to trigger the tool switch
    picker_tool = canvas.tools["Picker"]
    event = QMouseEvent(QMouseEvent.MouseButtonRelease, QPointF(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    picker_tool.mouseReleaseEvent(event, QPoint(10, 10))

    # 4. Check that the tool has switched back
    assert app.tool == "Pen"
