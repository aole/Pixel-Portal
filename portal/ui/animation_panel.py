from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QPalette
from PySide6.QtWidgets import QWidget, QSizePolicy


class AnimationPanel(QWidget):
    """Simple timeline panel showing equally spaced frame markers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect()
        if rect.height() <= 0 or rect.width() <= 0:
            return

        timeline_y = rect.center().y()

        pen = QPen(self.palette().color(QPalette.WindowText))
        painter.setPen(pen)

        painter.drawLine(rect.left(), timeline_y, rect.right(), timeline_y)

        step = 10
        for index, x in enumerate(range(rect.left() + 10, rect.right() + 1, step)):
            if index % 5 == 0:
                marker_height = 13
            else:
                marker_height = 10

            top = timeline_y - marker_height
            painter.drawLine(x, timeline_y, x, top)

            if index % 5 == 0:
                text = str(index)
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()
                text_rect = QRect(
                    x - text_width // 2,
                    top - text_height - 2,
                    text_width,
                    text_height,
                )
                painter.drawText(text_rect, Qt.AlignCenter, text)

        painter.end()
