from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent

from portal.tools.basetool import BaseTool


class BucketTool(BaseTool):
    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return

        doc_width = self.app.document.width
        doc_height = self.app.document.height

        # A set to keep track of points we've already started a fill from
        # to avoid redundant operations, e.g., on the mirror axis itself.
        processed_points = set()

        points_to_fill = [doc_pos]
        if self.app.mirror_x:
            points_to_fill.append(QPoint(doc_width - 1 - doc_pos.x(), doc_pos.y()))
        if self.app.mirror_y:
            points_to_fill.append(QPoint(doc_pos.x(), doc_height - 1 - doc_pos.y()))
        if self.app.mirror_x and self.app.mirror_y:
            points_to_fill.append(QPoint(doc_width - 1 - doc_pos.x(), doc_height - 1 - doc_pos.y()))

        for point in points_to_fill:
            if tuple(point.toTuple()) not in processed_points:
                self.canvas.drawing.flood_fill(point, self.canvas.selection_shape)
                processed_points.add(tuple(point.toTuple()))

        active_layer.on_image_change.emit()
        self.canvas.app.add_undo_state()
        self.canvas.update()
        