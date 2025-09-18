from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
import os

from portal.core.document_controller import DocumentController, BackgroundRemovalScope
from portal.core.settings_controller import SettingsController
from portal.core.scripting import ScriptingAPI
from portal.ui.script_dialog import ScriptDialog
from portal.core.command import CompositeCommand


class App(QObject):
    """Application orchestrator delegating logic to controllers."""

    undo_stack_changed = Signal()
    document_changed = Signal()
    select_all_triggered = Signal()
    select_none_triggered = Signal()
    invert_selection_triggered = Signal()
    crop_to_selection_triggered = Signal()
    clear_layer_triggered = Signal()
    exit_triggered = Signal()

    def __init__(self, document_service=None, clipboard_service=None):
        super().__init__()
        self._main_window = None

        self.settings_controller = SettingsController()
        self.document_controller = DocumentController(
            self.settings_controller, document_service, clipboard_service
        )
        self.document_controller.undo_stack_changed.connect(self.undo_stack_changed.emit)
        self.document_controller.document_changed.connect(self.document_changed.emit)

        self.scripting_api = ScriptingAPI(self)

    # expose common attributes for compatibility
    @property
    def document(self):
        return self.document_controller.document

    @property
    def undo_manager(self):
        return self.document_controller.undo_manager

    @property
    def drawing_context(self):
        return self.document_controller.drawing_context

    @property
    def document_service(self):
        return self.document_controller.document_service

    @document_service.setter
    def document_service(self, service):
        self.document_controller.document_service = service
        if hasattr(service, "app"):
            service.app = self.document_controller

    @property
    def clipboard_service(self):
        return self.document_controller.clipboard_service

    @clipboard_service.setter
    def clipboard_service(self, service):
        self.document_controller.clipboard_service = service
        if hasattr(service, "app"):
            service.app = self.document_controller

    @property
    def config(self):
        return self.settings_controller.config

    @property
    def last_directory(self):
        return self.settings_controller.last_directory

    @last_directory.setter
    def last_directory(self, value):
        self.settings_controller.last_directory = value

    @property
    def main_window(self):
        return self._main_window

    @main_window.setter
    def main_window(self, window):
        self._main_window = window
        self.document_controller.main_window = window

    def execute_command(self, command):
        self.document_controller.execute_command(command)

    @Slot(int, int)
    def new_document(self, width, height):
        self.document_controller.new_document(width, height)

    def on_layer_visibility_changed(self, index):
        self.document_controller.on_layer_visibility_changed(index)

    def on_layer_structure_changed(self):
        self.document_controller.on_layer_structure_changed()

    @Slot(int, int, object)
    def resize_document(self, width, height, interpolation):
        self.document_controller.resize_document(width, height, interpolation)

    @Slot()
    def crop_to_selection(self):
        self.crop_to_selection_triggered.emit()

    def perform_crop(self, selection_rect):
        self.document_controller.perform_crop(selection_rect)

    @Slot()
    def save_settings(self):
        ai_settings = None
        if self.main_window:
            ai_settings = self.main_window.ai_panel.get_settings()
        self.settings_controller.save_settings(ai_settings)

    @Slot()
    def undo(self):
        self.document_controller.undo()

    @Slot()
    def redo(self):
        self.document_controller.redo()

    def add_keyframe(self, frame_index: int) -> None:
        self.document_controller.add_keyframe(frame_index)

    def remove_keyframe(self, frame_index: int) -> None:
        self.document_controller.remove_keyframe(frame_index)

    def duplicate_keyframe(
        self, source_frame: Optional[int] = None, target_frame: Optional[int] = None
    ) -> Optional[int]:
        return self.document_controller.duplicate_keyframe(source_frame, target_frame)

    def insert_frame(self, frame_index: int) -> None:
        self.document_controller.insert_frame(frame_index)

    def delete_frame(self, frame_index: int) -> None:
        self.document_controller.delete_frame(frame_index)

    def copy_keyframe(self, frame_index: int) -> bool:
        return self.document_controller.copy_keyframe(frame_index)

    def paste_keyframe(self, frame_index: int) -> bool:
        return self.document_controller.paste_keyframe(frame_index)

    def has_copied_keyframe(self) -> bool:
        return self.document_controller.has_copied_keyframe()

    def select_frame(self, index: int) -> None:
        self.document_controller.select_frame(index)

    @Slot()
    def select_all(self):
        self.select_all_triggered.emit()

    @Slot()
    def select_none(self):
        self.select_none_triggered.emit()

    @Slot(bool, bool, bool)
    def flip(self, horizontal, vertical, all_layers):
        self.document_controller.flip(horizontal, vertical, all_layers)

    @Slot()
    def invert_selection(self):
        self.invert_selection_triggered.emit()

    @Slot()
    def select_opaque(self):
        document = getattr(self, "document", None)
        layer_manager = getattr(document, "layer_manager", None)
        active_layer = getattr(layer_manager, "active_layer", None)
        self._select_opaque_for_layer(active_layer)

    def select_opaque_for_layer(self, layer):
        """Select opaque pixels for a specific layer without changing state."""
        self._select_opaque_for_layer(layer)

    def _select_opaque_for_layer(self, layer):
        if not self.main_window or layer is None:
            return

        canvas = getattr(self.main_window, "canvas", None)
        if canvas is None:
            return

        from portal.commands.selection_commands import SelectOpaqueCommand

        command = SelectOpaqueCommand(layer, canvas)
        self.execute_command(command)

    @Slot()
    def clear_layer(self):
        self.clear_layer_triggered.emit()

    @Slot()
    def exit(self):
        self.exit_triggered.emit()

    def check_for_unsaved_changes(self):
        return self.document_controller.check_for_unsaved_changes()

    @Slot(bool)
    def set_mirror_x(self, enabled):
        self.document_controller.set_mirror_x(enabled)

    @Slot(bool)
    def set_mirror_y(self, enabled):
        self.document_controller.set_mirror_y(enabled)

    def get_current_image(self):
        return self.document_controller.get_current_image()

    def add_new_layer_with_image(self, image):
        self.document_controller.add_new_layer_with_image(image)

    @Slot()
    def create_brush(self):
        self.document_controller.create_brush()

    @Slot(object)
    def handle_command(self, command):
        self.document_controller.handle_command(command)

    def conform_to_palette(self):
        if not self.main_window:
            return
        palette_hex = self.main_window.get_palette()
        self.document_controller.conform_to_palette(palette_hex)

    def remove_background_from_layer(
        self, scope: BackgroundRemovalScope | None = None
    ):
        if scope is None:
            self.document_controller.remove_background_from_layer()
        else:
            self.document_controller.remove_background_from_layer(scope)

    def run_script(self, script_path):
        """Runs a script with optional parameters and undo support."""
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()

            script_namespace = {}
            exec(script_code, script_namespace)

            params = script_namespace.get('params')
            main_func = script_namespace.get('main')

            if not callable(main_func):
                raise ValueError("Script must define a main(api, values) function.")

            values = {}
            if params:
                dialog = ScriptDialog(params, self.main_window)
                if dialog.exec():
                    values = dialog.get_values()
                else:
                    return

            self.document_controller.is_recording = True
            self.document_controller.recorded_commands = []

            main_func(self.scripting_api, values)

            self.document_controller.is_recording = False

            if self.document_controller.recorded_commands:
                script_name = os.path.splitext(os.path.basename(script_path))[0]
                composite_command = CompositeCommand(
                    self.document_controller.recorded_commands,
                    name=f"Run Script: {script_name}"
                )
                self.document_controller.undo_manager.add_command(composite_command)
                self.document_controller.undo_stack_changed.emit()
        except Exception as e:
            print(f"Error running script {script_path}: {e}")
            self.document_controller.is_recording = False
