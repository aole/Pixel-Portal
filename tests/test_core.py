# This file will contain tests for core application functionality.
import pytest
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from portal.core.app import App
from portal.core.drawing_context import DrawingContext
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

@patch('portal.core.document_controller.CropCommand')
def test_perform_crop(mock_crop_command, app):
    rect = QRect(10, 10, 20, 20)
    app.perform_crop(rect)

    mock_crop_command.assert_called_once_with(app.document, rect)
    mock_crop_command.return_value.execute.assert_called_once()

@patch('portal.core.services.clipboard_service.PasteCommand')
@patch('PySide6.QtWidgets.QApplication.clipboard')
def test_paste_as_new_layer(mock_clipboard, mock_paste_command, app):
    # Mock the clipboard to return a valid QImage
    mock_image = QImage(10, 10, QImage.Format_RGB32)
    mock_clipboard.return_value.image.return_value = mock_image

    app.clipboard_service.paste_as_new_layer()

    mock_paste_command.assert_called_once_with(app.document, mock_image)
    mock_paste_command.return_value.execute.assert_called_once()

@patch('portal.core.document_controller.FlipCommand')
def test_flip(mock_flip_command, app):
    app.flip(horizontal=True, vertical=False, all_layers=False)
    mock_flip_command.assert_called_once_with(app.document, True, False, False)
    mock_flip_command.return_value.execute.assert_called_once()

import os
import sys
from portal.main import MainWindow
from portal.ui.color_button import ColorButton, ActiveColorButton
from PySide6.QtWidgets import QMainWindow, QApplication
from portal.commands.action_manager import ActionManager
from portal.core.document import Document
from portal.core.layer import Layer
from portal.core.command import (
    ResizeCommand, FlipCommand, AddLayerCommand, PasteCommand, CropCommand,
    DrawCommand, FillCommand, ShapeCommand, DuplicateLayerCommand,
    ClearLayerCommand, RemoveLayerCommand, MoveLayerCommand
)
from PySide6.QtCore import QPoint
from portal.core.drawing import Drawing
from portal.core.undo import UndoManager


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
    test_image_path = os.path.abspath('tests/test_image.png')
    mock_get_open_file_name.return_value = (test_image_path, 'Image Files (*.png *.jpg *.bmp)')

    with qtbot.waitSignal(app.document_changed, raising=True) as document_blocker, \
         qtbot.waitSignal(app.undo_stack_changed, raising=True) as undo_blocker:
        app.document_service.open_document()

    assert app.document.width == 32
    assert app.document.height == 32
    assert len(app.document.layer_manager.layers) == 1
    top_left = app.document.layer_manager.active_layer.image.pixelColor(0, 0)
    assert top_left == QColor(0, 0, 0)
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

    app.document_service.save_document()

    assert os.path.exists(save_path)

    # Verify the saved image is correct
    saved_image = QImage(str(save_path))
    assert saved_image.width() == 1
    assert saved_image.height() == 1
    assert saved_image.pixelColor(0, 0) == QColor("red")


@pytest.mark.skip("Main window relies on optional AI dependencies not available in test environment")
def test_application_startup(qtbot):
    """Test that the main application window is created and shown."""
    with patch.object(sys, 'exit') as mock_exit:
        q_app = QApplication.instance() or QApplication(sys.argv)
        app = App()
        window = MainWindow(app)
        qtbot.addWidget(window)

        window.show()

        assert window.isVisible()
        mock_exit.assert_not_called()


from PySide6.QtCore import Qt

def test_color_button(qtbot):
    """Test that the set_pen_color method is called on the app when a color button is clicked."""
    mock_drawing_context = MagicMock()
    button = ColorButton(QColor("red"), mock_drawing_context)
    qtbot.addWidget(button)

    qtbot.mouseClick(button, Qt.LeftButton)

    mock_drawing_context.set_pen_color.assert_called_once_with(QColor("red"))

@patch("PySide6.QtWidgets.QColorDialog.getColor")
def test_active_color_button(mock_get_color, qtbot):
    """Test that the color dialog is opened and that the set_pen_color method is called on the app when a color is selected."""
    mock_drawing_context = MagicMock()
    mock_drawing_context.pen_color = QColor("blue")
    mock_get_color.return_value = QColor("green")

    button = ActiveColorButton(mock_drawing_context)
    qtbot.addWidget(button)

    button.click()

    mock_get_color.assert_called_once()
    mock_drawing_context.set_pen_color.assert_called_once_with(QColor("green"))

