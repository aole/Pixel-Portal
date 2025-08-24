import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from portal.ui import MainWindow
from portal.app import App
from PySide6.QtGui import QImage, QWheelEvent, QColor

import pytest

@pytest.fixture
def app_and_window(qtbot):
    """Pytest fixture to create an App and a MainWindow."""
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    qtbot.addWidget(window)
    return app, window, window.canvas

def test_draw_and_test(app_and_window):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Draw a line
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)
    canvas.draw_line_for_test(start_pos, end_pos)

    # 3. Check that the image has changed
    pixel_color = app.document.layer_manager.active_layer.image.pixelColor(15, 15)
    assert pixel_color == QColor(Qt.black)

def test_draw_zoom_and_test(app_and_window):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Draw a line
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)
    canvas.draw_line_for_test(start_pos, end_pos)

    # 3. Zoom in
    initial_zoom = canvas.zoom

    pos = QPoint(15, 15)
    global_pos = canvas.mapToGlobal(pos)
    angle_delta = QPoint(0, 120)

    event = QWheelEvent(QPointF(pos), QPointF(global_pos), QPoint(0,0), angle_delta, Qt.NoButton, Qt.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    canvas.wheelEvent(event)

    # 4. Check that the zoom level has changed
    assert canvas.zoom > initial_zoom

def test_undo_redo_integration(app_and_window):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document and get the initial state
    app.new_document(32, 32)
    initial_rendered_image = app.document.render()

    # 2. Draw a line
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)

    # Simulate a mouse press, move, and release to draw
    canvas.draw_line_for_test(start_pos, end_pos)
    app.add_undo_state()

    drawn_rendered_image = app.document.render()

    # 3. Check that the image has changed
    assert drawn_rendered_image.pixel(15, 15) != initial_rendered_image.pixel(15, 15)

    # 4. Undo the drawing
    app.undo()
    undone_rendered_image = app.document.render()
    assert undone_rendered_image.constBits() == initial_rendered_image.constBits()

    # 5. Redo the drawing
    app.redo()
    redone_rendered_image = app.document.render()
    assert redone_rendered_image.constBits() == drawn_rendered_image.constBits()
