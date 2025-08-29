from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool
from ..command import FillCommand


class BucketTool(BaseTool):
    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return

        command = FillCommand(
            document=self.app.document,
            layer=active_layer,
            fill_pos=doc_pos,
            fill_color=self.app.pen_color,
            selection_shape=self.canvas.selection_shape,
            drawing=self.canvas.drawing,
            mirror_x=self.app.mirror_x,
            mirror_y=self.app.mirror_y,
        )
        self.app.execute_command(command)
        self.canvas.update()
        