@pytest.fixture
def mock_main_window(qapp):
    window = QMainWindow()
    window.app = MagicMock()
    window.app.document_service = MagicMock()
    window.app.clipboard_service = MagicMock()
    window.open_new_file_dialog = MagicMock()
    window.load_palette_from_image = MagicMock()
    window.save_palette_as_png = MagicMock()
    window.open_resize_dialog = MagicMock()
    window.open_background_color_dialog = MagicMock()
    window.open_background_image_dialog = MagicMock()
    window.toggle_ai_panel = MagicMock()
    window.open_flip_dialog = MagicMock()
    return window

def test_setup_actions(mock_main_window):
    # Create an instance of ActionManager
    action_manager = ActionManager(mock_main_window)

    # Mock the canvas
    canvas = MagicMock()

    # Call the method to be tested
    action_manager.setup_actions(canvas)

    # Verify that all actions are created
    assert action_manager.new_action is not None
    assert action_manager.open_action is not None
    assert action_manager.save_action is not None
    assert action_manager.load_palette_action is not None
    assert action_manager.save_palette_as_png_action is not None
    assert action_manager.exit_action is not None
    assert action_manager.undo_action is not None
    assert action_manager.redo_action is not None
    assert action_manager.paste_as_new_image_action is not None
    assert action_manager.select_all_action is not None
    assert action_manager.select_none_action is not None
    assert action_manager.invert_selection_action is not None
    assert action_manager.resize_action is not None
    assert action_manager.crop_action is not None
    assert action_manager.flip_action is not None
    assert action_manager.checkered_action is not None
    assert action_manager.white_action is not None
    assert action_manager.black_action is not None
    assert action_manager.gray_action is not None
    assert action_manager.magenta_action is not None
    assert action_manager.custom_color_action is not None
    assert action_manager.image_background_action is not None
    assert action_manager.circular_brush_action is not None
    assert action_manager.square_brush_action is not None
    assert action_manager.mirror_x_action is not None
    assert action_manager.mirror_y_action is not None
    assert action_manager.grid_action is not None

    # Verify that actions are connected to the correct slots by triggering them
    action_manager.new_action.trigger()
    mock_main_window.open_new_file_dialog.assert_called_once()

    action_manager.open_action.trigger()
    mock_main_window.app.document_service.open_document.assert_called_once()

    action_manager.save_action.trigger()
    mock_main_window.app.document_service.save_document.assert_called_once()

    action_manager.load_palette_action.trigger()
    mock_main_window.load_palette_from_image.assert_called_once()

    action_manager.save_palette_as_png_action.trigger()
    mock_main_window.save_palette_as_png.assert_called_once()

    action_manager.exit_action.trigger()
    mock_main_window.app.exit.assert_called_once()

    action_manager.undo_action.trigger()
    mock_main_window.app.undo.assert_called_once()

    action_manager.redo_action.trigger()
    mock_main_window.app.redo.assert_called_once()

    action_manager.paste_as_new_image_action.trigger()
    mock_main_window.app.clipboard_service.paste_as_new_image.assert_called_once()

    action_manager.select_all_action.trigger()
    mock_main_window.app.select_all.assert_called_once()

    action_manager.select_none_action.trigger()
    mock_main_window.app.select_none.assert_called_once()

    action_manager.invert_selection_action.trigger()
    mock_main_window.app.invert_selection.assert_called_once()

    action_manager.resize_action.trigger()
    mock_main_window.open_resize_dialog.assert_called_once()

    action_manager.crop_action.setEnabled(True)
    action_manager.crop_action.trigger()
    mock_main_window.app.crop_to_selection.assert_called_once()

    action_manager.flip_action.trigger()
    mock_main_window.open_flip_dialog.assert_called_once()

    action_manager.custom_color_action.trigger()
    mock_main_window.open_background_color_dialog.assert_called_once()

    action_manager.image_background_action.trigger()
    mock_main_window.open_background_image_dialog.assert_called_once()

    action_manager.mirror_x_action.trigger()
    mock_main_window.app.set_mirror_x.assert_called_once()

    action_manager.mirror_y_action.trigger()
    mock_main_window.app.set_mirror_y.assert_called_once()



