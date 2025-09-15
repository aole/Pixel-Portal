from portal.tools.basetool import BaseTool
from PySide6.QtGui import QColor, QCursor, QPixmap
from PySide6.QtCore import QPoint


class PickerTool(BaseTool):
    name = "Picker"
    icon = "icons/toolpicker.png"
    shortcut = "i"
    category = "draw"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(QPixmap("icons/toolpicker.png"), 0, 31)

    def mousePressEvent(self, event, doc_pos):
        self.pick_color(doc_pos)

    def mouseMoveEvent(self, event, doc_pos):
        if event.buttons():  # Only pick if a mouse button is pressed
            self.pick_color(doc_pos)

    def mouseReleaseEvent(self, event, doc_pos):
        if self.canvas.drawing_context.previous_tool:
            self.canvas.drawing_context.set_tool(self.canvas.drawing_context.previous_tool)

    def pick_color(self, doc_pos):
        rendered_image = self.canvas.document.render()
        sample_pos = doc_pos
        if self.canvas.tile_preview_enabled:
            doc_width = rendered_image.width()
            doc_height = rendered_image.height()
            sample_pos = QPoint(doc_pos.x() % doc_width, doc_pos.y() % doc_height)

        if rendered_image.rect().contains(sample_pos):
            color = rendered_image.pixelColor(sample_pos)
            if color.alpha() > 0:  # Only pick visible colors
                self.canvas.drawing_context.set_pen_color(color.name())
