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
    qtbot.addWidget(window)
    return app, window, window.canvas

def test_draw_and_test(app_and_window, qtbot):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Draw a line
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(20, 20))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)


    # 3. Check that the image has changed
    pixel_color = app.document.layer_manager.active_layer.image.pixelColor(15, 15)
    assert pixel_color == QColor(Qt.black)

def test_draw_zoom_and_test(app_and_window, qtbot):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Draw a line
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(20, 20))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    # 3. Zoom in
    initial_zoom = canvas.zoom

    pos = QPoint(15, 15)
    global_pos = canvas.mapToGlobal(pos)
    angle_delta = QPoint(0, 120)

    event = QWheelEvent(QPointF(pos), QPointF(global_pos), QPoint(0,0), angle_delta, Qt.NoButton, Qt.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    canvas.wheelEvent(event)

    # 4. Check that the zoom level has changed
    assert canvas.zoom > initial_zoom

def test_undo_redo_integration(app_and_window, qtbot):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document and get the initial state
    app.new_document(32, 32)
    initial_rendered_image = app.document.render()

    # 2. Draw a line
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(20, 20))

    # Simulate a mouse press, move, and release to draw
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    drawn_rendered_image = app.document.render()

    # 3. Check that the image has changed
    assert drawn_rendered_image.pixel(15, 15) != initial_rendered_image.pixel(15, 15)

    # 4. Undo the drawing
    app.undo()
    undone_rendered_image = app.document.render()
    assert undone_rendered_image.constBits() == initial_rendered_image.constBits()

    # 5. Redo the. drawing
    app.redo()
    redone_rendered_image = app.document.render()
    assert redone_rendered_image.constBits() == drawn_rendered_image.constBits()

def test_erase_and_test(app_and_window, qtbot):
    app, window, canvas = app_and_window

    # 1. Start with a fresh document and fill it with a color
    app.new_document(32, 32)
    app.document.layer_manager.active_layer.image.fill(QColor(Qt.blue))

    # 2. Erase a line
    start_pos = canvas.get_canvas_coords(QPoint(10, 10))
    end_pos = canvas.get_canvas_coords(QPoint(20, 20))
    qtbot.mousePress(canvas, Qt.RightButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.RightButton, Qt.NoModifier, end_pos)


    # 3. Check that the pixels on the erased line are transparent
    pixel_color = app.document.layer_manager.active_layer.image.pixelColor(15, 15)
    assert pixel_color.alpha() == 0


def test_flip_undo_redo(app_and_window, qtbot):
    app, window, canvas = app_and_window
    app.new_document(32, 32)

    # Draw something asymmetric to see the flip
    start_pos = canvas.get_canvas_coords(QPoint(5, 10))
    end_pos = canvas.get_canvas_coords(QPoint(15, 10))
    qtbot.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start_pos)
    qtbot.mouseMove(canvas, end_pos)
    qtbot.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end_pos)

    initial_image = app.document.render()

    # Flip horizontal
    app.flip_horizontal()
    flipped_image = app.document.render()
    assert initial_image.constBits() != flipped_image.constBits()

    # Undo flip
    app.undo()
    undone_image = app.document.render()
    assert initial_image.constBits() == undone_image.constBits()

    # Redo flip
    app.redo()
    redone_image = app.document.render()
    assert flipped_image.constBits() == redone_image.constBits()

    # Undo flip again
    app.undo()

    # Undo draw
    app.undo()

    # Now we should be at the initial empty state
    empty_image = QImage(32, 32, QImage.Format_ARGB32)
    empty_image.fill(Qt.transparent)
    assert app.document.render().constBits() == empty_image.constBits()


def test_open_document_and_duplicate_layer(app_and_window, monkeypatch, tmp_path):
    """
    Tests that after opening a document, UI updates like duplicating a layer work correctly.
    This specifically tests that the `layer_structure_changed` signal is connected.
    """
    app, window, canvas = app_and_window

    # 1. Create a dummy image file to "open"
    dummy_file = tmp_path / "test.png"
    dummy_image = QImage(16, 16, QImage.Format_RGB32)
    dummy_image.fill(Qt.green)
    dummy_image.save(str(dummy_file))

    # 2. Mock the file dialog to return the path to our dummy file
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", lambda *args, **kwargs: (str(dummy_file), "PNG (*.png)"))

    # 3. Call open_document
    app.open_document()

    # 4. Check that the document has been loaded
    assert app.document.width == 16
    assert app.document.height == 16
    assert window.layer_manager_widget.layer_list.count() == 1 # The new document's single layer

    # 5. Duplicate the layer and check if the UI updates
    initial_layer_count = window.layer_manager_widget.layer_list.count()
    window.layer_manager_widget.duplicate_button.click()
    assert window.layer_manager_widget.layer_list.count() == initial_layer_count + 1