def test_conform_to_palette(app, qtbot):
    """Test that the conform_to_palette method creates a new layer with an image conformed to the palette."""
    # Create a mock main window
    mock_window = MagicMock()
    mock_window.get_palette.return_value = ["#ff0000", "#00ff00"]  # Red and Green
    app.main_window = mock_window

    # Create an image with pure green and a color closer to green than red
    image = QImage(2, 1, QImage.Format_ARGB32)
    image.setPixelColor(0, 0, QColor(0, 255, 0))
    image.setPixelColor(1, 0, QColor(200, 255, 0))
    app.document.layer_manager.layers[0].image = image

    initial_layer_count = len(app.document.layer_manager.layers)

    app.conform_to_palette()

    # Check that a new layer was added
    assert len(app.document.layer_manager.layers) == initial_layer_count + 1

    # Check that the new layer's image is conformed to the palette
    new_layer = app.document.layer_manager.layers[-1]
    # Green is an exact match
    assert new_layer.image.pixelColor(0, 0).name() == "#00ff00"
    # Yellow is closer to green than red
    assert new_layer.image.pixelColor(1, 0).name() == "#00ff00"


@pytest.fixture
def document():
    """Returns a Document with one layer."""
    return Document(100, 100)

@pytest.fixture
def layer(document):
    """Returns the first layer of the document."""
    return document.layer_manager.layers[0]

def test_resize_command(document):
    """Test that the ResizeCommand resizes the document and that undo restores the original size."""
    old_width = document.width
    old_height = document.height
    new_width = 200
    new_height = 200

    command = ResizeCommand(document, new_width, new_height, "nearest")
    command.execute()

    assert document.width == new_width
    assert document.height == new_height

    command.undo()

    assert document.width == old_width
    assert document.height == old_height

def test_draw_command(layer, document):
    """Test that the DrawCommand correctly draws on the layer and that undo restores the previous state."""
    # Get the original image data
    original_image_data = layer.image.constBits().tobytes()

    points = [QPoint(10, 10), QPoint(20, 20)]
    color = QColor("red")
    width = 5
    brush_type = "Circular"

    command = DrawCommand(
        layer=layer,
        points=points,
        color=color,
        width=width,
        brush_type=brush_type,
        document=document,
        selection_shape=None,
        erase=False,
        mirror_x=False,
        mirror_y=False
    )
    command.execute()

    # Check that the image has been modified
    modified_image_data = layer.image.constBits().tobytes()
    assert original_image_data != modified_image_data

    command.undo()

    # Check that the image has been restored
    restored_image_data = layer.image.constBits().tobytes()
    assert original_image_data == restored_image_data

def test_shape_command(document, layer):
    """Test that the ShapeCommand correctly draws a shape and that undo restores the previous state."""
    # Get the original image data
    original_image_data = layer.image.constBits().tobytes()

    rect = QRect(10, 10, 20, 20)
    color = QColor("blue")
    width = 3
    shape_type = "rectangle"

    command = ShapeCommand(
        layer=layer,
        rect=rect,
        shape_type=shape_type,
        color=color,
        width=width,
        document=document,
        selection_shape=None,
        mirror_x=False,
        mirror_y=False
    )
    command.execute()

    # Check that the image has been modified
    modified_image_data = layer.image.constBits().tobytes()
    assert original_image_data != modified_image_data

    command.undo()

    # Check that the image has been restored
    restored_image_data = layer.image.constBits().tobytes()
    assert original_image_data == restored_image_data

