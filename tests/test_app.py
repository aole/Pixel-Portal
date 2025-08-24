import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from portal.ui import MainWindow
from portal.app import App
from PySide6.QtGui import QImage, QWheelEvent, QColor

def test_draw_and_test(qtbot):
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    canvas = window.canvas
    qtbot.addWidget(window)

    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Draw a line
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)
    canvas.draw_line_for_test(start_pos, end_pos)

    # 3. Check that the image has changed
    pixel_color = app.document.image.pixelColor(15, 15)
    assert pixel_color == QColor(Qt.black)

def test_draw_zoom_and_test(qtbot):
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    canvas = window.canvas
    qtbot.addWidget(window)

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

def test_undo_redo_integration(qtbot):
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    canvas = window.canvas
    qtbot.addWidget(window)

    # 1. Start with a fresh document and get the initial state
    app.new_document(32, 32)
    initial_image = app.document.image.copy()

    # 2. Draw a line using the actual mouse events
    # We can't easily simulate a drag, so we'll simulate the outcome
    # of a drawing action:
    # - A temp image is created
    # - A line is drawn on it
    # - It's copied back
    # - An undo state is added

    # Let's use the test helper and then manually add an undo state
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)
    canvas.draw_line_for_test(start_pos, end_pos)
    drawn_image = app.document.image.copy()
    app.add_undo_state() # Manually add the state like mouseRelease would

    # 3. Check that the image has changed
    assert app.document.image.pixel(15, 15) != initial_image.pixel(15, 15)

    # 4. Undo the drawing
    app.undo()
    assert app.document.image.constBits() == initial_image.constBits()

    # 5. Redo the drawing
    app.redo()
    assert app.document.image.constBits() == drawn_image.constBits()
