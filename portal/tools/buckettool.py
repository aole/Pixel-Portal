from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool
from portal.core.command import FillCommand


class BucketTool(BaseTool):
    name = "Bucket"
    icon = "icons/toolbucket.png"
    shortcut = "b"

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        command = FillCommand(
            document=self.canvas.document,
            layer=active_layer,
            fill_pos=doc_pos,
            fill_color=self.canvas.drawing_context.pen_color,
            selection_shape=self.canvas.selection_shape,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
        )
        self.command_generated.emit(command)
        self.canvas.update()
        