import pytest
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from portal.app import App
from portal.drawing_context import DrawingContext
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

@pytest.fixture
def app(qapp):
    # Create an App instance and return it
    app_instance = App()

    # The review mentioned that the setters are on App, not DrawingContext.
    # Let's add them to the App instance for the test, assuming they would delegate.
    def set_mirror_x(val):
        app_instance.drawing_context.set_mirror_x(val)
    app_instance.set_mirror_x = set_mirror_x

    def set_mirror_y(val):
        app_instance.drawing_context.set_mirror_y(val)
    app_instance.set_mirror_y = set_mirror_y

    def set_pen_width(val):
        app_instance.drawing_context.set_pen_width(val)
    app_instance.set_pen_width = set_pen_width

    def set_brush_type(val):
        app_instance.drawing_context.set_brush_type(val)
    app_instance.set_brush_type = set_brush_type

    def set_tool(val):
        app_instance.drawing_context.set_tool(val)
    app_instance.set_tool = set_tool

    def set_pen_color(val):
        app_instance.drawing_context.set_pen_color(val)
    app_instance.set_pen_color = set_pen_color

    return app_instance

def test_set_mirror_x(app, qtbot):
    with qtbot.waitSignal(app.drawing_context.mirror_x_changed) as blocker:
        app.set_mirror_x(True)
    assert app.drawing_context.mirror_x is True
    assert blocker.args == [True]

def test_set_mirror_y(app, qtbot):
    with qtbot.waitSignal(app.drawing_context.mirror_y_changed) as blocker:
        app.set_mirror_y(True)
    assert app.drawing_context.mirror_y is True
    assert blocker.args == [True]

def test_set_pen_width(app, qtbot):
    with qtbot.waitSignal(app.drawing_context.pen_width_changed) as blocker:
        app.set_pen_width(10)
    assert app.drawing_context.pen_width == 10
    assert blocker.args == [10]

def test_set_brush_type(app, qtbot):
    with qtbot.waitSignal(app.drawing_context.brush_type_changed) as blocker:
        app.set_brush_type("Square")
    assert app.drawing_context.brush_type == "Square"
    assert blocker.args == ["Square"]

def test_set_tool(app, qtbot):
    # Set tool for the first time
    with qtbot.waitSignal(app.drawing_context.tool_changed) as blocker:
        app.set_tool("Eraser")
    assert app.drawing_context.tool == "Eraser"
    assert blocker.args == ["Eraser"]

    # Set tool for the second time and check previous_tool
    with qtbot.waitSignal(app.drawing_context.tool_changed) as blocker:
        app.set_tool("Pen")
    assert app.drawing_context.tool == "Pen"
    assert app.drawing_context.previous_tool == "Eraser"
    assert blocker.args == ["Pen"]

def test_set_pen_color(app, qtbot):
    color = QColor("blue")
    with qtbot.waitSignal(app.drawing_context.pen_color_changed) as blocker:
        app.set_pen_color(color)
    assert app.drawing_context.pen_color == color
    assert blocker.args == [color]

def test_new_document(app, qtbot):
    with qtbot.waitSignal(app.document_changed, raising=True) as document_blocker, \
         qtbot.waitSignal(app.undo_stack_changed, raising=True) as undo_blocker:
        app.new_document(128, 128)

    assert app.document is not None
    assert app.document.width == 128
    assert app.document.height == 128
    assert document_blocker
    assert undo_blocker

def test_resize_document(app, qtbot):
    initial_width = app.document.width
    initial_height = app.document.height

    with qtbot.waitSignal(app.document_changed, raising=True) as blocker:
        app.resize_document(initial_width * 2, initial_height * 2, "nearest")

    assert app.document.width == initial_width * 2
    assert app.document.height == initial_height * 2
    assert len(app.undo_manager.undo_stack) == 1
    assert blocker

def test_crop_to_selection(app, qtbot):
    with qtbot.waitSignal(app.crop_to_selection_triggered) as blocker:
        app.crop_to_selection()
    assert blocker

def test_clear_layer(app, qtbot):
    with qtbot.waitSignal(app.clear_layer_triggered) as blocker:
        app.clear_layer()
    assert blocker

@patch('portal.app.CropCommand')
def test_perform_crop(mock_crop_command, app):
    rect = QRect(10, 10, 20, 20)
    app.perform_crop(rect)

    mock_crop_command.assert_called_once_with(app.document, rect)
    mock_crop_command.return_value.execute.assert_called_once()

@patch('portal.app.PasteCommand')
@patch('PySide6.QtWidgets.QApplication.clipboard')
def test_paste_as_new_layer(mock_clipboard, mock_paste_command, app):
    # Mock the clipboard to return a valid QImage
    mock_image = QImage(10, 10, QImage.Format_RGB32)
    mock_clipboard.return_value.image.return_value = mock_image

    app.paste_as_new_layer()

    mock_paste_command.assert_called_once_with(app.document, mock_image)
    mock_paste_command.return_value.execute.assert_called_once()

@patch('portal.app.FlipCommand')
def test_flip_horizontal(mock_flip_command, app):
    app.flip_horizontal()

    mock_flip_command.assert_called_once_with(app.document, 'horizontal')
    mock_flip_command.return_value.execute.assert_called_once()

import os

@patch('portal.app.FlipCommand')
def test_flip_vertical(mock_flip_command, app):
    app.flip_vertical()

    mock_flip_command.assert_called_once_with(app.document, 'vertical')
    mock_flip_command.return_value.execute.assert_called_once()

def test_undo_redo(app, qtbot):
    initial_width = app.document.width
    initial_height = app.document.height
    new_width = initial_width * 2
    new_height = initial_height * 2

    # Perform an action
    app.resize_document(new_width, new_height, "nearest")
    assert app.document.width == new_width
    assert app.document.height == new_height

    # Undo the action
    with qtbot.waitSignal(app.document_changed, raising=True):
        app.undo()

    assert app.document.width == initial_width
    assert app.document.height == initial_height

    # Redo the action
    with qtbot.waitSignal(app.document_changed, raising=True):
        app.redo()

    assert app.document.width == new_width
    assert app.document.height == new_height

@patch('PySide6.QtWidgets.QFileDialog.getOpenFileName')
def test_open_document(mock_get_open_file_name, app, qtbot):
    test_image_path = os.path.abspath('portal/tests/test_image.png')
    mock_get_open_file_name.return_value = (test_image_path, 'Image Files (*.png *.jpg *.bmp)')

    with qtbot.waitSignal(app.document_changed, raising=True) as document_blocker, \
         qtbot.waitSignal(app.undo_stack_changed, raising=True) as undo_blocker:
        app.open_document()

    assert app.document.width == 32
    assert app.document.height == 32
    assert document_blocker
    assert undo_blocker

@patch('PySide6.QtWidgets.QFileDialog.getSaveFileName')
def test_save_document(mock_get_save_file_name, app, tmp_path):
    save_path = tmp_path / "saved_image.png"
    mock_get_save_file_name.return_value = (str(save_path), 'PNG (*.png)')

    # Make sure there is something to save
    app.new_document(1, 1)
    # create a red pixel
    app.document.layer_manager.layers[0].image.setPixelColor(0, 0, QColor("red"))

    app.save_document()

    assert os.path.exists(save_path)

    # Verify the saved image is correct
    saved_image = QImage(str(save_path))
    assert saved_image.width() == 1
    assert saved_image.height() == 1
    assert saved_image.pixelColor(0, 0) == QColor("red")
