from portal.core.document import Document
from portal.core.undo import UndoManager
from portal.core.drawing_context import DrawingContext
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QMessageBox
import configparser
import os
from portal.core.command import FlipCommand, ResizeCommand, CropCommand, AddLayerCommand, DrawCommand, FillCommand, ShapeCommand, MoveCommand, CompositeCommand
from PySide6.QtCore import QPoint
from portal.core.color_utils import find_closest_color
from portal.core.scripting import ScriptingAPI
from portal.ui.script_dialog import ScriptDialog
from portal.core.services.document_service import DocumentService
from portal.core.services.clipboard_service import ClipboardService


class App(QObject):
    undo_stack_changed = Signal()
    document_changed = Signal()
    select_all_triggered = Signal()
    select_none_triggered = Signal()
    invert_selection_triggered = Signal()
    crop_to_selection_triggered = Signal()
    clear_layer_triggered = Signal()
    exit_triggered = Signal()

    def __init__(self, document_service: DocumentService | None = None, clipboard_service: ClipboardService | None = None):
        super().__init__()
        self.main_window = None
        self.document = Document(64, 64)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.document.layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.document.layer_manager.command_generated.connect(self.handle_command)
        self.drawing_context = DrawingContext()
        self.undo_manager = UndoManager()
        self.scripting_api = ScriptingAPI(self)

        self.document_service = document_service or DocumentService()
        self.clipboard_service = clipboard_service or ClipboardService(self.document_service)
        self.document_service.app = self
        self.clipboard_service.app = self

        self.is_recording = False
        self.recorded_commands = []
        self.is_dirty = False

        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')

        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

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

        self.document = Document(width, height)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.document.layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.document.layer_manager.command_generated.connect(self.handle_command)
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

    @Slot()
    def crop_to_selection(self):
        self.crop_to_selection_triggered.emit()

    def perform_crop(self, selection_rect):
        command = CropCommand(self.document, selection_rect)
        self.execute_command(command)

    @Slot()
    def save_settings(self):
        try:
            if self.main_window:
                ai_settings = self.main_window.ai_panel.get_settings()
                if not self.config.has_section('AI'):
                    self.config.add_section('AI')
                self.config.set('AI', 'last_prompt', ai_settings['prompt'])

            with open('settings.ini', 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setText("Error saving settings")
            error_box.setInformativeText(f"Could not write to settings.ini.\n\nReason: {e}")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec()

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
    def select_all(self):
        self.select_all_triggered.emit()

    @Slot()
    def select_none(self):
        self.select_none_triggered.emit()

    @Slot(bool, bool, bool)
    def flip(self, horizontal, vertical, all_layers):
        if self.document:
            command = FlipCommand(self.document, horizontal, vertical, all_layers)
            self.execute_command(command)
    @Slot()
    def invert_selection(self):
        self.invert_selection_triggered.emit()

    @Slot()
    def clear_layer(self):
        self.clear_layer_triggered.emit()

    @Slot()
    def exit(self):
        self.exit_triggered.emit()

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

    def add_new_layer_with_image(self, image):
        command = AddLayerCommand(self.document, image, "AI Generated Layer")
        self.execute_command(command)

    @Slot(object)
    def handle_command(self, command):
        if isinstance(command, tuple):
            return

        if command:
            self.execute_command(command)

    def conform_to_palette(self):
        if not self.document or not self.main_window:
            return

        palette_hex = self.main_window.get_palette()
        if not palette_hex:
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

    def run_script(self, script_path):
        """
        Runs a script by defining its parameters, showing a dialog to get user input,
        and then executing the script's main function as a single undoable command.
        """
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()

            # Execute the script in a temporary namespace to get params and main function
            script_namespace = {}
            exec(script_code, script_namespace)

            params = script_namespace.get('params')
            main_func = script_namespace.get('main')

            if not callable(main_func):
                raise ValueError("Script must define a main(api, values) function.")

            # Get parameters from user if the script defines them
            values = {}
            if params:
                dialog = ScriptDialog(params, self.main_window)
                if dialog.exec():
                    values = dialog.get_values()
                else:
                    return # User cancelled

            # Start recording and execute the main logic
            self.is_recording = True
            self.recorded_commands = []

            main_func(self.scripting_api, values)

            self.is_recording = False

            # Create a composite command if any commands were recorded
            if self.recorded_commands:
                script_name = os.path.splitext(os.path.basename(script_path))[0]
                composite_command = CompositeCommand(self.recorded_commands, name=f"Run Script: {script_name}")
                self.undo_manager.add_command(composite_command)
                self.undo_stack_changed.emit()

        except Exception as e:
            print(f"Error running script {script_path}: {e}")
            self.is_recording = False # Ensure recording is turned off on error
