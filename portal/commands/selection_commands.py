from portal.core.command import Command
from PySide6.QtGui import QPainterPath, QImage, qRgba, qAlpha

class SelectOpaqueCommand(Command):
    def __init__(self, layer, canvas):
        self.layer = layer
        self.canvas = canvas
        self.previous_selection = self.canvas.selection_shape

    def execute(self):
        path = QPainterPath()
        image = self.layer.image
        image = image.convertToFormat(QImage.Format_ARGB32)

        for y in range(image.height()):
            for x in range(image.width()):
                if qAlpha(image.pixel(x, y)) > 0:
                    path.addRect(x, y, 1, 1)

        self.canvas._update_selection_and_emit_size(path.simplified())

    def undo(self):
        self.canvas._update_selection_and_emit_size(self.previous_selection)
