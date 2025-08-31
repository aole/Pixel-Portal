import pytest
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QRect
from portal.document import Document
import os

@pytest.fixture
def document():
    """Returns a Document with two layers."""
    doc = Document(100, 100)
    doc.layer_manager.add_layer("Layer 2")
    # Fill layers with some content for rendering tests
    layer1 = doc.layer_manager.layers[0]
    layer2 = doc.layer_manager.layers[1]
    layer1.image.fill(QColor(255, 0, 0, 128))  # Semi-transparent red
    layer2.image.fill(QColor(0, 0, 255, 128))  # Semi-transparent blue
    return doc

def test_clone(document):
    """Test that a deep copy of the document is created."""
    clone = document.clone()

    # Check that it's a new object
    assert clone is not document

    # Check that the properties are the same
    assert clone.width == document.width
    assert clone.height == document.height

    # Check that the layer manager is also a clone
    assert clone.layer_manager is not document.layer_manager
    assert len(clone.layer_manager.layers) == len(document.layer_manager.layers)

    # Check that the layers are clones
    for i in range(len(clone.layer_manager.layers)):
        assert clone.layer_manager.layers[i] is not document.layer_manager.layers[i]
        assert clone.layer_manager.layers[i].image.constBits() == document.layer_manager.layers[i].image.constBits()

def test_render(document):
    """Test that all visible layers are correctly composited into a single image."""
    rendered_image = document.render()

    # The expected color is a blend of semi-transparent red and semi-transparent blue
    # This is a simplified check. A more accurate check would involve calculating the exact blended color.
    # For now, we'll just check that it's not the color of either layer or the background.
    pixel_color = rendered_image.pixelColor(50, 50)
    assert pixel_color != QColor(255, 0, 0, 128)
    assert pixel_color != QColor(0, 0, 255, 128)
    assert pixel_color != QColor(0, 0, 0, 0)

    # Test with one layer hidden
    document.layer_manager.layers[0].visible = False
    rendered_image = document.render()
    pixel_color = rendered_image.pixelColor(50, 50)
    assert pixel_color == QColor(0, 0, 255, 128)

def test_save_load_tiff(document):
    """Test that a document with multiple layers can be saved and loaded as a TIFF file."""
    filepath = "test.tiff"
    document.save_tiff(filepath)

    loaded_document = Document.load_tiff(filepath)

    assert loaded_document.width == document.width
    assert loaded_document.height == document.height
    assert len(loaded_document.layer_manager.layers) == len(document.layer_manager.layers)

    for i in range(len(document.layer_manager.layers)):
        original_layer = document.layer_manager.layers[i]
        loaded_layer = loaded_document.layer_manager.layers[i]
        assert original_layer.name == loaded_layer.name
        assert original_layer.visible == loaded_layer.visible
        assert original_layer.opacity == loaded_layer.opacity
        assert original_layer.image.constBits() == loaded_layer.image.constBits()

    os.remove(filepath)

def test_flip_horizontal_vertical(document):
    """Test that all layers in the document are flipped correctly."""
    # Create a non-symmetrical image on each layer
    for layer in document.layer_manager.layers:
        layer.image.fill(QColor(0, 0, 0, 0))
        layer.image.setPixelColor(0, 0, QColor("red"))
        layer.image.setPixelColor(99, 99, QColor("blue"))

    document.flip_horizontal()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(99, 0) == QColor("red")
        assert layer.image.pixelColor(0, 99) == QColor("blue")

    document.flip_vertical()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(99, 99) == QColor("red")
        assert layer.image.pixelColor(0, 0) == QColor("blue")

def test_resize(document):
    """Test that all layers in the document are resized correctly."""
    new_width = 200
    new_height = 200
    document.resize(new_width, new_height, "nearest")

    assert document.width == new_width
    assert document.height == new_height
    for layer in document.layer_manager.layers:
        assert layer.image.width() == new_width
        assert layer.image.height() == new_height

def test_crop(document):
    """Test that all layers in the document are cropped correctly."""
    crop_rect = QRect(10, 10, 50, 50)
    document.crop(crop_rect)

    assert document.width == crop_rect.width()
    assert document.height == crop_rect.height()
    for layer in document.layer_manager.layers:
        assert layer.image.width() == crop_rect.width()
        assert layer.image.height() == crop_rect.height()
