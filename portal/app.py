from .document import Document
from .undo import UndoManager
from .drawing_context import DrawingContext
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QFileDialog, QApplication
import configparser
import os
from .command import FlipCommand, ResizeCommand, CropCommand, PasteCommand, AddLayerCommand, DrawCommand, FillCommand, ShapeCommand, MoveCommand


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

    @Slot()
    def flip_horizontal(self):
        if self.document:
            command = FlipCommand(self.document, 'horizontal')
            self.execute_command(command)

    @Slot()
    def flip_vertical(self):
        if self.document:
            command = FlipCommand(self.document, 'vertical')
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
    def handle_command_data(self, command_data):
        command_type, data = command_data
        active_layer = self.document.layer_manager.active_layer
        if not active_layer:
            # Handle messages that don't need an active layer
            if command_type == "get_active_layer_image":
                # A tool has requested the active layer image, but there is no layer.
                # Set canvas.original_image to None to signal this.
                # This requires a reference to the canvas, which the App doesn't have.
                # This is a design issue. The UI should have this reference.
                # For now, I'll assume the UI will handle this.
                pass
            return

        if command_type == "draw":
            command = DrawCommand(
                layer=active_layer,
                points=data["points"],
                color=data["color"],
                width=data["width"],
                brush_type=data["brush_type"],
                erase=data.get("erase", False),
                selection_shape=data["selection_shape"],
            )
            self.execute_command(command)

        elif command_type == "fill":
            command = FillCommand(
                document=self.document,
                layer=active_layer,
                fill_pos=data["fill_pos"],
                fill_color=data["fill_color"],
                selection_shape=data["selection_shape"],
                mirror_x=data["mirror_x"],
                mirror_y=data["mirror_y"],
            )
            self.execute_command(command)

        elif command_type == "shape":
            command = ShapeCommand(
                layer=active_layer,
                rect=data["rect"],
                shape_type=data["shape_type"],
                color=data["color"],
                width=data["width"],
                selection_shape=data["selection_shape"],
            )
            self.execute_command(command)

        elif command_type == "move":
            command = MoveCommand(
                layer=active_layer,
                moved_image=data["moved_image"],
                delta=data["delta"],
                original_selection_shape=data["original_selection_shape"],
            )
            self.execute_command(command)

        elif command_type == "get_active_layer_image":
            # This is a special command for tools that need a copy of the layer before proceeding.
            # The UI should connect this to a method that can access the canvas.
            # This is a flaw in the current design. I will need to address this in the UI step.
            # For now, I will emit a signal that the UI can catch.
            self.document_changed.emit() # This is not ideal, but it will trigger a repaint.

        elif command_type == "cut_selection":
            # Similar to above, this needs to be handled by something with access to the canvas and the document.
            self.document_changed.emit()