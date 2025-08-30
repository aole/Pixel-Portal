import pytest
from PySide6.QtGui import QImage, QColor
from portal.document import Document
from portal.layer import Layer
from portal.command import ResizeCommand, FlipCommand, AddLayerCommand, PasteCommand, CropCommand, DrawCommand, FillCommand, ShapeCommand
from PySide6.QtCore import QRect, QPoint
from unittest.mock import Mock
from portal.drawing import Drawing

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
    command_h = FlipCommand(document, 'horizontal')
    command_h.execute()
    assert layer.image.pixelColor(99, 0) == QColor("red")
    assert layer.image.pixelColor(0, 99) == QColor("blue")

    command_h.undo()
    assert layer.image.pixelColor(0, 0) == QColor("red")
    assert layer.image.pixelColor(99, 99) == QColor("blue")

    # Vertical flip
    command_v = FlipCommand(document, 'vertical')
    command_v.execute()
    assert layer.image.pixelColor(0, 99) == QColor("red")
    assert layer.image.pixelColor(99, 0) == QColor("blue")

    command_v.undo()
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
