from portal.tools.basetool import BaseTool
from PySide6.QtGui import QMouseEvent, QPainterPath
from PySide6.QtCore import QPoint, QRect


class SelectColorTool(BaseTool):
    name = "Select Color"
    icon = "icons/toolselectcolor.png"
    shortcut = "w"

    def __init__(self, canvas):
        super().__init__(canvas)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        rendered_image = self.canvas.document.render()
        if not rendered_image.rect().contains(doc_pos):
            return

        target_color = rendered_image.pixelColor(doc_pos)
        path = QPainterPath()

        for x in range(rendered_image.width()):
            for y in range(rendered_image.height()):
                if rendered_image.pixelColor(x, y) == target_color:
                    path.addRect(QRect(x, y, 1, 1))

        self.canvas._update_selection_and_emit_size(path.simplified())

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass
