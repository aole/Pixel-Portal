from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from PySide6.QtGui import QColor, QImage

from portal.core.document_controller import DocumentController
from portal.core.document import Document
from portal.core.key import Key
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


def test_preview_panel_does_not_drive_document_frame(qtbot):
    document = Document(2, 2)

    class StubApp:
        def __init__(self, doc: Document) -> None:
            self.document = doc
            self.selected_frames: list[int] = []

        def select_frame(self, frame: int) -> None:  # pragma: no cover - defensive
            self.selected_frames.append(frame)
            self.document.layer_manager.set_current_frame(frame)

    stub_app = StubApp(document)
    panel = PreviewPanel(stub_app)
    qtbot.addWidget(panel)

    panel.preview_player.play()
    panel._on_preview_frame_changed(1)

    assert stub_app.selected_frames == []
    assert document.layer_manager.current_frame == 0
    panel.preview_player.pause()


def test_preview_panel_renders_requested_frame(qtbot):
    document = Document(1, 1)
    layer = document.layer_manager.active_layer
    base_image = QImage(1, 1, QImage.Format_ARGB32)
    base_image.fill(QColor("red"))
    layer.keys[0].image = base_image

    blue_image = QImage(1, 1, QImage.Format_ARGB32)
    blue_image.fill(QColor("blue"))
    layer.keys.append(Key.from_qimage(blue_image, frame_number=3))

    class StubApp:
        def __init__(self, doc: Document) -> None:
            self.document = doc

    stub_app = StubApp(document)
    panel = PreviewPanel(stub_app)
    qtbot.addWidget(panel)
    panel.set_loop_range(0, 4)

    panel.preview_player.play()
    panel._on_preview_frame_changed(3)

    pixmap = panel.preview_label.pixmap()
    assert pixmap is not None
    sampled = pixmap.toImage().pixelColor(0, 0)
    assert sampled == QColor("blue")
    assert document.layer_manager.current_frame == 0
    panel.preview_player.pause()


def test_preview_panel_tracks_document_frame_when_idle(qtbot):
    document = Document(2, 2)

    class StubApp:
        def __init__(self, doc: Document) -> None:
            self.document = doc

    stub_app = StubApp(document)
    panel = PreviewPanel(stub_app)
    qtbot.addWidget(panel)

    document.layer_manager.set_current_frame(2)
    panel.sync_to_document_frame()

    assert panel.preview_player.current_frame == 2


def test_aole_roundtrip_preserves_loop_range(tmp_path, document_controller):
    document = Document(8, 8)
    document.set_playback_loop_range(2, 10)
    archive_path = tmp_path / "loop_range.aole"
    document.save_aole(str(archive_path))

    loaded = Document.load_aole(str(archive_path))
    assert loaded.get_playback_loop_range() == (2, 10)

    document_controller.attach_document(loaded)
    assert document_controller.playback_loop_range == (2, 10)
