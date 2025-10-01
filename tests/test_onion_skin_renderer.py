import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from portal.core.document import Document
from portal.core.key import Key
from portal.core.renderer import CanvasRenderer
from portal.core.drawing_context import DrawingContext


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _add_key(layer, frame_number, color):
    key = Key(layer.image.width(), layer.image.height(), frame_number=frame_number)
    key.image.fill(color)
    layer._register_key(key)
    layer.keys.append(key)
    return key


def test_onion_skin_shows_prev_and_next_keys_on_active_keyframe(qapp):
    document = Document(4, 4)
    layer_manager = document.layer_manager
    layer = layer_manager.active_layer

    layer.keys[0].frame_number = 0
    layer.keys[0].image.fill(QColor(255, 255, 255, 255))

    current_color = QColor(0, 0, 0, 255)
    _add_key(layer, 5, current_color)
    _add_key(layer, 10, QColor(255, 255, 255, 255))
    layer.keys.sort(key=lambda key: key.frame_number)

    layer_manager.set_current_frame(5)

    class DummyCanvas:
        onion_skin_enabled = True
        onion_skin_prev_frames = 1
        onion_skin_next_frames = 1
        onion_skin_prev_color = QColor(255, 0, 0, 128)
        onion_skin_next_color = QColor(0, 0, 255, 128)
        animation_playback_active = False

    renderer = CanvasRenderer(DummyCanvas(), DrawingContext())

    target = QImage(document.width, document.height, QImage.Format_ARGB32)
    target.fill(current_color)

    before_background = target.pixelColor(0, 0)
    renderer._draw_onion_skin_background(target, document)
    assert target.pixelColor(0, 0) == before_background

    renderer._draw_onion_skin_foreground(target, document)
    result = target.pixelColor(0, 0)

    assert result != before_background
    assert result.red() > before_background.red()
    assert result.blue() > before_background.blue()
