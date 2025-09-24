from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationTimelinePanel(QWidget):
    """A simple timeline panel rendered above the status bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):  # noqa: N802 - Qt override naming convention
        painter = QPainter(self)
        rect = self.rect()

        background_color = self.palette().color(QPalette.Base)
        painter.fillRect(rect, background_color)

        mid_y = rect.center().y()
        painter.setPen(QPen(self.palette().color(QPalette.Mid)))
        painter.drawLine(rect.left(), mid_y, rect.right(), mid_y)

        tick_pen = QPen(self.palette().color(QPalette.Text))
        painter.setPen(tick_pen)

        spacing = 10
        font_metrics = painter.fontMetrics()

        for index, x in enumerate(range(rect.left(), rect.right(), spacing)):
            is_major_tick = index % 5 == 0
            tick_height = 13 if is_major_tick else 10
            painter.drawLine(x, mid_y - tick_height, x, mid_y)

            if is_major_tick:
                text_rect = QRectF(
                    x - spacing * 2,
                    mid_y - tick_height - font_metrics.height() - 2,
                    spacing * 4,
                    font_metrics.height(),
                )
                painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignBottom, str(index))

        painter.end()
