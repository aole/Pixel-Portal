from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):  # noqa: N802 (Qt API requirement)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect()
        painter.fillRect(rect, self.palette().window())

        timeline_y = rect.center().y()

        line_pen = QPen(self.palette().mid().color())
        line_pen.setWidth(1)
        painter.setPen(line_pen)
        painter.drawLine(rect.left(), timeline_y, rect.right(), timeline_y)

        tick_pen = QPen(self.palette().mid().color())
        painter.setPen(tick_pen)

        font = QFont(self.font())
        font.setPointSizeF(font.pointSizeF() * 0.9)
        painter.setFont(font)

        for index, x in enumerate(range(rect.left(), rect.right(), 10)):
            if index % 5 == 0:
                tick_height = 13
                painter.drawLine(x, timeline_y - tick_height, x, timeline_y)

                painter.drawText(
                    x - 20,
                    timeline_y - tick_height - 18,
                    40,
                    18,
                    Qt.AlignCenter,
                    str(index // 5),
                )
            else:
                tick_height = 10
                painter.drawLine(x, timeline_y - tick_height, x, timeline_y)

        painter.end()

