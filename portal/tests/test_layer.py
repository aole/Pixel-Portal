import pytest
from PySide6.QtGui import QColor
from portal.layer import Layer

@pytest.fixture
def layer():
    """Returns a Layer instance."""
    return Layer(100, 100, "Test Layer")

def test_layer_creation(layer):
    """Test that a layer is created with the correct name, visibility, and opacity."""
    assert layer.name == "Test Layer"
    assert layer.visible is True
    assert layer.opacity == 1.0
    assert layer.image.width() == 100
    assert layer.image.height() == 100

def test_clear(layer):
    """Test that the layer is filled with a transparent color."""
    layer.image.fill(QColor("blue"))
    layer.clear()
    for x in range(layer.image.width()):
        for y in range(layer.image.height()):
            assert layer.image.pixelColor(x, y) == QColor(0, 0, 0, 0)

def test_clone(layer):
    """Test that a deep copy of the layer is created."""
    layer.image.fill(QColor("red"))
    clone = layer.clone()

    assert clone is not layer
    assert clone.name == layer.name
    assert clone.visible == layer.visible
    assert clone.opacity == layer.opacity
    assert clone.image.constBits() == layer.image.constBits()

    # Modify the clone and check that the original is not affected
    clone.name = "Cloned Layer"
    clone.visible = False
    clone.image.fill(QColor("green"))

    assert layer.name == "Test Layer"
    assert layer.visible is True
    assert layer.image.pixelColor(50, 50) == QColor("red")
