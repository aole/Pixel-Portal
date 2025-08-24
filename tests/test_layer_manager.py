import pytest
from PySide6.QtGui import QColor
from portal.layer import Layer
from portal.layer_manager import LayerManager

W, H = 64, 64

@pytest.fixture
def manager():
    """Pytest fixture to create a LayerManager instance."""
    return LayerManager(W, H)

def test_layer_creation():
    """Test the creation of a single Layer."""
    layer = Layer(W, H, "Test Layer")
    assert layer.name == "Test Layer"
    assert layer.visible is True
    assert layer.opacity == 1.0
    assert layer.image.size().width() == W
    assert layer.image.size().height() == H
    assert layer.image.pixelColor(0, 0).alpha() == 0 # Check for transparency

    with pytest.raises(ValueError):
        Layer(W, H, "") # Empty name
    with pytest.raises(ValueError):
        Layer(W, H, None) # Invalid name

def test_manager_initialization(manager):
    """Test that the LayerManager initializes with a default layer."""
    assert len(manager.layers) == 1
    assert manager.layers[0].name == "Background"
    assert manager.active_layer_index == 0
    assert manager.active_layer is manager.layers[0]

def test_add_layer(manager):
    """Test adding a new layer."""
    manager.add_layer("New Layer")
    assert len(manager.layers) == 2
    assert manager.layers[1].name == "New Layer"
    assert manager.active_layer_index == 1
    assert manager.active_layer.name == "New Layer"

def test_remove_layer(manager):
    """Test removing a layer."""
    manager.add_layer("Layer 1")
    manager.add_layer("Layer 2")
    assert len(manager.layers) == 3

    manager.remove_layer(1) # Remove "Layer 1"
    assert len(manager.layers) == 2
    assert manager.layers[0].name == "Background"
    assert manager.layers[1].name == "Layer 2"
    assert manager.active_layer_index == 1 # Active layer was 2, now at index 1

    # Test removing the last layer raises an error
    manager.remove_layer(1)
    with pytest.raises(ValueError):
        manager.remove_layer(0)

def test_remove_invalid_layer(manager):
    """Test removing a layer with an invalid index."""
    with pytest.raises(IndexError):
        manager.remove_layer(5)

def test_select_layer(manager):
    """Test selecting the active layer."""
    manager.add_layer("Layer 1")
    manager.add_layer("Layer 2")

    manager.select_layer(0)
    assert manager.active_layer_index == 0
    assert manager.active_layer.name == "Background"

    manager.select_layer(2)
    assert manager.active_layer_index == 2
    assert manager.active_layer.name == "Layer 2"

    with pytest.raises(IndexError):
        manager.select_layer(3)

def test_move_layer_up(manager):
    """Test moving a layer up in the stack."""
    manager.add_layer("Layer 1")
    manager.add_layer("Layer 2") # Order: [BG, L1, L2], Active: L2 (idx 2)

    manager.select_layer(1) # Select L1
    assert manager.active_layer_index == 1

    manager.move_layer_up(1) # Move L1 up -> [BG, L2, L1]
    assert manager.layers[1].name == "Layer 2"
    assert manager.layers[2].name == "Layer 1"
    assert manager.active_layer_index == 2 # Active layer (L1) moved up

    manager.move_layer_up(2) # Try to move top layer up (should do nothing)
    assert manager.layers[2].name == "Layer 1"

def test_move_layer_down(manager):
    """Test moving a layer down in the stack."""
    manager.add_layer("Layer 1") # Order: [BG, L1], Active: L1 (idx 1)

    manager.move_layer_down(1) # Move L1 down -> [L1, BG]
    assert manager.layers[0].name == "Layer 1"
    assert manager.layers[1].name == "Background"
    assert manager.active_layer_index == 0 # Active layer (L1) moved down

    manager.move_layer_down(0) # Try to move bottom layer down (should do nothing)
    assert manager.layers[0].name == "Layer 1"

def test_merge_layer_down(qtbot):
    """Test merging a layer down, verifying the image content."""
    manager = LayerManager(1, 1)
    manager.add_layer("Top Layer")

    # Set pixel colors on each layer
    red = QColor("red")
    blue = QColor("blue")
    manager.layers[0].image.setPixelColor(0, 0, blue) # Background layer
    manager.layers[1].image.setPixelColor(0, 0, red)  # Top layer

    manager.merge_layer_down(1) # Merge "Top Layer" down to "Background"

    assert len(manager.layers) == 1
    merged_color = manager.layers[0].image.pixelColor(0, 0)
    assert merged_color == red

    with pytest.raises(IndexError):
        manager.merge_layer_down(0) # Cannot merge bottom layer

def test_merge_with_opacity(qtbot):
    """Test merging a semi-transparent layer."""
    manager = LayerManager(1, 1)
    manager.add_layer("Top Layer")

    manager.layers[0].image.fill(QColor("white"))
    manager.layers[1].image.fill(QColor(255, 0, 0, 128)) # 50% transparent red
    manager.layers[1].opacity = 0.5

    manager.merge_layer_down(1)

    assert len(manager.layers) == 1
    merged_color = manager.layers[0].image.pixelColor(0, 0)
    # Merging a semi-transparent red (255,0,0,128) with 0.5 opacity
    # onto a white background (255,255,255).
    # Effective alpha = 0.5 * (128/255) approx 0.25
    # R = 255 * 0.25 + 255 * (1-0.25) = 255
    # G = 0 * 0.25 + 255 * (1-0.25) = 191.25
    # B = 0 * 0.25 + 255 * (1-0.25) = 191.25
    assert merged_color.red() == 255
    assert merged_color.green() == 191
    assert merged_color.blue() == 191

def test_toggle_visibility(manager):
    """Test toggling a layer's visibility."""
    assert manager.layers[0].visible is True
    manager.toggle_visibility(0)
    assert manager.layers[0].visible is False
    manager.toggle_visibility(0)
    assert manager.layers[0].visible is True

    with pytest.raises(IndexError):
        manager.toggle_visibility(1)
