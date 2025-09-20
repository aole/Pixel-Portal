import pytest

from portal.core.document_controller import DocumentController
from portal.core.settings_controller import SettingsController


class DummyWindow:
    def __init__(self, title: str = "Pixel Portal"):
        self._title = title
        self.canvas = None

    def windowTitle(self):
        return self._title

    def setWindowTitle(self, value: str) -> None:
        self._title = value


@pytest.fixture
def controller(qapp):
    return DocumentController(SettingsController())


def test_window_title_for_unsaved_document(controller):
    window = DummyWindow()
    controller.main_window = window

    assert window.windowTitle() == "Pixel Portal - <unsaved>"


def test_window_title_updates_for_saved_document(tmp_path, controller):
    window = DummyWindow()
    controller.main_window = window

    saved_path = tmp_path / "artwork.aole"
    controller.document.file_path = str(saved_path)
    controller.is_dirty = True

    base_title = controller._base_window_title
    expected_dirty = f"{base_title} - {saved_path.name}*"
    assert window.windowTitle() == expected_dirty

    controller.is_dirty = False
    controller.update_main_window_title()

    expected_clean = f"{base_title} - {saved_path.name}"
    assert window.windowTitle() == expected_clean


def test_window_title_respects_custom_base(tmp_path, qapp):
    controller = DocumentController(SettingsController())
    window = DummyWindow("Pixel Portal Deluxe")
    controller.main_window = window

    controller.document.file_path = str(tmp_path / "scene.png")
    controller.update_main_window_title()

    assert window.windowTitle() == "Pixel Portal Deluxe - scene.png"
