from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationPanel(QWidget):
    """Simple timeline visualisation shown above the status bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(48)

    def sizeHint(self):
        return QSize(200, 36)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect()
        painter.fillRect(rect, self.palette().window())

        mid_y = rect.center().y()
        text_color = self.palette().windowText()

        timeline_pen = QPen(text_color, 1)
        painter.setPen(timeline_pen)
        painter.drawLine(rect.left(), mid_y, rect.right(), mid_y)

        for x in range(rect.left(), rect.right() + 1, 10):
            frame_index = (x - rect.left()) // 10
            is_major = frame_index % 5 == 0
            line_height = 13 if is_major else 10

            half_height = line_height // 2
            top = mid_y - half_height
            bottom = mid_y + (line_height - half_height)
            painter.drawLine(x, top, x, bottom)

            if is_major:
                text = str(frame_index)
                label_bottom = top - 4
                if label_bottom > 0:
                    label_rect = QRect(x - 20, 0, 40, label_bottom)
                    painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignBottom, text)

        painter.end()
