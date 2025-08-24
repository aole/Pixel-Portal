import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QEnterEvent, QColor, QMouseEvent
from portal.main import MainWindow
from portal.app import App

@pytest.fixture
def app_with_window(qtbot):
    # Ensure a QApplication instance exists
    q_app = QApplication.instance() or QApplication(sys.argv)

    app = App()
    window = MainWindow(app)
    app.set_window(window)
    window.show()
    qtbot.addWidget(window)

    # Wait for the window to be fully shown and sized
    qtbot.waitExposed(window)

    return app, window

def test_canvas_cursor_visibility(app_with_window, qtbot):
    app, window = app_with_window
    canvas = window.canvas

    # 1. Initial state: cursor should be default arrow
    assert canvas.cursor().shape() == Qt.ArrowCursor

    # 2. Mouse enters canvas: cursor should become blank
    enter_event = QEnterEvent(QPoint(), QPoint(), QPoint())
    QApplication.sendEvent(canvas, enter_event)
    assert canvas.cursor().shape() == Qt.BlankCursor

    # 3. Mouse leaves canvas: cursor should be restored
    canvas.leaveEvent(None)
    assert canvas.cursor().shape() == Qt.ArrowCursor

def test_canvas_cursor_drawing(app_with_window, qtbot):
    app, window = app_with_window
    canvas = window.canvas

    # Enter the canvas first to set the state
    enter_event = QEnterEvent(QPoint(), QPoint(), QPoint())
    QApplication.sendEvent(canvas, enter_event)

    # For this test, we need a predictable background
    solid_bg_color = QColor("blue")
    active_layer = app.document.layer_manager.active_layer
    active_layer.image.fill(solid_bg_color)

    canvas.zoom = 4.0
    app.pen_size = 1

    canvas.update()
    qtbot.wait(10)

    doc_width_scaled = canvas.app.document.width * canvas.zoom
    doc_height_scaled = canvas.app.document.height * canvas.zoom
    doc_canvas_x = (canvas.width() - doc_width_scaled) / 2 + canvas.x_offset
    doc_canvas_y = (canvas.height() - doc_height_scaled) / 2 + canvas.y_offset

    target_doc_pos = QPoint(10.5, 10.5)
    mouse_x = doc_canvas_x + target_doc_pos.x() * canvas.zoom
    mouse_y = doc_canvas_y + target_doc_pos.y() * canvas.zoom

    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(int(mouse_x), int(mouse_y)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    QApplication.sendEvent(canvas, move_event)
    qtbot.wait(10)

    image = canvas.grab().toImage()

    cursor_top_left_x = int(doc_canvas_x + 10 * canvas.zoom)
    cursor_top_left_y = int(doc_canvas_y + 10 * canvas.zoom)

    inside_pixel_color = image.pixelColor(cursor_top_left_x + 1, cursor_top_left_y + 1)
    assert inside_pixel_color == QColor("yellow")

    outside_pixel_color = image.pixelColor(cursor_top_left_x - 1, cursor_top_left_y - 1)
    assert outside_pixel_color == solid_bg_color
