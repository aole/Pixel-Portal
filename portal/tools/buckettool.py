from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool


class BucketTool(BaseTool):
    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        self.canvas.drawing_logic.flood_fill(doc_pos, self.canvas.selection_shape)
        active_layer.on_image_change.emit()
        self.canvas.app.add_undo_state()
        self.canvas.update()
