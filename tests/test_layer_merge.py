from __future__ import annotations

from PySide6.QtGui import QColor

from portal.commands.layer_commands import MergeLayerDownCommand
from portal.core.document import Document
from portal.core.key import Key
from portal.core.layer import Layer


def _build_layer(width: int, height: int, name: str, frames: list[tuple[int, QColor]]) -> Layer:
    keys: list[Key] = []
    for frame, color in frames:
        key = Key(width, height, frame_number=frame)
        key.image.fill(color)
        keys.append(key)
    return Layer(width, height, name, keys=keys)


def _prepare_document() -> Document:
    document = Document(1, 1)
    layer_manager = document.layer_manager
    bottom = _build_layer(
        document.width,
        document.height,
        "Bottom",
        [(0, QColor("green")), (10, QColor("blue"))],
    )
    top = _build_layer(
        document.width,
        document.height,
        "Top",
        [(0, QColor("red")), (5, QColor("yellow"))],
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
