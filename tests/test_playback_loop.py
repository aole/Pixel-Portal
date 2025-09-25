from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from portal.core.document_controller import DocumentController
from portal.core.document import Document
from portal.ui.preview_panel import NullAnimationPlayer, PreviewPanel


@pytest.fixture
def document_controller():
    settings = SimpleNamespace(animation_fps=12.0, config=None, last_directory="")
    controller = DocumentController(
        settings,
        document_service=MagicMock(),
        clipboard_service=MagicMock(),
    )
    return controller


def test_document_controller_loop_range_clamping(document_controller):
    document_controller.set_playback_loop_range(-5, 0)
    assert document_controller.playback_loop_range == (0, 1)

    document_controller.set_playback_loop_range(3, 3)
    assert document_controller.playback_loop_range == (3, 4)

    document_controller.set_playback_loop_range(4, 9)
    assert document_controller.playback_loop_range == (4, 9)


def test_null_animation_player_loops_within_window(qtbot):
    player = NullAnimationPlayer()
    player.set_loop_range(2, 5)
    player.set_current_frame(2)

    captured = []
    player.frame_changed.connect(captured.append)

    player.play()
    player._timer.stop()

    for _ in range(5):
        player._advance_frame()

    assert captured == [3, 4, 5, 2, 3]

    player.pause()
    qtbot.wait(0)


def test_preview_panel_updates_document_frame(qtbot):
    document = Document(2, 2)

    class StubApp:
        def __init__(self, doc: Document) -> None:
            self.document = doc
            self.selected_frames: list[int] = []

        def select_frame(self, frame: int) -> None:
            self.selected_frames.append(frame)
            self.document.layer_manager.set_current_frame(frame)

    stub_app = StubApp(document)
    panel = PreviewPanel(stub_app)
    qtbot.addWidget(panel)

    panel._on_preview_frame_changed(1)
    assert stub_app.selected_frames == [1]
    assert document.layer_manager.current_frame == 1

    panel._on_preview_frame_changed(1)
    assert stub_app.selected_frames == [1]
