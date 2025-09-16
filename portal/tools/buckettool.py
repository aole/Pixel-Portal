from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool
from portal.core.command import FillCommand


class BucketTool(BaseTool):
    name = "Bucket"
    icon = "icons/toolbucket.png"
    shortcut = "f"
    category = "draw"

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            return

        pos = doc_pos
        if self.canvas.tile_preview_enabled:
            doc_width = self.canvas.document.width
            doc_height = self.canvas.document.height
            pos = QPoint(doc_pos.x() % doc_width, doc_pos.y() % doc_height)

        command = FillCommand(
            document=self.canvas.document,
            layer=active_layer,
            fill_pos=pos,
            fill_color=self.canvas.drawing_context.pen_color,
            selection_shape=self.canvas.selection_shape,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
        )
        self.command_generated.emit(command)
        self.canvas.update()
        