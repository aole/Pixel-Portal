from .document import Document
from .undo import UndoManager
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QFileDialog, QApplication
import configparser
import os


class App(QObject):
    tool_changed = Signal(str)
    pen_color_changed = Signal(QColor)
    pen_width_changed = Signal(int)
    undo_stack_changed = Signal()
    document_changed = Signal()

    def __init__(self):
        super().__init__()
        self.window = None
        self.document = Document(64, 64)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.tool = "Pen"
        self.previous_tool = "Pen"
        self.pen_color = QColor("black")
        self.pen_width = 1
        self.undo_manager = UndoManager()
        self._prime_undo_stack()

        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')

        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

    def set_pen_width(self, width):
        self.pen_width = width
        self.pen_width_changed.emit(self.pen_width)

    def _prime_undo_stack(self):
        self.undo_manager.add_undo_state(self.document.clone())
        self.undo_stack_changed.emit()

    def set_window(self, window):
        self.window = window
        self.undo_stack_changed.emit()

    def set_tool(self, tool):
        if self.tool != "Picker":
            self.previous_tool = self.tool
        self.tool = tool
        self.tool_changed.emit(self.tool)

    def set_pen_color(self, color_hex):
        self.pen_color = QColor(color_hex)
        self.pen_color_changed.emit(self.pen_color)

    def new_document(self, width, height):
        self.document = Document(width, height)
        self.document.layer_manager.layer_visibility_changed.connect(self.on_layer_visibility_changed)
        self.undo_manager.clear()
        self._prime_undo_stack()
        if self.window:
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
        self.document_changed.emit()

    def on_layer_visibility_changed(self, index):
        if self.window:
            self.window.canvas.update()

    def resize_document(self, width, height, interpolation):
        if self.document:
            self.document.resize(width, height, interpolation)
            self.add_undo_state()
            if self.window:
                self.window.canvas.update()
            self.document_changed.emit()

    def crop_to_selection(self):
        if self.window and self.window.canvas.selection_shape:
            selection_rect = self.window.canvas.selection_shape.boundingRect().toRect()
            self.document.crop(selection_rect)
            self.window.canvas.select_none()
            self.add_undo_state()
            if self.window:
                self.window.canvas.update()
            self.document_changed.emit()

    def paste_as_new_layer(self):
        clipboard = QApplication.clipboard()
        image = clipboard.image()

        if self.document and not image.isNull():
            self.document.add_layer_from_clipboard(image)
            self.add_undo_state()
            if self.window:
                self.window.layer_manager_widget.refresh_layers()
                self.window.canvas.update()

    def open_document(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, 
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
            self.undo_manager.clear()
            self._prime_undo_stack()
            if self.window:
                self.window.layer_manager_widget.refresh_layers()
                self.window.canvas.update()

    def save_document(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self.window, 
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

    def add_undo_state(self):
        self.undo_manager.add_undo_state(self.document.clone())
        self.undo_stack_changed.emit()

    def undo(self):
        state = self.undo_manager.undo()
        if state:
            self.document = state
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
            self.undo_stack_changed.emit()

    def redo(self):
        state = self.undo_manager.redo()
        if state:
            self.document = state
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
            self.undo_stack_changed.emit()

    def select_all(self):
        if self.window:
            self.window.canvas.select_all()

    def select_none(self):
        if self.window:
            self.window.canvas.select_none()

    def flip_horizontal(self):
        if self.document:
            self.document.flip_horizontal()
            self.add_undo_state()
            if self.window:
                self.window.canvas.update()
            self.document_changed.emit()

    def flip_vertical(self):
        if self.document:
            self.document.flip_vertical()
            self.add_undo_state()
            if self.window:
                self.window.canvas.update()
            self.document_changed.emit()

    def invert_selection(self):
        if self.window:
            self.window.canvas.invert_selection()

    def clear_layer(self):
        if self.window:
            self.window.layer_manager_widget.clear_layer()

    def exit(self):
        if self.window:
            self.window.close()

    def get_current_image(self):
        return self.document.get_current_image_for_ai()

    def add_new_layer_with_image(self, image):
        self.document.add_new_layer_with_image(image)
        self.add_undo_state()
        if self.window:
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
