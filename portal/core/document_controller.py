from enum import Enum, auto
from typing import Iterable, Optional

from PySide6.QtCore import QObject, Signal, Slot, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QMessageBox

from portal.core.document import Document
from portal.core.undo import UndoManager
from portal.core.drawing_context import DrawingContext
from portal.core.command import (
    FlipCommand,
    ResizeCommand,
    CropCommand,
    AddLayerCommand,
    CompositeCommand,
)
from portal.commands.layer_commands import RemoveBackgroundCommand
from portal.commands.timeline_commands import (
    AddKeyframeCommand,
    DeleteFrameCommand,
    DuplicateKeyframeCommand,
    InsertFrameCommand,
    PasteKeyframeCommand,
    RemoveKeyframeCommand,
    SetKeyframesCommand,
)
from portal.core.color_utils import find_closest_color
from portal.core.layer import Layer
from portal.core.services.document_service import DocumentService
from portal.core.services.clipboard_service import ClipboardService
from portal.core.settings_controller import SettingsController


class BackgroundRemovalScope(Enum):
    THIS_KEY = auto()
    ALL_KEYS = auto()


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
        self._copied_key_state = None
        self.auto_key_enabled = False

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

    def is_auto_key_enabled(self) -> bool:
        return bool(self.auto_key_enabled)

    def set_auto_key_enabled(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self.auto_key_enabled:
            return
        self.auto_key_enabled = normalized

    def ensure_auto_key_for_active_layer(self) -> bool:
        """Create a keyframe on the active layer if auto-key is enabled."""

        if not self.auto_key_enabled:
            return False

        document = self.document
        if document is None:
            return False

        frame_manager = getattr(document, "frame_manager", None)
        if frame_manager is None:
            return False

        current_frame = getattr(frame_manager, "active_frame_index", None)
        if current_frame is None or current_frame < 0:
            return False

        try:
            layer_manager = document.layer_manager
        except ValueError:
            return False

        active_layer = getattr(layer_manager, "active_layer", None)
        if active_layer is None:
            return False

        key_frames = getattr(document, "key_frames", [])
        if current_frame in key_frames:
            return False

        self.add_keyframe(current_frame)
        return True

    def set_keyframes(self, frames: Iterable[int]) -> None:
        document = self.document
        if document is None:
            return
        frame_manager = document.frame_manager
        layer_manager = getattr(frame_manager, "current_layer_manager", None)
        if layer_manager is None or layer_manager.active_layer is None:
            return
        normalized: set[int] = set()
        for value in frames:
            try:
                frame_index = int(value)
            except (TypeError, ValueError):
                continue
            if frame_index < 0:
                continue
            normalized.add(frame_index)
        if not normalized:
            normalized = {0}
        existing_keys = set(document.key_frames)
        if normalized == existing_keys:
            return
        command = SetKeyframesCommand(document, normalized)
        self.execute_command(command)

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

    @Slot(bool, bool, bool)
    def flip(self, horizontal, vertical, all_layers):
        if self.document:
            command = FlipCommand(self.document, horizontal, vertical, all_layers)
            self.execute_command(command)

    def add_keyframe(self, frame_index: int) -> None:
        document = self.document
        if document is None:
            return
        if frame_index < 0:
            return
        frame_manager = document.frame_manager
        frame_manager.ensure_frame(frame_index)
        if frame_index in document.key_frames:
            return
        command = AddKeyframeCommand(document, frame_index)
        self.execute_command(command)
        self.select_frame(frame_index)

    def remove_keyframe(self, frame_index: int) -> None:
        document = self.document
        if document is None:
            return
        if frame_index not in document.key_frames:
            return
        if len(document.key_frames) <= 1:
            return
        command = RemoveKeyframeCommand(document, frame_index)
        self.execute_command(command)

    def duplicate_keyframe(
        self,
        source_frame: Optional[int],
        target_frame: Optional[int],
    ) -> Optional[int]:
        document = self.document
        if document is None:
            return None
        if not document.key_frames:
            return None
        frame_manager = document.frame_manager
        if target_frame is not None and target_frame < 0:
            return None
        if target_frame is not None:
            frame_manager.ensure_frame(target_frame)

        command = DuplicateKeyframeCommand(document, source_frame, target_frame)
        self.execute_command(command)
        return command.created_frame

    def insert_frame(self, frame_index: int) -> None:
        document = self.document
        if document is None:
            return
        if frame_index < 0:
            frame_index = 0
        command = InsertFrameCommand(document, frame_index)
        self.execute_command(command)

    def delete_frame(self, frame_index: int) -> None:
        document = self.document
        if document is None:
            return
        frame_manager = document.frame_manager
        frame_count = len(frame_manager.frames)
        if frame_count <= 1:
            return
        if not (0 <= frame_index < frame_count):
            return
        command = DeleteFrameCommand(document, frame_index)
        self.execute_command(command)

    def has_copied_keyframe(self) -> bool:
        return self._copied_key_state is not None

    def copy_keyframe(self, frame_index: int) -> bool:
        document = self.document
        if document is None:
            return False
        if frame_index < 0:
            return False
        key_state = document.copy_active_layer_key(frame_index)
        if key_state is None:
            return False
        self._copied_key_state = key_state
        return True

    def paste_keyframe(self, frame_index: int) -> bool:
        if self._copied_key_state is None:
            return False
        document = self.document
        if document is None:
            return False
        if frame_index < 0:
            return False
        frame_manager = document.frame_manager
        layer_manager = frame_manager.current_layer_manager
        if layer_manager is None or layer_manager.active_layer is None:
            return False
        existing_keys = set(document.key_frames)
        if frame_index in existing_keys:
            parent = getattr(self, "main_window", None)
            response = QMessageBox.question(
                parent,
                "Replace Keyframe?",
                f"Frame {frame_index} already has a key. Replace it with the copied key?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                return False
        command = PasteKeyframeCommand(document, frame_index, self._copied_key_state)
        self.execute_command(command)
        return command.applied

    def paste_key_from_image(
        self,
        image: QImage,
        frame_index: Optional[int] = None,
        *,
        prompt_on_replace: bool = False,
    ) -> bool:
        if image is None or image.isNull():
            return False
        document = self.document
        if document is None:
            return False
        frame_manager = document.frame_manager
        if frame_manager is None:
            return False
        target_frame = frame_index
        if target_frame is None:
            target_frame = getattr(frame_manager, "active_frame_index", None)
        if target_frame is None or target_frame < 0:
            return False
        frame_manager.ensure_frame(target_frame)
        layer_manager = frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        if prompt_on_replace:
            existing_keys = set(document.key_frames)
            if target_frame in existing_keys:
                parent = getattr(self, "main_window", None)
                response = QMessageBox.question(
                    parent,
                    "Replace Keyframe?",
                    (
                        f"Frame {target_frame} already has a key. "
                        "Replace it with the imported image?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if response != QMessageBox.Yes:
                    return False

        target_width = layer.image.width()
        target_height = layer.image.height()
        prepared_image = image
        if (
            prepared_image.width() > target_width
            or prepared_image.height() > target_height
        ):
            prepared_image = prepared_image.scaled(
                target_width,
                target_height,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )

        key_state = Layer(target_width, target_height, layer.name)
        key_state.visible = layer.visible
        key_state.opacity = layer.opacity
        key_state.image.fill(Qt.transparent)

        painter = QPainter(key_state.image)
        painter.drawImage(0, 0, prepared_image)
        painter.end()

        command = PasteKeyframeCommand(document, target_frame, key_state)
        self.execute_command(command)
        return command.applied

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

    def remove_background_from_layer(
        self, scope: BackgroundRemovalScope = BackgroundRemovalScope.ALL_KEYS
    ):
        document = self.document
        if document is None:
            return

        layer_manager = getattr(document, "layer_manager", None)
        if layer_manager is None:
            return

        layer = getattr(layer_manager, "active_layer", None)
        if layer is None:
            return

        frame_manager = getattr(document, "frame_manager", None)
        if frame_manager is None:
            command = RemoveBackgroundCommand(layer)
            self.execute_command(command)
            return

        layer_uid = getattr(layer, "uid", None)
        if layer_uid is None:
            return

        active_frame_index = getattr(frame_manager, "active_frame_index", None)
        if active_frame_index is None:
            active_frame_index = 0

        layer_keys_map = getattr(frame_manager, "layer_keys", {})
        if not isinstance(layer_keys_map, dict):
            layer_keys_map = {}

        resolve_key = getattr(
            frame_manager, "resolve_layer_key_frame_index", lambda *_, **__: None
        )

        if scope is BackgroundRemovalScope.ALL_KEYS:
            keys = sorted(layer_keys_map.get(layer_uid, set()))
            if not keys:
                resolved = resolve_key(layer_uid, active_frame_index)
                keys = [resolved] if resolved is not None else []
        else:
            resolved = resolve_key(layer_uid, active_frame_index)
            keys = [resolved] if resolved is not None else []

        visited_layers = set()
        target_layers = []
        frames = getattr(frame_manager, "frames", [])
        for key_index in keys:
            if key_index is None:
                continue
            if not (0 <= key_index < len(frames)):
                continue
            manager = frames[key_index].layer_manager
            target_layer = None
            for candidate in getattr(manager, "layers", []):
                if getattr(candidate, "uid", None) == layer_uid:
                    target_layer = candidate
                    break
            if target_layer is None:
                continue
            identity = id(target_layer)
            if identity in visited_layers:
                continue
            visited_layers.add(identity)
            target_layers.append(target_layer)

        if not target_layers:
            command = RemoveBackgroundCommand(layer)
            self.execute_command(command)
            return

        commands = [RemoveBackgroundCommand(target) for target in target_layers]

        if len(commands) == 1:
            command = commands[0]
        else:
            name = (
                "Remove Background (All Keys)"
                if scope is BackgroundRemovalScope.ALL_KEYS
                else "Remove Background"
            )
            command = CompositeCommand(commands, name=name)

        self.execute_command(command)

    def select_frame(self, index: int) -> None:
        document = self.document
        if document is None:
            return
        frame_manager = document.frame_manager
        if index < 0:
            return
        frame_manager.ensure_frame(index)
        if frame_manager.active_frame_index == index:
            return
        document.select_frame(index)
        self.document_changed.emit()

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
