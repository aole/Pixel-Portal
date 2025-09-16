from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QImage


class DrawingContext(QObject):
    tool_changed = Signal(str)
    pen_color_changed = Signal(QColor)
    pen_width_changed = Signal(int)
    brush_type_changed = Signal(str)
    mirror_x_changed = Signal(bool)
    mirror_y_changed = Signal(bool)
    mirror_x_position_changed = Signal(float)
    mirror_y_position_changed = Signal(float)
    pattern_brush_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self.tool = "Pen"
        self.previous_tool = "Pen"
        self.pen_color = QColor("black")
        self.pen_width = 1
        self.brush_type = "Circular"
        self.pattern_brush: QImage | None = None
        self.mirror_x = False
        self.mirror_y = False
        self.mirror_x_position: float | None = None
        self.mirror_y_position: float | None = None

    @Slot(bool)
    def set_mirror_x(self, enabled):
        self.mirror_x = enabled
        self.mirror_x_changed.emit(self.mirror_x)

    @Slot(bool)
    def set_mirror_y(self, enabled):
        self.mirror_y = enabled
        self.mirror_y_changed.emit(self.mirror_y)

    @Slot(float)
    def set_mirror_x_position(self, position):
        if position == self.mirror_x_position:
            return
        self.mirror_x_position = position
        self.mirror_x_position_changed.emit(position)

    @Slot(float)
    def set_mirror_y_position(self, position):
        if position == self.mirror_y_position:
            return
        self.mirror_y_position = position
        self.mirror_y_position_changed.emit(position)

    @Slot(int)
    def set_pen_width(self, width):
        self.pen_width = width
        self.pen_width_changed.emit(self.pen_width)

    @Slot(str)
    def set_brush_type(self, brush_type):
        self.brush_type = brush_type
        self.brush_type_changed.emit(self.brush_type)

    @Slot(str)
    def set_tool(self, tool):
        if self.tool != "Picker":
            self.previous_tool = self.tool
        self.tool = tool
        self.tool_changed.emit(self.tool)

    @Slot(QColor)
    def set_pen_color(self, color):
        # This slot can accept a string or a QColor
        if isinstance(color, str):
            self.pen_color = QColor(color)
        else:
            self.pen_color = color
        self.pen_color_changed.emit(self.pen_color)

    @Slot(QImage)
    def set_pattern_brush(self, image):
        self.pattern_brush = image
        self.pattern_brush_changed.emit(self.pattern_brush)
        self.set_brush_type("Pattern")
