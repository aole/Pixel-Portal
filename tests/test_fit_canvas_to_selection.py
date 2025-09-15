"""Tests for the "Fit canvas to selection" functionality."""

from configparser import ConfigParser
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QColor, QPainterPath, QImage

from portal.core.command import DrawCommand
from portal.core.document_controller import DocumentController
from portal.ui.ui import MainWindow


def create_stub_main_window(selection_shape):
    """Create a minimal stub carrying the attributes used by the slot."""

    canvas = SimpleNamespace(selection_shape=selection_shape, select_none=MagicMock())
    app = SimpleNamespace(perform_crop=MagicMock())
    return SimpleNamespace(canvas=canvas, app=app), canvas, app


class _StubSettings:
    """Provide the minimal settings API consumed by DocumentController."""

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
    """Document service stand-in so controller setup stays lightweight."""

    def __init__(self):
        self.app = None


class _StubClipboardService:
    """Clipboard service stub that only stores controller wiring."""

    def __init__(self, document_service):
        self.document_service = document_service
        self.app = None


def _image_bytes(image):
    """Return a deterministic RGBA snapshot for equality assertions."""

    normalized = image.convertToFormat(QImage.Format_ARGB32)
    width = normalized.width()
    height = normalized.height()
    if width == 0 or height == 0:
        return b""

    pixels = bytearray(width * height * 4)
    index = 0
    for y in range(height):
        for x in range(width):
            color = normalized.pixelColor(x, y)
            pixels[index] = color.red()
            pixels[index + 1] = color.green()
            pixels[index + 2] = color.blue()
            pixels[index + 3] = color.alpha()
            index += 4
    return bytes(pixels)


def test_fit_canvas_to_selection_crops_and_clears_selection():
    """Cropping runs when a selection exists and clears the selection afterwards."""

    selection_path = QPainterPath()
    selection_path.addRect(QRectF(5, 8, 10, 12))
    main_window, canvas, app = create_stub_main_window(selection_path)

    MainWindow.on_crop_to_selection(main_window)

    expected_rect = selection_path.boundingRect().toRect()
    app.perform_crop.assert_called_once_with(expected_rect)
    canvas.select_none.assert_called_once_with()


def test_fit_canvas_to_selection_ignores_missing_selection():
    """Cropping is skipped when there is no active selection."""

    main_window, canvas, app = create_stub_main_window(None)

    MainWindow.on_crop_to_selection(main_window)

    app.perform_crop.assert_not_called()
    canvas.select_none.assert_not_called()


def test_fit_canvas_to_selection_uses_full_selection_bounds():
    """Cropping uses the bounding rectangle of complex selections."""

    selection_path = QPainterPath()
    selection_path.addRect(QRectF(-5.5, -2.25, 12.3, 9.4))
    selection_path.addRect(QRectF(8.1, 6.75, 3.6, 4.8))
    main_window, canvas, app = create_stub_main_window(selection_path)

    MainWindow.on_crop_to_selection(main_window)

    expected_rect = selection_path.boundingRect().toRect()
    actual_rect = app.perform_crop.call_args[0][0]
    assert actual_rect == expected_rect
    canvas.select_none.assert_called_once_with()


def test_fit_canvas_to_selection_undo_restores_previous_states():
    """Undo unwinds post-crop edits back through crop and original drawing."""

    settings = _StubSettings()
    document_service = _StubDocumentService()
    clipboard_service = _StubClipboardService(document_service)
    controller = DocumentController(
        settings,
        document_service=document_service,
        clipboard_service=clipboard_service,
    )

    original_size = (controller.document.width, controller.document.height)
    layer = controller.document.layer_manager.active_layer
    initial_bytes = _image_bytes(layer.image)

    first_stroke = DrawCommand(
        layer=layer,
        points=[QPoint(2, 2), QPoint(12, 12)],
        color=QColor("red"),
        width=4,
        brush_type="Circular",
        document=controller.document,
        selection_shape=None,
    )
    controller.execute_command(first_stroke)
    after_first_draw = _image_bytes(controller.document.layer_manager.active_layer.image)
    assert after_first_draw != initial_bytes

    selection_path = QPainterPath()
    selection_path.addRect(QRectF(0, 0, 16, 16))
    canvas = SimpleNamespace(selection_shape=selection_path, select_none=MagicMock())
    main_window = SimpleNamespace(canvas=canvas, app=controller)
    controller.main_window = main_window

    MainWindow.on_crop_to_selection(main_window)

    canvas.select_none.assert_called_once_with()
    cropped_size = (controller.document.width, controller.document.height)
    assert cropped_size == (16, 16)
    after_crop = _image_bytes(controller.document.layer_manager.active_layer.image)
    assert after_crop != after_first_draw

    second_layer = controller.document.layer_manager.active_layer
    second_stroke = DrawCommand(
        layer=second_layer,
        points=[QPoint(1, 1), QPoint(14, 14)],
        color=QColor("blue"),
        width=2,
        brush_type="Circular",
        document=controller.document,
        selection_shape=None,
    )
    controller.execute_command(second_stroke)
    assert len(controller.undo_manager.undo_stack) == 3

    after_second_draw = _image_bytes(controller.document.layer_manager.active_layer.image)
    assert after_second_draw != after_crop

    controller.undo()
    assert len(controller.undo_manager.undo_stack) == 2
    state_after_last_draw_undo = _image_bytes(controller.document.layer_manager.active_layer.image)
    assert state_after_last_draw_undo == after_crop
    assert (controller.document.width, controller.document.height) == cropped_size

    controller.undo()
    assert len(controller.undo_manager.undo_stack) == 1
    layer_after_crop_undo = controller.document.layer_manager.active_layer
    state_after_crop_undo = _image_bytes(layer_after_crop_undo.image)
    assert state_after_crop_undo == after_first_draw
    assert (controller.document.width, controller.document.height) == original_size

    controller.undo()
    assert len(controller.undo_manager.undo_stack) == 0
    final_state = _image_bytes(controller.document.layer_manager.active_layer.image)
    assert final_state == initial_bytes
    assert len(controller.undo_manager.redo_stack) == 3
