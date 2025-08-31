import pytest
from portal.layer_manager import LayerManager

@pytest.fixture
def layer_manager():
    """Returns a LayerManager instance."""
    return LayerManager(100, 100)

def test_add_layer(layer_manager):
    """Test that a new layer is added to the top of the stack."""
    initial_layer_count = len(layer_manager.layers)
    layer_manager.add_layer("New Layer")
    assert len(layer_manager.layers) == initial_layer_count + 1
    assert layer_manager.layers[-1].name == "New Layer"
    assert layer_manager.active_layer_index == initial_layer_count
