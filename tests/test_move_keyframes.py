from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from portal.core.document_controller import DocumentController
from portal.core.key import Key
from PySide6.QtGui import QColor


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


@pytest.mark.usefixtures("qapp")
def test_copy_paste_keyframes_creates_new_keys():
    controller = _make_controller()
    layer = controller.document.layer_manager.active_layer

    base_key = layer.keys[0]
    base_key.frame_number = 0
    base_key.image.fill(QColor(10, 20, 30, 255))
    second_key = _append_key(layer, 4)
    _append_key(layer, 8)

    assert controller.copy_keyframes((0, 4)) is True
    assert controller.has_copied_keyframe() is True

    assert controller.paste_keyframes(6) is True

    frames = _collect_frames(layer)
    assert frames == [0, 4, 6, 8, 10]

    pasted_six = next(key for key in layer.keys if key.frame_number == 6)
    pasted_ten = next(key for key in layer.keys if key.frame_number == 10)

    assert pasted_six is not base_key
    assert pasted_six is not second_key
    assert pasted_ten.frame_number == 10

    pasted_six.image.fill(QColor(200, 100, 50, 255))
    assert base_key.image.pixelColor(0, 0) == QColor(10, 20, 30, 255)

    controller.undo()
    assert _collect_frames(layer) == [0, 4, 8]

    controller.redo()
    assert _collect_frames(layer) == [0, 4, 6, 8, 10]


@pytest.mark.usefixtures("qapp")
def test_copy_keyframes_requires_existing_frames():
    controller = _make_controller()

    assert controller.copy_keyframes(()) is False
    assert controller.copy_keyframes((99,)) is False
    assert controller.has_copied_keyframe() is False
    assert controller.paste_keyframes(5) is False

