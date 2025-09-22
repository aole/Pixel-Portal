import configparser
from pathlib import Path

import pytest

from portal.core.document import Document
from portal.core.services.document_service import DocumentService, QFileDialog


class DummyApp:
    def __init__(self, directory: Path):
        self.document = Document(8, 8)
        self.last_directory = str(directory)
        self.config = configparser.ConfigParser()
        self.config.add_section("General")
        self.is_dirty = True
        self.updated_title = False
        self.main_window = None

    def update_main_window_title(self) -> None:
        self.updated_title = True


@pytest.fixture
def document_service(tmp_path):
    service = DocumentService()
    service.app = DummyApp(tmp_path)
    return service


def test_save_document_as_updates_state(monkeypatch, document_service, tmp_path):
    target = tmp_path / "sprite"

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "PNG (*.png)"),
    )

    document_service.save_document_as()

    expected_path = target.with_suffix(".png")
    app = document_service.app

    assert app.document.file_path == str(expected_path)
    assert expected_path.exists()
    assert app.is_dirty is False
    assert app.updated_title is True
    assert app.last_directory == str(tmp_path)
    assert app.config.get("General", "last_directory") == str(tmp_path)


def test_save_document_uses_existing_path(monkeypatch, document_service, tmp_path):
    existing = tmp_path / "existing.png"
    document_service.app.document.file_path = str(existing)

    save_as_calls = []
    monkeypatch.setattr(document_service, "save_document_as", lambda: save_as_calls.append(True))

    document_service.save_document()

    assert not save_as_calls
    assert existing.exists()
    assert document_service.app.is_dirty is False
    assert document_service.app.updated_title is True


@pytest.mark.parametrize(
    "selected_filter, expected_extension",
    [
        ("Pixel Portal Document (*.aole)", ".aole"),
        ("TIFF Files (*.tif *.tiff)", ".tiff"),
        ("All Supported Files (*.aole *.png *.jpg *.bmp *.tif *.tiff)", None),
        ("All Files (*)", None),
    ],
)
def test_extract_extension_hint_handles_multi_extension_filters(
    document_service, selected_filter, expected_extension
):
    assert document_service._extract_extension_hint(selected_filter) == expected_extension