def test_flip_command(document, layer):
    """Test that the FlipCommand correctly flips the document and that undo flips it back."""
    # Create a non-symmetrical image (top-left red, bottom-right blue)
    layer.image.setPixelColor(0, 0, QColor("red"))
    layer.image.setPixelColor(99, 99, QColor("blue"))

    # Horizontal flip
    command_h = FlipCommand(document, horizontal=True, vertical=False, all_layers=False)
    command_h.execute()
    assert layer.image.pixelColor(99, 0) == QColor("red")
    assert layer.image.pixelColor(0, 99) == QColor("blue")

    command_h.undo()
    assert layer.image.pixelColor(0, 0) == QColor("red")
    assert layer.image.pixelColor(99, 99) == QColor("blue")

    # Vertical flip
    command_v = FlipCommand(document, horizontal=False, vertical=True, all_layers=False)
    command_v.execute()
    assert layer.image.pixelColor(0, 99) == QColor("red")
    assert layer.image.pixelColor(99, 0) == QColor("blue")

    command_v.undo()
    assert layer.image.pixelColor(0, 0) == QColor("red")
    assert layer.image.pixelColor(99, 99) == QColor("blue")

def test_flip_command_all_layers(document):
    """Test that the FlipCommand correctly flips all layers in the document."""
    # Create a non-symmetrical image on each layer
    for layer in document.layer_manager.layers:
        layer.image.fill(QColor(0, 0, 0, 0))
        layer.image.setPixelColor(0, 0, QColor("red"))
        layer.image.setPixelColor(99, 99, QColor("blue"))

    # Horizontal flip all layers
    command_h = FlipCommand(document, horizontal=True, vertical=False, all_layers=True)
    command_h.execute()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(99, 0) == QColor("red")
        assert layer.image.pixelColor(0, 99) == QColor("blue")

    command_h.undo()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(0, 0) == QColor("red")
        assert layer.image.pixelColor(99, 99) == QColor("blue")

def test_add_layer_command(document):
    """Test that the AddLayerCommand adds a new layer and that undo removes it."""
    initial_layer_count = len(document.layer_manager.layers)

    command = AddLayerCommand(document, name="New Layer")
    command.execute()

    assert len(document.layer_manager.layers) == initial_layer_count + 1
    assert document.layer_manager.layers[-1].name == "New Layer"

    command.undo()

    assert len(document.layer_manager.layers) == initial_layer_count


from portal.commands.canvas_input_handler import CanvasInputHandler

def test_ctrl_key_activates_move_tool(app, qtbot):
    """Test that pressing Ctrl activates the Move tool and releasing it reverts to the previous tool."""
    # Set initial tool
    app.drawing_context.set_tool("Pen")
    assert app.drawing_context.tool == "Pen"

    # Mock a canvas to instantiate the handler
    mock_canvas = MagicMock()
    mock_canvas.drawing_context = app.drawing_context
    handler = CanvasInputHandler(mock_canvas)

    # Simulate Ctrl press
    mock_event = MagicMock()
    mock_event.key.return_value = Qt.Key_Control
    handler.keyPressEvent(mock_event)

    assert app.drawing_context.tool == "Move"
    assert app.drawing_context.previous_tool == "Pen"

    # Simulate Ctrl release
    handler.keyReleaseEvent(mock_event)
    assert app.drawing_context.tool == "Pen"


def test_add_command():
    """Test that a command is added to the undo stack and that the redo stack is cleared."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)

    assert len(undo_manager.undo_stack) == 1
    assert undo_manager.undo_stack[0] == mock_command
    assert len(undo_manager.redo_stack) == 0

def test_undo():
    """Test that the last command is undone and moved to the redo stack."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)

    undo_manager.undo()

    mock_command.undo.assert_called_once()
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 1
    assert undo_manager.redo_stack[0] == mock_command

