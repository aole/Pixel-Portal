from PySide6.QtGui import QColor

from portal.core.document import Document
from portal.commands.timeline_commands import (
    AddKeyframeCommand,
    DuplicateKeyframeCommand,
    RemoveKeyframeCommand,
)


def test_document_initializes_with_single_frame():
    document = Document(4, 4)

    assert len(document.frame_manager.frames) == 1
    assert document.frame_manager.active_frame_index == 0
    assert document.layer_manager is document.frame_manager.current_layer_manager


def test_document_add_and_select_frames():
    document = Document(4, 4)
    first_manager = document.layer_manager

    document.add_frame()

    assert len(document.frame_manager.frames) == 2
    assert document.frame_manager.active_frame_index == 1
    assert document.layer_manager is first_manager
    assert document.frame_manager.resolve_key_frame_index() == 0

    document.select_frame(0)
    assert document.layer_manager is first_manager


def test_render_current_frame_tracks_active_frame():
    document = Document(2, 2)
    document.layer_manager.active_layer.image.fill(QColor("red"))

    red_pixel = document.render_current_frame().pixelColor(0, 0)
    assert red_pixel == QColor("red")

    document.add_frame()
    document.layer_manager.active_layer.image.fill(QColor("blue"))

    blue_pixel = document.render_current_frame().pixelColor(0, 0)
    assert blue_pixel == QColor("blue")

    document.select_frame(0)
    blue_again = document.render().pixelColor(0, 0)
    assert blue_again == QColor("blue")


def test_scrubbing_uses_previous_keyframe_state():
    document = Document(2, 2)
    document.layer_manager.active_layer.image.fill(QColor("red"))

    for _ in range(6):
        document.add_frame()

    document.select_frame(3)
    assert document.frame_manager.resolve_key_frame_index() == 0
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    document.select_frame(5)
    document.add_key_frame(5)
    key_layer_manager = document.layer_manager
    assert key_layer_manager is document.frame_manager.frames[5].layer_manager
    assert key_layer_manager is not document.frame_manager.frames[0].layer_manager
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    key_layer_manager.active_layer.image.fill(QColor("blue"))

    document.select_frame(6)
    assert document.frame_manager.resolve_key_frame_index() == 5
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")

    document.select_frame(2)
    assert document.frame_manager.resolve_key_frame_index() == 0
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")


def test_remove_frame_updates_active_index():
    document = Document(2, 2)
    document.add_frame()
    document.select_frame(0)

    document.remove_frame(0)

    assert len(document.frame_manager.frames) == 1
    assert document.frame_manager.active_frame_index == 0
    assert document.layer_manager is document.frame_manager.current_layer_manager


def test_layer_manager_listener_notified_on_frame_change():
    document = Document(3, 3)
    observed = []

    document.add_layer_manager_listener(observed.append)
    assert observed[-1] is document.layer_manager

    document.add_frame()
    assert observed[-1] is document.layer_manager

    document.select_frame(0)
    assert observed[-1] is document.layer_manager

    document.remove_frame(1)
    assert observed[-1] is document.layer_manager


def test_clone_copies_frames_and_layers():
    document = Document(2, 2)
    document.layer_manager.add_layer("Foreground")
    document.layer_manager.active_layer.image.fill(QColor("green"))
    document.add_frame()
    document.layer_manager.add_layer("Second Frame Layer")

    clone = document.clone()

    assert len(clone.frame_manager.frames) == len(document.frame_manager.frames)
    assert clone.frame_manager.active_frame_index == document.frame_manager.active_frame_index

    for original_frame, cloned_frame in zip(document.frame_manager.frames, clone.frame_manager.frames):
        assert cloned_frame is not original_frame
        assert cloned_frame.layer_manager is not original_frame.layer_manager
        assert len(cloned_frame.layer_manager.layers) == len(original_frame.layer_manager.layers)


def test_document_key_frames_follow_frame_removal():
    document = Document(4, 4)
    document.add_frame()
    document.add_key_frame(1)

    assert document.key_frames == [0, 1]

    document.remove_frame(0)

    assert document.key_frames == [0]


def test_add_keyframe_command_supports_undo_redo():
    document = Document(4, 4)
    document.layer_manager.active_layer.image.fill(QColor("red"))
    document.add_frame()

    command = AddKeyframeCommand(document, 1)
    command.execute()

    assert document.key_frames == [0, 1]
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    document.layer_manager.active_layer.image.fill(QColor("blue"))

    document.select_frame(0)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    document.select_frame(1)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")

    command.undo()
    assert document.key_frames == [0]
    document.select_frame(1)
    assert document.frame_manager.resolve_key_frame_index() == 0
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    command.execute()
    assert document.key_frames == [0, 1]
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")


def test_remove_keyframe_command_supports_undo_redo():
    document = Document(4, 4)
    document.layer_manager.active_layer.image.fill(QColor("red"))
    document.add_frame()
    document.add_key_frame(1)
    document.layer_manager.active_layer.image.fill(QColor("blue"))

    command = RemoveKeyframeCommand(document, 1)
    command.execute()

    assert document.key_frames == [0]
    document.select_frame(1)
    assert document.frame_manager.resolve_key_frame_index() == 0
    assert document.render_current_frame().pixelColor(0, 0) == QColor("red")

    command.undo()

    assert document.key_frames == [0, 1]
    document.select_frame(1)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")


def test_duplicate_keyframe_command_supports_undo_redo():
    document = Document(4, 4)
    document.layer_manager.active_layer.image.fill(QColor("red"))
    for _ in range(3):
        document.add_frame()
    document.add_key_frame(2)
    document.layer_manager.active_layer.image.fill(QColor("blue"))

    command = DuplicateKeyframeCommand(document, source_frame=2, target_frame=3)
    command.execute()

    assert document.key_frames == [0, 2, 3]
    document.select_frame(3)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")

    document.layer_manager.active_layer.image.fill(QColor("green"))
    document.select_frame(2)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")

    command.undo()
    assert document.key_frames == [0, 2]
    document.select_frame(3)
    assert document.frame_manager.resolve_key_frame_index() == 2
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")

    command.execute()
    assert document.key_frames == [0, 2, 3]
    document.select_frame(3)
    assert document.render_current_frame().pixelColor(0, 0) == QColor("blue")
