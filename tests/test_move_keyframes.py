from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from portal.core.document_controller import DocumentController
from portal.core.key import Key


def _make_controller():
    settings = SimpleNamespace(animation_fps=12.0, config=None, last_directory="")
    return DocumentController(settings, document_service=MagicMock(), clipboard_service=MagicMock())


def _collect_frames(layer):
    return [key.frame_number for key in layer.keys]


def _append_key(layer, frame_number: int) -> Key:
    width = layer.image.width()
    height = layer.image.height()
    key = Key(width, height, frame_number=frame_number)
    layer._register_key(key)
    layer.keys.append(key)
    layer.keys.sort(key=lambda item: item.frame_number)
    return key


@pytest.mark.usefixtures("qapp")
def test_move_keyframes_shifts_frames():
    controller = _make_controller()
    layer = controller.document.layer_manager.active_layer

    layer.keys[0].frame_number = 0
    _append_key(layer, 4)
    _append_key(layer, 7)

    controller.move_keyframes((0, 4), 2)

    assert _collect_frames(layer) == [2, 6, 7]

    controller.undo()
    assert _collect_frames(layer) == [0, 4, 7]


@pytest.mark.usefixtures("qapp")
def test_move_keyframes_overwrites_conflicting_target():
    controller = _make_controller()
    layer = controller.document.layer_manager.active_layer

    layer.keys[0].frame_number = 0
    existing = _append_key(layer, 5)
    moving = _append_key(layer, 2)

    controller.move_keyframes((2,), 3)

    frames = _collect_frames(layer)
    assert frames == [0, 5]
    assert moving in layer.keys
    assert existing not in layer.keys

    controller.undo()
    frames = _collect_frames(layer)
    assert sorted(frames) == [0, 2, 5]
    assert existing in layer.keys


@pytest.mark.usefixtures("qapp")
def test_delete_keyframes_removes_selection():
    controller = _make_controller()
    layer = controller.document.layer_manager.active_layer

    layer.keys[0].frame_number = 0
    removed_key = _append_key(layer, 3)
    _append_key(layer, 6)

    controller.remove_keyframes((3,))

    assert _collect_frames(layer) == [0, 6]
    assert removed_key not in layer.keys

    controller.undo()
    assert _collect_frames(layer) == [0, 3, 6]
    assert removed_key in layer.keys

    controller.redo()
    assert _collect_frames(layer) == [0, 6]


@pytest.mark.usefixtures("qapp")
def test_delete_keyframes_keeps_at_least_one_key():
    controller = _make_controller()
    layer = controller.document.layer_manager.active_layer

    initial_frames = tuple(_collect_frames(layer))

    controller.remove_keyframes(initial_frames)

    assert _collect_frames(layer) == list(initial_frames)
