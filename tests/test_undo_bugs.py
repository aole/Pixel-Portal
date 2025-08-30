import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QImage, QColor, QPainterPath
import pytest

from portal.ui import MainWindow
from portal.app import App

@pytest.fixture
def app_and_window(qtbot):
    """Pytest fixture to create an App and a MainWindow."""
    app = App()
    window = MainWindow(app)
    qtbot.addWidget(window)
    # Start with a document
    app.new_document(100, 100)
    return app, window, window.canvas

from PySide6.QtTest import QTest


def test_undo_redo_mirror_bug(app_and_window, qtbot):
    """
    Tests that redoing a command uses the mirror settings from when the command
    was created, not the current mirror settings.
    """
    app, window, canvas = app_and_window

    # 1. Ensure mirror is off and draw a line
    app.set_mirror_x(False)
    app.set_mirror_y(False)
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(20, 20))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 2. Get the rendered image
    drawn_image = app.document.render()
    assert drawn_image.pixelColor(15, 15) != QColor(Qt.transparent)
    assert drawn_image.pixelColor(85, 15) == QColor(Qt.transparent) # Check mirrored pixel

    # 3. Turn on mirroring, then undo and redo
    app.set_mirror_x(True)
    app.undo()
    app.redo()

    # 4. Get the redone image and check
    redone_image = app.document.render()

    # 5. The redone image should be the same as the original, without mirroring
    assert redone_image.constBits() == drawn_image.constBits()
    assert redone_image.pixelColor(15, 15) != QColor(Qt.transparent)
    assert redone_image.pixelColor(85, 15) == QColor(Qt.transparent) # Mirrored pixel should NOT be drawn

def test_undo_redo_selection_bug(app_and_window, qtbot):
    """
    Tests that a drawing command is correctly clipped to the selection,
    both on initial execution and on redo.
    """
    app, window, canvas = app_and_window

    # 1. Create a selection
    selection_path = QPainterPath()
    selection_path.addRect(QRect(25, 25, 50, 50))
    canvas.selection_shape = selection_path

    # 2. Draw a line that goes through the selection
    start_pos = canvas.get_canvas_coords(QPoint(10, 50))
    end_pos = canvas.get_canvas_coords(QPoint(90, 50))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 3. Check that the line is clipped
    drawn_image = app.document.render()
    assert drawn_image.pixelColor(20, 50) == QColor(Qt.transparent) # Outside
    assert drawn_image.pixelColor(50, 50) != QColor(Qt.transparent) # Inside
    assert drawn_image.pixelColor(80, 50) == QColor(Qt.transparent) # Outside

    # 4. Undo and Redo
    app.undo()
    app.redo()
    redone_image = app.document.render()

    # 5. The redone image should be the same as the original, still clipped
    assert redone_image.constBits() == drawn_image.constBits()
    assert redone_image.pixelColor(20, 50) == QColor(Qt.transparent)
    assert redone_image.pixelColor(50, 50) != QColor(Qt.transparent)
    assert redone_image.pixelColor(80, 50) == QColor(Qt.transparent)
