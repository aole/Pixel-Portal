from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool
from ..command import FillCommand


class BucketTool(BaseTool):
    name = "Bucket"
    icon = "icons/toolbucket.png"
    shortcut = "b"

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        fill_data = {
            "fill_pos": doc_pos,
            "fill_color": self.canvas._pen_color,
            "selection_shape": self.canvas.selection_shape,
            "mirror_x": self.canvas._mirror_x,
            "mirror_y": self.canvas._mirror_y,
        }
        self.command_generated.emit(("fill", fill_data))
        self.canvas.update()
        