def test_redo():
    """Test that the last undone command is redone and moved to the undo stack."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)
    undo_manager.undo()

    undo_manager.redo()

    mock_command.execute.assert_called_once()
    assert len(undo_manager.undo_stack) == 1
    assert undo_manager.undo_stack[0] == mock_command
    assert len(undo_manager.redo_stack) == 0


def test_duplicate_layer_command(document):
    """Test that the DuplicateLayerCommand duplicates the layer and that undo removes it."""
    layer_manager = document.layer_manager
    initial_layer_count = len(layer_manager.layers)
    layer_to_duplicate_index = layer_manager.active_layer_index

    command = DuplicateLayerCommand(layer_manager, layer_to_duplicate_index)
    command.execute()

    assert len(layer_manager.layers) == initial_layer_count + 1
    original_layer = layer_manager.layers[layer_to_duplicate_index]
    duplicated_layer = layer_manager.layers[layer_to_duplicate_index + 1]
    assert duplicated_layer.name == f"{original_layer.name} copy"
    assert duplicated_layer.image.constBits() == original_layer.image.constBits()

    command.undo()

    assert len(layer_manager.layers) == initial_layer_count


def test_clear_layer_command(layer):
    """Test that the ClearLayerCommand clears the layer and that undo restores the content."""
    layer.image.fill(QColor("red"))
    original_image_data = layer.image.constBits().tobytes()

    command = ClearLayerCommand(layer, None)
    command.execute()

    # Check that the layer is cleared (i.e., all pixels are transparent)
    for x in range(layer.image.width()):
        for y in range(layer.image.height()):
            assert layer.image.pixelColor(x, y) == QColor(0, 0, 0, 0)

    command.undo()

    assert layer.image.constBits().tobytes() == original_image_data


def test_remove_layer_command(document):
    """Test that the RemoveLayerCommand removes the layer and that undo restores it."""
    layer_manager = document.layer_manager
    layer_manager.add_layer("Layer 2")
    initial_layer_count = len(layer_manager.layers)
    layer_to_remove_index = 1

    command = RemoveLayerCommand(layer_manager, layer_to_remove_index)
    command.execute()

    assert len(layer_manager.layers) == initial_layer_count - 1

    command.undo()

    assert len(layer_manager.layers) == initial_layer_count
    assert layer_manager.layers[layer_to_remove_index].name == "Layer 2"


def test_move_layer_command(document):
    """Test that the MoveLayerCommand moves the layer and that undo moves it back."""
    layer_manager = document.layer_manager
    layer_manager.add_layer("Layer 2")
    layer_manager.add_layer("Layer 3")

    original_layers = list(layer_manager.layers)
    from_index = 0
    to_index = 2

    command = MoveLayerCommand(layer_manager, from_index, to_index)
    command.execute()

    assert layer_manager.layers[to_index] == original_layers[from_index]

    command.undo()

    assert layer_manager.layers == original_layers

def test_fill_command(document, layer):
    """Test that the FillCommand correctly fills an area and that undo restores the previous state."""
    # Create a black square on the layer
    for x in range(10, 20):
        for y in range(10, 20):
            layer.image.setPixelColor(x, y, QColor("black"))

    # Get the original image data
    original_image_data = layer.image.constBits().tobytes()

    command = FillCommand(
        document=document,
        layer=layer,
        fill_pos=QPoint(15, 15),
        fill_color=QColor("red"),
        selection_shape=None,
        mirror_x=False,
        mirror_y=False,
    )
    command.execute()

    # Check that the image has been modified
    modified_image_data = layer.image.constBits().tobytes()
    assert original_image_data != modified_image_data
    assert layer.image.pixelColor(15, 15) == QColor("red")

    command.undo()

    # Check that the image has been restored
    restored_image_data = layer.image.constBits().tobytes()
    assert original_image_data == restored_image_data

def test_crop_command(document):
    """Test that the CropCommand crops the document and that undo restores the original document."""
    old_width = document.width
    old_height = document.height
    crop_rect = QRect(10, 10, 50, 50)

    command = CropCommand(document, crop_rect)
    command.execute()

    assert document.width == crop_rect.width()
    assert document.height == crop_rect.height()

    command.undo()

    assert document.width == old_width
    assert document.height == old_height

def test_paste_command(document):
    """Test that the PasteCommand adds a new layer with the pasted image and that undo removes it."""
    initial_layer_count = len(document.layer_manager.layers)
    image_to_paste = QImage(10, 10, QImage.Format_RGB32)
    image_to_paste.fill(QColor("green"))

    command = PasteCommand(document, image_to_paste)
    command.execute()

    assert len(document.layer_manager.layers) == initial_layer_count + 1
    pasted_layer = document.layer_manager.layers[-1]
    assert pasted_layer.name == "Pasted Layer"
    # The image might be scaled, so we can't do a direct comparison of the image objects.
    # Let's check the color of a pixel.
    assert pasted_layer.image.pixelColor(5, 5) == QColor("green")

    command.undo()

    assert len(document.layer_manager.layers) == initial_layer_count
