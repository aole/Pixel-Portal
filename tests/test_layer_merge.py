from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor

from portal.commands.layer_commands import MergeLayerDownCommand
from portal.core.command import AddLayerCommand, DrawCommand
from portal.core.document import Document
from portal.core.key import Key
from portal.core.layer import Layer
from portal.core.layer_manager import LayerManager
from portal.core.undo import UndoManager


def _build_layer(
    width: int,
    height: int,
    name: str,
    frames: list[tuple[int, QColor]],
    layer_manager: LayerManager,
) -> Layer:
    keys: list[Key] = []
    for frame, color in frames:
        key = Key(width, height, frame_number=frame)
        key.image.fill(color)
        keys.append(key)
    return Layer(width, height, name, layer_manager=layer_manager, keys=keys)


def _prepare_document() -> Document:
    document = Document(1, 1)
    layer_manager = document.layer_manager
    bottom = _build_layer(
        document.width,
        document.height,
        "Bottom",
        [(0, QColor("green")), (10, QColor("blue"))],
        layer_manager,
    )
    top = _build_layer(
        document.width,
        document.height,
        "Top",
        [(0, QColor("red")), (5, QColor("yellow"))],
        layer_manager,
    )
    layer_manager.layers = [bottom, top]
    for layer in layer_manager.layers:
        layer.attach_to_manager(layer_manager)
    layer_manager.active_layer_index = 1
    return document


def test_merge_layer_down_unions_keyframes(qapp):
    document = _prepare_document()
    layer_manager = document.layer_manager

    layer_manager.merge_layer_down(1)

    assert len(layer_manager.layers) == 1
    merged_layer = layer_manager.layers[0]
    frame_numbers = [key.frame_number for key in merged_layer.keys]
    assert frame_numbers == [0, 5, 10]

    colors = {key.frame_number: key.image.pixelColor(0, 0) for key in merged_layer.keys}
    assert colors[0] == QColor("red")
    assert colors[5] == QColor("yellow")
    assert colors[10] == QColor("blue")


def test_merge_layer_down_command_uses_union_logic(qapp):
    document = _prepare_document()
    layer_manager = document.layer_manager

    command = MergeLayerDownCommand(document, 1)
    command.execute()

    assert len(layer_manager.layers) == 1
    merged_layer = layer_manager.layers[0]
    frame_numbers = [key.frame_number for key in merged_layer.keys]
    assert frame_numbers == [0, 5, 10]

    colors = {key.frame_number: key.image.pixelColor(0, 0) for key in merged_layer.keys}
    assert colors[0] == QColor("red")
    assert colors[5] == QColor("yellow")
    assert colors[10] == QColor("blue")


def _assert_initial_state(layer_manager):
    assert len(layer_manager.layers) == 2

    bottom_layer = layer_manager.layers[0]
    top_layer = layer_manager.layers[1]

    assert bottom_layer.name == "Bottom"
    assert top_layer.name == "Top"

    bottom_frames = {key.frame_number: key for key in bottom_layer.keys}
    top_frames = {key.frame_number: key for key in top_layer.keys}

    assert sorted(bottom_frames) == [0, 10]
    assert sorted(top_frames) == [0, 5]

    assert bottom_frames[0].image.pixelColor(0, 0) == QColor("green")
    assert bottom_frames[10].image.pixelColor(0, 0) == QColor("blue")
    assert top_frames[0].image.pixelColor(0, 0) == QColor("red")
    assert top_frames[5].image.pixelColor(0, 0) == QColor("yellow")


def test_merge_layer_down_command_undo_restores_original_layers(qapp):
    document = _prepare_document()
    layer_manager = document.layer_manager

    command = MergeLayerDownCommand(document, 1)
    command.execute()

    command.undo()

    _assert_initial_state(layer_manager)
    assert layer_manager.active_layer_index == 1


def test_merge_layer_down_command_redo_reapplies_merge(qapp):
    document = _prepare_document()
    layer_manager = document.layer_manager

    command = MergeLayerDownCommand(document, 1)
    command.execute()
    command.undo()

    command.execute()  # redo

    assert len(layer_manager.layers) == 1
    merged_layer = layer_manager.layers[0]
    frame_numbers = [key.frame_number for key in merged_layer.keys]
    assert frame_numbers == [0, 5, 10]

    colors = {key.frame_number: key.image.pixelColor(0, 0) for key in merged_layer.keys}
    assert colors[0] == QColor("red")
    assert colors[5] == QColor("yellow")
    assert colors[10] == QColor("blue")
    assert layer_manager.active_layer_index == 0


def test_merge_layer_down_command_invalid_index_is_noop(qapp):
    document = _prepare_document()
    layer_manager = document.layer_manager

    command = MergeLayerDownCommand(document, 0)
    command.execute()

    _assert_initial_state(layer_manager)
    assert layer_manager.active_layer_index == 1


def test_merge_down_command_preserves_prior_undo_commands(qapp):
    document = Document(2, 2)
    layer_manager = document.layer_manager
    undo_manager = UndoManager()

    base_layer = layer_manager.active_layer

    base_draw = DrawCommand(
        base_layer,
        [QPoint(0, 0)],
        QColor("red"),
        width=1,
        brush_type="Square",
        document=document,
        selection_shape=None,
    )
    base_draw.execute()
    undo_manager.add_command(base_draw)

    add_layer = AddLayerCommand(document, name="Layer 2")
    add_layer.execute()
    undo_manager.add_command(add_layer)

    top_layer = layer_manager.active_layer
    top_draw = DrawCommand(
        top_layer,
        [QPoint(0, 0)],
        QColor("blue"),
        width=1,
        brush_type="Square",
        document=document,
        selection_shape=None,
    )
    top_draw.execute()
    undo_manager.add_command(top_draw)

    merge_command = MergeLayerDownCommand(document, layer_manager.active_layer_index)
    merge_command.execute()
    undo_manager.add_command(merge_command)

    assert len(layer_manager.layers) == 1

    undo_manager.undo()  # Undo merge down
    assert len(layer_manager.layers) == 2
    assert top_layer in layer_manager.layers
    assert top_layer.image.pixelColor(0, 0) == QColor("blue")

    undo_manager.undo()  # Undo drawing on the top layer
    assert top_layer.image.pixelColor(0, 0).alpha() == 0

    undo_manager.undo()  # Undo the added layer
    assert top_layer not in layer_manager.layers
