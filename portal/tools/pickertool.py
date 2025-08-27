from .basetool import BaseTool
from PySide6.QtGui import QColor


class PickerTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)

    def mousePressEvent(self, event, doc_pos):
        self.pick_color(doc_pos)

    def mouseMoveEvent(self, event, doc_pos):
        if event.buttons():  # Only pick if a mouse button is pressed
            self.pick_color(doc_pos)

    def mouseReleaseEvent(self, event, doc_pos):
        if self.app.previous_tool:
            self.app.set_tool(self.app.previous_tool)

    def pick_color(self, doc_pos):
        active_layer = self.app.document.layer_manager.active_layer
        if active_layer and active_layer.image.rect().contains(doc_pos):
            color = active_layer.image.pixelColor(doc_pos)
            if color.alpha() > 0:  # Only pick visible colors
                self.app.set_pen_color(color.name())
