from .document import Document
from .undo import UndoManager
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor


class App(QObject):
    tool_changed = Signal(str)
    pen_color_changed = Signal(QColor)
    undo_stack_changed = Signal()

    def __init__(self):
        super().__init__()
        self.window = None
        self.document = Document(64, 64)
        self.tool = "Pen"
        self.pen_color = QColor("black")
        self.pen_width = 5
        self.undo_manager = UndoManager()
        self._prime_undo_stack()

    def set_pen_width(self, width):
        self.pen_width = width

    def _prime_undo_stack(self):
        self.undo_manager.add_undo_state(self.document.layer_manager.clone())
        self.undo_stack_changed.emit()

    def set_window(self, window):
        self.window = window
        self.undo_stack_changed.emit()

    def set_tool(self, tool):
        self.tool = tool
        self.tool_changed.emit(self.tool)

    def set_pen_color(self, color_hex):
        self.pen_color = QColor(color_hex)
        self.pen_color_changed.emit(self.pen_color)

    def new_document(self, width, height):
        self.document = Document(width, height)
        self.undo_manager.clear()
        self._prime_undo_stack()
        if self.window:
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()

    def add_undo_state(self):
        self.undo_manager.add_undo_state(self.document.layer_manager.clone())
        self.undo_stack_changed.emit()

    def undo(self):
        state = self.undo_manager.undo()
        if state:
            self.document.layer_manager = state
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
            self.undo_stack_changed.emit()

    def redo(self):
        state = self.undo_manager.redo()
        if state:
            self.document.layer_manager = state
            self.window.layer_manager_widget.refresh_layers()
            self.window.canvas.update()
            self.undo_stack_changed.emit()

    def exit(self):
        if self.window:
            self.window.close()
