from portal.core.document import Document
from portal.core.undo import UndoManager
from portal.core.drawing_context import DrawingContext
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QFileDialog, QApplication
import configparser
import os
from portal.core.command import FlipCommand, ResizeCommand, CropCommand, PasteCommand, AddLayerCommand, DrawCommand, FillCommand, ShapeCommand, MoveCommand
from PySide6.QtCore import QPoint
from portal.core.color_utils import find_closest_color


class App(QObject):
    undo_stack_changed = Signal()
    document_changed = Signal()
    select_all_triggered = Signal()
    select_none_triggered = Signal()
    invert_selection_triggered = Signal()
    crop_to_selection_triggered = Signal()
    clear_layer_triggered = Signal()
    exit_triggered = Signal()

    def __init__(self):
        super().__init__()
        self.main_window = None
        self.document = Document(64, 64)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.document.layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.drawing_context = DrawingContext()
        self.undo_manager = UndoManager()

        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')

        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

    def execute_command(self, command):
        command.execute()
        self.undo_manager.add_command(command)
        self.undo_stack_changed.emit()
        self.document_changed.emit()

    @Slot(int, int)
    def new_document(self, width, height):
        self.document = Document(width, height)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.document.layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.undo_manager.clear()
        self.undo_stack_changed.emit()
        self.document_changed.emit()

    def on_layer_visibility_changed(self, index):
        self.document_changed.emit()

    def on_layer_structure_changed(self):
        self.document_changed.emit()

    @Slot(int, int, object)
    def resize_document(self, width, height, interpolation):
        if self.document:
            command = ResizeCommand(self.document, width, height, interpolation)
            self.execute_command(command)

    @Slot()
    def crop_to_selection(self):
        self.crop_to_selection_triggered.emit()

    def perform_crop(self, selection_rect):
        command = CropCommand(self.document, selection_rect)
        self.execute_command(command)

    @Slot()
    def paste_as_new_layer(self):
        clipboard = QApplication.clipboard()
        image = clipboard.image()

        if self.document and not image.isNull():
            command = PasteCommand(self.document, image)
            self.execute_command(command)

    @Slot()
    def open_document(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image", 
            self.last_directory, 
            "All Supported Files (*.png *.jpg *.bmp *.tif *.tiff);;Image Files (*.png *.jpg *.bmp);;TIFF Files (*.tif *.tiff)"
        )
        if file_path:
            self.last_directory = os.path.dirname(file_path)
            self.config.set('General', 'last_directory', self.last_directory)
            with open('settings.ini', 'w') as configfile:
                self.config.write(configfile)

            if file_path.lower().endswith(('.tif', '.tiff')):
                self.document = Document.load_tiff(file_path)
            else:
                image = QImage(file_path)
                if not image.isNull():
                    self.document = Document(image.width(), image.height())
                    self.document.layer_manager.layers[0].image = image

            self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
            self.document.layer_manager.layer_structure_changed.connect(self.on_layer_structure_changed)
            self.undo_manager.clear()
            self.undo_stack_changed.emit()
            self.document_changed.emit()

    @Slot()
    def save_document(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            None,
            "Save Image", 
            self.last_directory, 
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;Bitmap (*.bmp);;TIFF (*.tif *.tiff)"
        )
        if file_path:
            self.last_directory = os.path.dirname(file_path)
            self.config.set('General', 'last_directory', self.last_directory)
            with open('settings.ini', 'w') as configfile:
                self.config.write(configfile)

            if "TIFF" in selected_filter:
                self.document.save_tiff(file_path)
            else:
                image = self.document.render()
                image.save(file_path)

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
            print(f"Ignoring tuple-based command in App.handle_command: {command}")
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