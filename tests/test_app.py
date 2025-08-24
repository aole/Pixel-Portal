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
    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    QTest.mouseMove(canvas, end_pos, -1, Qt.LeftButton)
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    qtbot.wait(100)

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
    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    QTest.mouseMove(canvas, end_pos, -1, Qt.LeftButton)
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 3. Zoom in
    initial_zoom = canvas.zoom

    pos = QPoint(15, 15)
    global_pos = canvas.mapToGlobal(pos)
    angle_delta = QPoint(0, 120)

    event = QWheelEvent(QPointF(pos), QPointF(global_pos), QPoint(0,0), angle_delta, Qt.NoButton, Qt.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    canvas.wheelEvent(event)

    # 4. Check that the zoom level has changed
    assert canvas.zoom > initial_zoom
