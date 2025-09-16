from configparser import ConfigParser

from PySide6.QtGui import QColor

from portal.core.document import Document
from portal.core.document_controller import DocumentController


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
    assert document.layer_manager is document.frame_manager.frames[1].layer_manager

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
    red_again = document.render().pixelColor(0, 0)
    assert red_again == QColor("red")


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


class _StubSettings:
    def __init__(self):
        self.config = ConfigParser()
        if not self.config.has_section("General"):
            self.config.add_section("General")
        self._last_directory = ""

    @property
    def last_directory(self):
        return self._last_directory

    @last_directory.setter
    def last_directory(self, value):
        self._last_directory = value


class _StubDocumentService:
    def __init__(self):
        self.app = None


class _StubClipboardService:
    def __init__(self, document_service):
        self.document_service = document_service
        self.app = None


def _make_controller():
    settings = _StubSettings()
    document_service = _StubDocumentService()
    clipboard_service = _StubClipboardService(document_service)
    return DocumentController(
        settings,
        document_service=document_service,
        clipboard_service=clipboard_service,
    )


def test_undo_removes_added_frame():
    controller = _make_controller()
    original_frame = controller.document.frame_manager.frames[0]

    controller.add_frame()
    assert len(controller.document.frame_manager.frames) == 2
    assert controller.document.frame_manager.active_frame_index == 1
    new_frame = controller.document.frame_manager.frames[1]

    controller.undo()
    assert len(controller.document.frame_manager.frames) == 1
    assert controller.document.frame_manager.frames[0] is original_frame
    assert controller.document.frame_manager.active_frame_index == 0

    controller.redo()
    assert len(controller.document.frame_manager.frames) == 2
    assert controller.document.frame_manager.frames[1] is new_frame
    assert controller.document.frame_manager.active_frame_index == 1


def test_undo_removes_duplicate_frame():
    controller = _make_controller()
    original_frame = controller.document.frame_manager.frames[0]

    controller.duplicate_frame()
    assert len(controller.document.frame_manager.frames) == 2
    assert controller.document.frame_manager.active_frame_index == 1
    duplicate_frame = controller.document.frame_manager.frames[1]

    controller.undo()
    assert len(controller.document.frame_manager.frames) == 1
    assert controller.document.frame_manager.frames[0] is original_frame
    assert controller.document.frame_manager.active_frame_index == 0

    controller.redo()
    assert len(controller.document.frame_manager.frames) == 2
    assert controller.document.frame_manager.frames[1] is duplicate_frame
    assert controller.document.frame_manager.active_frame_index == 1
