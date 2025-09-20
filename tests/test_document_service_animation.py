from pathlib import Path

import pytest
from PySide6.QtGui import QColor

from portal.core.document import Document
from portal.core.services.document_service import DocumentService


def _create_document_with_transparent_keys(total_frames: int) -> Document:
    document = Document(2, 2)
    frame_manager = document.frame_manager
    frame_manager.ensure_frame(total_frames - 1)

    layer = document.layer_manager.active_layer
    layer.image.fill(0)
    layer.image.setPixelColor(0, 0, QColor(255, 0, 0, 255))
    layer.image.setPixelColor(1, 1, QColor(0, 0, 0, 0))

    layer_uid = layer.uid
    frame_manager.add_layer_key(layer_uid, 3)
    key_layer = frame_manager.frames[3].layer_manager.active_layer
    key_layer.image.fill(0)
    key_layer.image.setPixelColor(0, 0, QColor(0, 255, 0, 255))
    key_layer.image.setPixelColor(1, 0, QColor(0, 0, 255, 128))
    key_layer.image.setPixelColor(1, 1, QColor(0, 0, 0, 0))

    return document


@pytest.mark.parametrize("total_frames", [15])
def test_export_import_roundtrip_preserves_transparency(tmp_path: Path, total_frames: int) -> None:
    document = _create_document_with_transparent_keys(total_frames)
    service = DocumentService()

    target = tmp_path / "animation.gif"
    service._export_animation_file(
        frame_manager=document.frame_manager,
        file_path=str(target),
        format_name="GIF",
        total_frames=total_frames,
        fps_value=12.0,
    )

    frame_entries, imported_total, fps = service._read_animation_frames(str(target))

    assert imported_total == total_frames
    assert pytest.approx(fps, rel=1e-3) == 12.0
    assert len(frame_entries) == 2

    first_frame, first_repeats = frame_entries[0]
    second_frame, second_repeats = frame_entries[1]

    assert first_repeats == 3
    assert second_repeats == total_frames - 3

    assert first_frame.pixelColor(1, 1).alpha() == 0
    assert first_frame.pixelColor(0, 0).red() == 255

    assert second_frame.pixelColor(0, 0).green() == 255
    assert second_frame.pixelColor(1, 0).alpha() == 128
    assert second_frame.pixelColor(1, 1).alpha() == 0
