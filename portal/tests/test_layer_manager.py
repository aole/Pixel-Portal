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


def test_remove_layer(layer_manager):
    """Test that the layer at the given index is removed."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    initial_layer_count = len(layer_manager.layers)
    layer_to_remove_index = 1
    layer_manager.remove_layer(layer_to_remove_index)
    assert len(layer_manager.layers) == initial_layer_count - 1
    assert layer_manager.active_layer_index == 1


def test_select_layer(layer_manager):
    """Test that the layer at the given index is selected as the active one."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_select_index = 1
    layer_manager.select_layer(layer_to_select_index)
    assert layer_manager.active_layer_index == layer_to_select_index


def test_move_layer_up(layer_manager):
    """Test that the layer at the given index is moved up one step in the stack."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_move_index = 1
    layer_to_move = layer_manager.layers[layer_to_move_index]
    layer_manager.move_layer_up(layer_to_move_index)
    assert layer_manager.layers[layer_to_move_index + 1] == layer_to_move


def test_move_layer_down(layer_manager):
    """Test that the layer at the given index is moved down one step in the stack."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_move_index = 2
    layer_to_move = layer_manager.layers[layer_to_move_index]
    layer_manager.move_layer_down(layer_to_move_index)
    assert layer_manager.layers[layer_to_move_index - 1] == layer_to_move


def test_merge_layer_down(layer_manager):
    """Test that the layer at the given index is merged with the layer below it."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    initial_layer_count = len(layer_manager.layers)
    layer_to_merge_index = 2
    layer_manager.merge_layer_down(layer_to_merge_index)
    assert len(layer_manager.layers) == initial_layer_count - 1


def test_toggle_visibility(layer_manager):
    """Test that the visibility of the layer at the given index is toggled."""
    layer_manager.add_layer("Layer 1")
    layer_to_toggle_index = 1
    initial_visibility = layer_manager.layers[layer_to_toggle_index].visible
    layer_manager.toggle_visibility(layer_to_toggle_index)
    assert layer_manager.layers[layer_to_toggle_index].visible != initial_visibility


def test_clone(layer_manager):
    """Test that a deep copy of the layer manager is created."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    new_manager = layer_manager.clone()
    assert new_manager is not layer_manager
    assert len(new_manager.layers) == len(layer_manager.layers)
    for i in range(len(new_manager.layers)):
        assert new_manager.layers[i] is not layer_manager.layers[i]
