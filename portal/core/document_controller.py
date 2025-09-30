import os
from enum import Enum, auto
from typing import Iterable, Optional
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QMessageBox

from PIL.ImageQt import ImageQt

from portal.core.document import Document
from portal.core.undo import UndoManager
from portal.core.drawing_context import DrawingContext
from portal.core.command import (
    FlipCommand,
    FlipScope,
    ResizeCommand,
    CropCommand,
    AddLayerCommand,
    CompositeCommand,
    AddKeyframeCommand,
    MoveKeyframesCommand,
    DeleteKeyframesCommand,
    PasteKeyframesCommand,
)
from portal.commands.layer_commands import RemoveBackgroundCommand
from portal.core.color_utils import find_closest_color
from portal.core.layer import Layer
from portal.core.key import Key
from portal.core.services.document_service import DocumentService
from portal.core.services.clipboard_service import ClipboardService
from portal.core.settings_controller import SettingsController


DEFAULT_PLAYBACK_FPS = 12.0


@dataclass(slots=True)
class _CopiedKeyframesState:
    base_frame: int
    keys: tuple[Key, ...]


class BackgroundRemovalScope(Enum):
    THIS_KEY = auto()
    ALL_KEYS = auto()


class DocumentController(QObject):
    """Handles document manipulation and undo stack management."""

    undo_stack_changed = Signal()
    document_changed = Signal()
    ai_output_rect_changed = Signal(QRect)

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

        self.is_recording = False
        self.recorded_commands = []
        self._is_dirty = False

        self._main_window = None
        self._base_window_title = "Pixel Portal"
        self._copied_key_state = None
        self.auto_key_enabled = False
        default_fps = getattr(settings, "animation_fps", DEFAULT_PLAYBACK_FPS)
        self._playback_fps = Document.normalize_playback_fps(default_fps)
        self._playback_loop_start = 0
        self._playback_loop_end = 12

        self._last_ai_output_rect = QRect()
        self.document_changed.connect(self._on_document_mutated)

        initial_fps = self._playback_fps
        self.attach_document(Document(64, 64))
        self.set_playback_fps(initial_fps)

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

    @property
    def main_window(self):
        return self._main_window

    @main_window.setter
    def main_window(self, window):
        previous_window = getattr(self, "_main_window", None)
        self._main_window = window
        if window is None:
            self._base_window_title = "Pixel Portal"
        elif window is not previous_window:
            title_accessor = getattr(window, "windowTitle", None)
            if callable(title_accessor):
                base_title = title_accessor()
            elif isinstance(title_accessor, str):
                base_title = title_accessor
            else:
                base_title = None
            if not isinstance(base_title, str) or not base_title:
                base_title = "Pixel Portal"
            self._base_window_title = base_title
        self._refresh_window_title()

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool) -> None:
        normalized = bool(value)
        previous = self._is_dirty
        self._is_dirty = normalized
        if normalized != previous:
            self._refresh_window_title()

    def is_auto_key_enabled(self) -> bool:
        return bool(self.auto_key_enabled)

    def set_auto_key_enabled(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self.auto_key_enabled:
            return
        self.auto_key_enabled = normalized

    # ------------------------------------------------------------------
    def get_ai_output_rect(self) -> QRect | None:
        document = self.document
        if document is None:
            return None
        return document.get_ai_output_rect()

    # ------------------------------------------------------------------
    def set_ai_output_rect(self, rect: QRect | None) -> None:
        document = self.document
        if document is None:
            return
        normalized = document.set_ai_output_rect(rect)
        if normalized != self._last_ai_output_rect:
            self._last_ai_output_rect = normalized
            self.ai_output_rect_changed.emit(normalized)

    @property
    def playback_loop_range(self) -> tuple[int, int]:
        return self._playback_loop_start, self._playback_loop_end

    @property
    def playback_fps(self) -> float:
        return self._playback_fps

    def set_playback_fps(self, fps: float) -> None:
        normalized = Document.normalize_playback_fps(fps)
        if normalized == self._playback_fps:
            document = self.document
            if document is not None:
                document.set_playback_fps(normalized)
            return
        self._playback_fps = normalized
        document = self.document
        if document is not None:
            document.set_playback_fps(normalized)

    def set_playback_loop_range(self, start: int, end: int) -> None:
        document = self.document
        loop_range_setter = getattr(document, "set_playback_loop_range", None)
        start, nd = loop_range_setter(start, end)
        setattr(document, "playback_loop_start", start)
        setattr(document, "playback_loop_end", end)
        self._playback_loop_start = start
        self._playback_loop_end = end

    def ensure_auto_key_for_active_layer(self) -> bool:
        """Auto-key functionality has been removed."""

        return False

    def set_keyframes(self, frames: Iterable[int]) -> None:
        """Keyframe management is no longer supported."""

        return

    def move_keyframes(self, frames: Iterable[int], delta: int) -> None:
        if delta == 0:
            return
        document = self.document

        layer_manager = getattr(document, 'layer_manager', None)
        active_layer = getattr(layer_manager, 'active_layer', None)

        normalized: list[int] = []
        seen: set[int] = set()
        for frame in frames:
            if frame in seen:
                continue
            seen.add(frame)
            normalized.append(frame)

        if not normalized:
            return

        command = MoveKeyframesCommand(layer_manager, active_layer, normalized, delta)
        self.execute_command(command)

    def duplicate_keyframes(self, frames: Iterable[int], delta: int) -> None:
        """Keyframe management is no longer supported."""

        return

    def copy_keyframes(self, frames: Iterable[int]) -> bool:
        document = self.document
        layer_manager = getattr(document, 'layer_manager', None)
        active_layer = getattr(layer_manager, 'active_layer', None)

        normalized: list[int] = []
        seen: set[int] = set()
        for frame in frames:
            seen.add(frame)
            normalized.append(frame)

        if not normalized:
            return False

        normalized.sort()
        frame_lookup = {key.frame_number: key for key in active_layer.keys}
        keys_to_copy: list[Key] = []
        for frame in normalized:
            key = frame_lookup.get(frame)
            keys_to_copy.append(key)

        if not keys_to_copy:
            return False

        base_frame = min(key.frame_number for key in keys_to_copy)
        clones = tuple(key.clone(deep_copy=True) for key in keys_to_copy)
        self._copied_key_state = _CopiedKeyframesState(base_frame=base_frame, keys=clones)
        return True

    def paste_keyframes(self, target_frame: int) -> bool:
        state = self._copied_key_state
        document = self.document
        layer_manager = getattr(document, 'layer_manager', None)
        active_layer = getattr(layer_manager, 'active_layer', None)

        entries: list[tuple[int, Key]] = []
        base_frame = state.base_frame
        for key in state.keys:
            offset = key.frame_number - base_frame
            new_frame = target_frame + offset
            entries.append((new_frame, key.clone(deep_copy=True)))

        if not entries:
            return False

        entries.sort(key=lambda item: item[0])

        command = PasteKeyframesCommand(layer_manager, active_layer, entries)
        self.execute_command(command)
        return True

    # ------------------------------------------------------------------
    def _on_document_mutated(self):
        document = self.document
        if document is None:
            return
        rect = document.ensure_ai_output_rect()
        if rect != self._last_ai_output_rect:
            self._last_ai_output_rect = rect
            self.ai_output_rect_changed.emit(rect)

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

    def on_layer_onion_skin_changed(self, index):
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

    @Slot(bool, bool, object)
    def flip(self, horizontal, vertical, scope):
        if self.document:
            if not isinstance(scope, FlipScope):
                scope_map = {
                    True: FlipScope.FRAME,
                    False: FlipScope.LAYER,
                    "layer": FlipScope.LAYER,
                    "current_layer": FlipScope.LAYER,
                    "frame": FlipScope.FRAME,
                    "current_frame": FlipScope.FRAME,
                    "document": FlipScope.DOCUMENT,
                    "whole_document": FlipScope.DOCUMENT,
                    "all_frames": FlipScope.DOCUMENT,
                }
                scope = scope_map.get(scope, FlipScope.LAYER)
            command = FlipCommand(self.document, horizontal, vertical, scope)
            self.execute_command(command)

    def add_keyframe(self, frame_index: int) -> None:
        document = self.document
        if document is None:
            return

        layer_manager = getattr(document, "layer_manager", None)
        active_layer = getattr(layer_manager, "active_layer", None) if layer_manager else None
        if active_layer is None:
            return

        try:
            normalized_frame = int(frame_index)
        except (TypeError, ValueError):
            normalized_frame = layer_manager.current_frame if layer_manager else 0
        if normalized_frame < 0:
            normalized_frame = 0

        for index, key in enumerate(getattr(active_layer, "keys", [])):
            if getattr(key, "frame_number", None) == normalized_frame:
                active_layer.set_active_key_index(index)
                if layer_manager is not None:
                    layer_manager.set_current_frame(normalized_frame)
                return

        command = AddKeyframeCommand(self, active_layer, normalized_frame)
        self.execute_command(command)

    def remove_keyframes(self, frames: Iterable[int]) -> None:
        document = self.document
        if document is None:
            return

        layer_manager = getattr(document, 'layer_manager', None)
        active_layer = getattr(layer_manager, 'active_layer', None)

        normalized: list[int] = []
        seen: set[int] = set()
        for frame in frames:
            if frame in seen:
                continue
            seen.add(frame)
            normalized.append(frame)

        if not normalized:
            return

        command = DeleteKeyframesCommand(layer_manager, active_layer, normalized)
        self.execute_command(command)

    def remove_keyframe(self, frame_index: int) -> None:
        self.remove_keyframes((frame_index,))
    def duplicate_keyframe(
        self,
        source_frame: Optional[int],
        target_frame: Optional[int],
    ) -> Optional[int]:
        """Keyframe management is no longer supported."""

        return None

    def insert_frame(self, frame_index: int) -> None:
        """Frame management is no longer supported."""

        return

    def delete_frame(self, frame_index: int) -> None:
        """Frame management is no longer supported."""

        return

    def has_copied_keyframe(self) -> bool:
        state = self._copied_key_state
        return bool(state and state.keys)

    def copy_keyframe(self, frame_index: int) -> bool:
        return self.copy_keyframes((frame_index,))

    def paste_keyframe(self, frame_index: int) -> bool:
        return self.paste_keyframes(frame_index)

    def paste_key_from_image(
        self,
        image: QImage,
        frame_index: Optional[int] = None,
        *,
        prompt_on_replace: bool = False,
    ) -> bool:
        if image is None or image.isNull():
            return False
        return False

    def add_new_layer_with_image(self, image):
        document = self.document
        if document is None:
            return

        target_rect = document.get_ai_output_rect() or QRect(
            0, 0, max(1, int(document.width)), max(1, int(document.height))
        )

        if isinstance(image, QImage):
            q_image = image
        else:
            q_image = QImage(ImageQt(image.convert("RGBA")))

        if (
            q_image.width() != target_rect.width()
            or q_image.height() != target_rect.height()
        ):
            q_image = q_image.scaled(
                target_rect.width(),
                target_rect.height(),
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )

        composed = QImage(
            max(1, int(document.width)),
            max(1, int(document.height)),
            QImage.Format_ARGB32,
        )
        composed.fill(Qt.transparent)

        painter = QPainter(composed)
        painter.drawImage(target_rect.topLeft(), q_image)
        painter.end()

        command = AddLayerCommand(document, composed, "AI Generated Layer")
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
        stored_fps = getattr(document, "playback_fps", DEFAULT_PLAYBACK_FPS)
        normalized_fps = Document.normalize_playback_fps(stored_fps)
        self._playback_fps = normalized_fps
        document.set_playback_fps(normalized_fps)
        loop_range_getter = getattr(document, "get_playback_loop_range", None)
        loop_start, loop_end = loop_range_getter()

        self._playback_loop_start = loop_start
        self._playback_loop_end = loop_end
        
        if self._layer_manager_unsubscribe:
            self._layer_manager_unsubscribe()
            self._layer_manager_unsubscribe = None
        self._disconnect_layer_manager()
        self._layer_manager_unsubscribe = self.document.add_layer_manager_listener(
            self._bind_layer_manager
        )
        self._refresh_window_title()
        rect = self.document.ensure_ai_output_rect()
        self._last_ai_output_rect = rect
        self.ai_output_rect_changed.emit(rect)

    def update_main_window_title(self) -> None:
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        window = self._main_window
        if window is None:
            return
        base_title = self._base_window_title or "Pixel Portal"
        document = self.document
        display_name = ""
        if document is not None:
            file_path = getattr(document, "file_path", None)
            if file_path:
                display_name = os.path.basename(str(file_path)) or str(file_path)
                if self.is_dirty:
                    display_name = f"{display_name}*"
            else:
                display_name = "<unsaved>"
        title = base_title
        if display_name:
            title = f"{base_title} - {display_name}"
        setter = getattr(window, "setWindowTitle", None)
        if not callable(setter):
            return
        setter(title)

    def _bind_layer_manager(self, layer_manager):
        if layer_manager is self._layer_manager:
            return
        self._disconnect_layer_manager()
        self._layer_manager = layer_manager
        layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        layer_manager.layer_onion_skin_changed.connect(self.on_layer_onion_skin_changed)
        layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        layer_manager.command_generated.connect(self.handle_command)

    def _disconnect_layer_manager(self):
        if not self._layer_manager:
            return
        for signal, slot in (
            (self._layer_manager.layer_visibility_changed, self.on_layer_visibility_changed),
            (self._layer_manager.layer_onion_skin_changed, self.on_layer_onion_skin_changed),
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
        layer = getattr(layer_manager, "active_layer", None)
        command = RemoveBackgroundCommand(layer)
        self.execute_command(command)

    def select_frame(self, index: int) -> None:
        layer_manager = getattr(self.document, "layer_manager", None)
        layer_manager.set_current_frame(index)

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


