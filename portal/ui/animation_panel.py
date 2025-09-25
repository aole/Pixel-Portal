from __future__ import annotations

import math
from typing import Iterable, Optional

from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QPalette
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationPanel(QWidget):
    """Timeline widget that exposes the current animation frame."""

    frame_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._current_frame = 0
        self._pixels_per_frame = 10.0
        self._offset = 0.0
        self._left_margin = 20
        self._right_margin = 20
        self._major_tick_interval = 5

        self._is_dragging_frame = False
        self._is_panning = False
        self._last_pan_pos: Optional[QPointF] = None
        self._keyframes: tuple[int, ...] = tuple()

    def set_current_frame(self, frame: int) -> None:
        frame = max(0, int(frame))
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self._ensure_frame_visible(frame)
        self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self._is_dragging_frame = True
            self._select_frame_at(event.position().x())
            event.accept()
            return
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._last_pan_pos = QPointF(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if self._is_dragging_frame and event.buttons() & Qt.LeftButton:
            self._select_frame_at(event.position().x())
            event.accept()
            return
        if self._is_panning and event.buttons() & Qt.MiddleButton and self._last_pan_pos:
            delta_x = event.position().x() - self._last_pan_pos.x()
            self._set_offset(self._offset + delta_x)
            self._last_pan_pos = QPointF(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self._is_dragging_frame = False
        elif event.button() == Qt.MiddleButton:
            self._is_panning = False
            self._last_pan_pos = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self._is_dragging_frame = False
        self._is_panning = False
        self._last_pan_pos = None
        super().leaveEvent(event)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        self._clamp_offset()
        super().resizeEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect()
        if rect.height() <= 0 or rect.width() <= 0:
            return

        self._clamp_offset()

        baseline_left = rect.left() + self._left_margin
        baseline_right = rect.right() - self._right_margin
        timeline_y = rect.center().y() + 10

        line_pen = QPen(self.palette().color(QPalette.WindowText))
        painter.setPen(line_pen)
        painter.drawLine(baseline_left, timeline_y, baseline_right, timeline_y)

        available_width = max(0, baseline_right - baseline_left)
        visible_left = max(0.0, -self._offset)
        visible_right = visible_left + available_width

        start_frame = max(0, int(math.floor(visible_left / self._pixels_per_frame)) - 1)
        end_frame = max(
            start_frame + 1,
            int(math.ceil(visible_right / self._pixels_per_frame)) + 2,
        )

        metrics = painter.fontMetrics()

        for frame in range(start_frame, end_frame):
            tick_x = round(self._frame_to_x(frame))
            if tick_x < baseline_left - 2 or tick_x > baseline_right + 2:
                continue

            is_major = frame % self._major_tick_interval == 0
            marker_height = 13 if is_major else 9
            top = timeline_y - marker_height
            painter.drawLine(tick_x, timeline_y, tick_x, top)

            if is_major:
                text = str(frame)
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()
                text_rect = QRect(
                    tick_x - text_width // 2,
                    top - text_height - 2,
                    text_width,
                    text_height,
                )
                painter.drawText(text_rect, Qt.AlignCenter, text)

        if self._keyframes:
            outline_color = self.palette().color(QPalette.WindowText)
            base_fill = self.palette().color(QPalette.Highlight)
            inactive_fill = base_fill.lighter(165)

            outline_pen = QPen(outline_color)
            outline_pen.setCosmetic(True)

            half_width = 4
            half_height = 5
            center_offset = 5
            min_x = baseline_left - half_width - 1
            max_x = baseline_right + half_width + 1

            for frame in self._keyframes:
                key_x = round(self._frame_to_x(frame))
                if key_x < min_x or key_x > max_x:
                    continue

                fill_color = base_fill if frame == self._current_frame else inactive_fill
                painter.setPen(outline_pen)
                painter.setBrush(fill_color)

                center_y = timeline_y - center_offset
                points = [
                    QPointF(key_x, center_y - half_height),
                    QPointF(key_x + half_width, center_y),
                    QPointF(key_x, center_y + half_height),
                    QPointF(key_x - half_width, center_y),
                ]
                painter.drawPolygon(points)

        # draw current frame indicator line
        current_x = round(self._frame_to_x(self._current_frame))
        highlight_color = self.palette().color(QPalette.Highlight)
        highlight_pen = QPen(highlight_color, 2)
        highlight_pen.setCosmetic(True)
        painter.setPen(highlight_pen)
        painter.drawLine(current_x, timeline_y - 13, current_x, timeline_y + 4)

        # draw current frame indicator text
        label_text = str(self._current_frame)
        text_width = metrics.horizontalAdvance(label_text)
        text_height = metrics.height()
        padding_x = 6
        padding_y = 2
        total_width = text_width + padding_x * 2
        total_height = text_height + padding_y * 2

        major_marker_height = 13
        marker_top = timeline_y - major_marker_height
        label_text_top = marker_top - text_height - 2
        label_top = label_text_top - padding_y

        label_left = current_x - total_width // 2
        min_left = rect.left() + 4
        max_left = rect.right() - total_width - 4
        if max_left < min_left:
            max_left = min_left
        label_left = max(min_left, min(label_left, max_left))
        label_rect = QRect(label_left, label_top, total_width, total_height)

        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight_color)
        painter.drawRoundedRect(label_rect, 4, 4)

        text_rect = label_rect.adjusted(padding_x, padding_y, -padding_x, -padding_y)
        painter.setPen(QPen(Qt.white))
        painter.drawText(text_rect, Qt.AlignCenter, label_text)

        painter.end()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _frame_to_x(self, frame: int) -> float:
        rect = self.rect()
        return rect.left() + self._left_margin + self._offset + frame * self._pixels_per_frame

    def _select_frame_at(self, x: float) -> None:
        frame = self._frame_from_x(x)
        if frame is None:
            return
        previous = self._current_frame
        self._current_frame = frame
        self._ensure_frame_visible(frame)
        if self._current_frame != previous:
            self.frame_selected.emit(self._current_frame)
        self.update()

    def _frame_from_x(self, x: float) -> Optional[int]:
        rect = self.rect()
        if rect.width() <= 0:
            return None
        relative = x - rect.left() - self._left_margin - self._offset
        frame_value = relative / self._pixels_per_frame
        frame = int(round(frame_value))
        return max(0, frame)

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self._clamp_offset()
        self.update()

    def set_keyframes(self, frames: Iterable[int]) -> None:
        normalized: list[int] = []
        seen: set[int] = set()
        for frame in frames:
            try:
                value = int(frame)
            except (TypeError, ValueError):
                continue
            if value < 0:
                value = 0
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        normalized.sort()
        keyframe_tuple = tuple(normalized)
        if keyframe_tuple == self._keyframes:
            return
        self._keyframes = keyframe_tuple
        self.update()

    def _clamp_offset(self) -> None:
        rect = self.rect()
        available_width = rect.width() - self._left_margin - self._right_margin
        if available_width <= 0:
            self._offset = 0.0
            return

        if self._offset > 0:
            self._offset = 0.0

    def _ensure_frame_visible(self, frame: int) -> None:
        rect = self.rect()
        available_width = rect.width() - self._left_margin - self._right_margin
        if available_width <= 0:
            return

        target = frame * self._pixels_per_frame
        left_edge = max(0.0, -self._offset)
        right_edge = left_edge + available_width

        if target < left_edge:
            self._offset = -target
        elif target > right_edge:
            self._offset = available_width - target

        self._clamp_offset()
