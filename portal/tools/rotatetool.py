import math
import logging

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QCursor, QMouseEvent, QPainter, QTransform

from portal.core.command import RotateCommand
from portal.tools.basetool import BaseTool


class RotateTool(BaseTool):
    name = "Rotate"
    icon = "icons/toolrotate.png"
    shortcut = "r"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.center = QPoint()
        self.original_image = None
        self.before_image = None
        self.rotating = False
        self.cursor = QCursor(Qt.CrossCursor)
        logging.basicConfig(level=logging.INFO)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        logging.info("RotateTool.mousePressEvent")
        self.canvas.temp_image_replaces_active_layer = True
        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        self.before_image = active_layer.image.copy()

        if self.canvas.selection_shape:
            self.command_generated.emit(("cut_selection", "rotate_tool_start"))
            self.center = self.canvas.selection_shape.boundingRect().center().toPoint()
            self.original_image = self.canvas.original_image
        else:
            self.command_generated.emit(("cut_selection", "rotate_tool_start_no_selection"))
            self.center = active_layer.image.rect().center()
            self.original_image = active_layer.image.copy()

        self.rotating = True

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        logging.info("RotateTool.mouseMoveEvent")
        if not self.rotating or self.original_image is None:
            return

        angle = self.calculate_angle(doc_pos)
        transform = QTransform().translate(self.center.x(), self.center.y()).rotate(angle).translate(-self.center.x(), -self.center.y())

        if self.canvas.selection_shape:
            # This part needs to be implemented properly for selection rotation preview
            self.canvas.temp_image.fill(Qt.transparent)
            painter = QPainter(self.canvas.temp_image)
            painter.setTransform(transform)
            painter.drawImage(QRect(self.center - QPoint(self.original_image.width() / 2, self.original_image.height() / 2), self.original_image.size()), self.original_image)
            painter.end()
        else:
            self.canvas.temp_image = self.original_image.transformed(transform, Qt.FastTransformation)

        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        logging.info("RotateTool.mouseReleaseEvent")
        if not self.rotating or self.original_image is None or self.before_image is None:
            return

        angle = self.calculate_angle(doc_pos)
        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        command = RotateCommand(
            layer=active_layer,
            before_rotate_image=self.before_image,
            rotated_image=self.original_image,
            angle=angle,
            center=self.center,
            selection=self.canvas.selection_shape,
        )
        self.command_generated.emit(command)

        self.rotating = False
        self.original_image = None
        self.before_image = None
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()

    def calculate_angle(self, pos: QPoint):
        delta = pos - self.center
        return math.degrees(math.atan2(delta.y(), delta.x()))
