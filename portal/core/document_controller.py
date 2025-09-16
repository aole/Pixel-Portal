from PySide6.QtCore import QObject, Signal, Slot, QRect
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QMessageBox

from portal.core.document import Document
from portal.core.undo import UndoManager
from portal.core.drawing_context import DrawingContext
from portal.core.command import (
    AddFrameCommand,
    AddLayerCommand,
    CropCommand,
    DuplicateFrameCommand,
    FlipCommand,
    RemoveFrameCommand,
    ResizeCommand,
)
from portal.commands.layer_commands import RemoveBackgroundCommand
from portal.core.color_utils import find_closest_color
from portal.core.services.document_service import DocumentService
from portal.core.services.clipboard_service import ClipboardService
from portal.core.settings_controller import SettingsController


class DocumentController(QObject):
    """Handles document manipulation and undo stack management."""

    undo_stack_changed = Signal()
    document_changed = Signal()

    def __init__(self, settings: SettingsController, document_service: DocumentService | None = None, clipboard_service: ClipboardService | None = None):
        super().__init__()
        self.settings = settings
        self.document: Document | None = None
        self._layer_manager = None
        self._layer_manager_unsubscribe = None
        self.drawing_context = DrawingContext()
        self.undo_manager = UndoManager()

        self.document_service = document_service or DocumentService()
        self.clipboard_service = clipboard_service or ClipboardService(self.document_service)
        self.document_service.app = self
        self.clipboard_service.app = self

        self.attach_document(Document(64, 64))

        self.is_recording = False
        self.recorded_commands = []
        self.is_dirty = False

        self.main_window = None

    # expose settings-backed properties
    @property
    def config(self):
        return self.settings.config

    @property
    def last_directory(self):
        return self.settings.last_directory

    @last_directory.setter
    def last_directory(self, value):
        self.settings.last_directory = value

    def execute_command(self, command):
        command.execute()
        if self.is_recording:
            self.recorded_commands.append(command)
        else:
            self.undo_manager.add_command(command)
            self.undo_stack_changed.emit()
        self.is_dirty = True
        self.document_changed.emit()

    @Slot(int, int)
    def new_document(self, width, height):
        if not self.check_for_unsaved_changes():
            return
        self.attach_document(Document(width, height))
        self.undo_manager.clear()
        self.is_dirty = False
        self.undo_stack_changed.emit()
        self.document_changed.emit()
        if self.main_window:
            self.main_window.canvas.set_initial_zoom()

    def on_layer_visibility_changed(self, index):
        self.document_changed.emit()

    def on_layer_structure_changed(self):
        self.document_changed.emit()

    @Slot(int, int, object)
    def resize_document(self, width, height, interpolation):
        if self.document:
            command = ResizeCommand(self.document, width, height, interpolation)
            self.execute_command(command)
            if self.main_window:
                self.main_window.canvas.set_initial_zoom()

    def perform_crop(self, selection_rect):
        command = CropCommand(self.document, selection_rect)
        self.execute_command(command)

    @Slot()
    def undo(self):
        self.undo_manager.undo()
        self.undo_stack_changed.emit()
        self.document_changed.emit()

    @Slot()
    def redo(self):
        self.undo_manager.redo()
        self.undo_stack_changed.emit()
        self.document_changed.emit()

    @Slot()
    def add_frame(self):
        if not self.document:
            return
        command = AddFrameCommand(self.document)
        self.execute_command(command)

    @Slot()
    @Slot(int)
    def remove_frame(self, index: int | None = None):
        if not self.document:
            return
        manager = self.document.frame_manager
        if len(manager.frames) <= 1:
            return
        if index is None:
            index = manager.active_frame_index
        if not (0 <= index < len(manager.frames)):
            return
        command = RemoveFrameCommand(self.document, index)
        self.execute_command(command)

    @Slot()
    @Slot(int)
    def duplicate_frame(self, index: int | None = None):
        if not self.document:
            return
        manager = self.document.frame_manager
        if not manager.frames:
            return
        if index is None:
            index = manager.active_frame_index
        if not (0 <= index < len(manager.frames)):
            return
        command = DuplicateFrameCommand(self.document, index)
        self.execute_command(command)

    @Slot(int)
    def select_frame(self, index):
        if not self.document:
            return
        try:
            self.document.select_frame(index)
        except (ValueError, IndexError):
            return
        self.document_changed.emit()

    @Slot(int)
    def step_frame(self, offset):
        if not self.document:
            return
        manager = self.document.frame_manager
        if not manager.frames:
            return
        new_index = (manager.active_frame_index + offset) % len(manager.frames)
        self.document.select_frame(new_index)
        self.document_changed.emit()

    @Slot(bool, bool, bool)
    def flip(self, horizontal, vertical, all_layers):
        if self.document:
            command = FlipCommand(self.document, horizontal, vertical, all_layers)
            self.execute_command(command)

    def add_new_layer_with_image(self, image):
        command = AddLayerCommand(self.document, image, "AI Generated Layer")
        self.execute_command(command)

    @Slot(object)
    def handle_command(self, command):
        if isinstance(command, tuple):
            return
        if command:
            self.execute_command(command)

    def attach_document(self, document: Document) -> None:
        """Swap to a new document and bind to its layer manager lifecycle."""

        self.document = document
        if self._layer_manager_unsubscribe:
            self._layer_manager_unsubscribe()
            self._layer_manager_unsubscribe = None
        self._disconnect_layer_manager()
        self._layer_manager_unsubscribe = self.document.add_layer_manager_listener(
            self._bind_layer_manager
        )

    def _bind_layer_manager(self, layer_manager):
        if layer_manager is self._layer_manager:
            return
        self._disconnect_layer_manager()
        self._layer_manager = layer_manager
        layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        layer_manager.command_generated.connect(self.handle_command)

    def _disconnect_layer_manager(self):
        if not self._layer_manager:
            return
        for signal, slot in (
            (self._layer_manager.layer_visibility_changed, self.on_layer_visibility_changed),
            (self._layer_manager.layer_structure_changed, self.on_layer_structure_changed),
            (self._layer_manager.command_generated, self.handle_command),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._layer_manager = None

    def conform_to_palette(self, palette_hex):
        if not self.document or not palette_hex:
            return
        palette_rgb = [QColor(color).getRgb() for color in palette_hex]
        source_image = self.document.render()
        new_image = QImage(source_image.size(), QImage.Format_ARGB32)
        for y in range(source_image.height()):
            for x in range(source_image.width()):
                pixel_color = source_image.pixelColor(x, y).getRgb()
                closest_color_rgb = find_closest_color(pixel_color, palette_rgb)
                new_image.setPixelColor(x, y, QColor.fromRgb(*closest_color_rgb))
        self.add_new_layer_with_image(new_image)

    def remove_background_from_layer(self):
        layer = self.document.layer_manager.active_layer
        if not layer:
            return
        command = RemoveBackgroundCommand(layer)
        self.execute_command(command)

    def check_for_unsaved_changes(self):
        if not self.is_dirty:
            return True
        message_box = QMessageBox()
        message_box.setText("The document has been modified.")
        message_box.setInformativeText("Do you want to save your changes?")
        message_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        message_box.setDefaultButton(QMessageBox.Save)
        ret = message_box.exec()
        if ret == QMessageBox.Save:
            self.document_service.save_document()
            return not self.is_dirty
        elif ret == QMessageBox.Discard:
            return True
        elif ret == QMessageBox.Cancel:
            return False
        return False

    @Slot(bool)
    def set_mirror_x(self, enabled):
        self.drawing_context.set_mirror_x(enabled)

    @Slot(bool)
    def set_mirror_y(self, enabled):
        self.drawing_context.set_mirror_y(enabled)

    def get_current_image(self):
        return self.document.get_current_image_for_ai()

    @Slot()
    def create_brush(self):
        if not self.main_window:
            return
        selection = self.main_window.canvas.selection_shape if self.main_window.canvas else None
        image = self.document.render()
        if image.isNull():
            return
        if selection and not selection.isEmpty():
            rect = selection.boundingRect().toRect()
            rect = rect.intersected(image.rect())
            if rect.isEmpty():
                return
            image = image.copy(rect)

        cropped_image = self._crop_to_non_transparent_pixels(image)
        if cropped_image is None:
            return
        self.drawing_context.set_pattern_brush(cropped_image)

    def _crop_to_non_transparent_pixels(self, image: QImage) -> QImage | None:
        if image.isNull():
            return None

        width = image.width()
        height = image.height()
        min_x, min_y = width, height
        max_x, max_y = -1, -1

        for y in range(height):
            for x in range(width):
                if image.pixelColor(x, y).alpha() > 0:
                    if x < min_x:
                        min_x = x
                    if y < min_y:
                        min_y = y
                    if x > max_x:
                        max_x = x
                    if y > max_y:
                        max_y = y

        if max_x < min_x or max_y < min_y:
            return None

        rect = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        return image.copy(rect)
