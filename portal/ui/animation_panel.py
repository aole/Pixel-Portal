from __future__ import annotations

import math
from typing import Iterable, Optional

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPalette
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationPanel(QWidget):
    """Timeline widget that exposes the current animation frame."""

    current_frame_changed = Signal(int)
    frame_double_clicked = Signal(int)
    loop_range_changed = Signal(int, int)
    keyframes_selection_changed = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(90)
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
        self._loop_start = 0
        self._loop_end = 12
        self._dragging_loop_start = False
        self._dragging_loop_end = False
        self._loop_start_handle_rect = QRectF()
        self._loop_end_handle_rect = QRectF()
        self._selected_keyframes: tuple[int, ...] = tuple()
        self._selection_anchor: Optional[int] = None

    def set_current_frame(self, frame: int) -> None:
        frame = max(0, int(frame))
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self._ensure_frame_visible(frame)
        self.update()

    def set_loop_range(self, start: int, end: int) -> None:
        self._loop_start = start
        self._loop_end = end
        self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            handle = self._loop_handle_hit_test(event.position())
            if handle == "start":
                self._dragging_loop_start = True
                self._is_dragging_frame = False
                event.accept()
                return
            if handle == "end":
                self._dragging_loop_end = True
                self._is_dragging_frame = False
                event.accept()
                return
            clicked_key = self._keyframe_at(event.position())
            if clicked_key is not None:
                self._handle_keyframe_click(clicked_key, event.modifiers())
                self._is_dragging_frame = True
                self._set_current_frame_from_x(event.position().x())
                event.accept()
                return
            self._is_dragging_frame = True
            if self._selected_keyframes:
                self._set_selected_keyframes(())
            self._set_current_frame_from_x(event.position().x())
            event.accept()
            return
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._last_pan_pos = QPointF(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if self._dragging_loop_start and event.buttons() & Qt.LeftButton:
            self._update_loop_start_from_x(event.position().x())
            event.accept()
            return
        if self._dragging_loop_end and event.buttons() & Qt.LeftButton:
            self._update_loop_end_from_x(event.position().x())
            event.accept()
            return
        if self._is_dragging_frame and event.buttons() & Qt.LeftButton:
            self._set_current_frame_from_x(event.position().x())
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
            self._dragging_loop_start = False
            self._dragging_loop_end = False
        elif event.button() == Qt.MiddleButton:
            self._is_panning = False
            self._last_pan_pos = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self._is_dragging_frame = False
        self._is_panning = False
        self._last_pan_pos = None
        self._dragging_loop_start = False
        self._dragging_loop_end = False
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            frame = self._frame_from_x(event.position().x())
            if frame is not None:
                self._set_current_frame_from_x(event.position().x())
                self.frame_double_clicked.emit(frame)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

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
        timeline_y = rect.bottom() - 30
        min_timeline_y = rect.top() + 40
        if timeline_y < min_timeline_y:
            timeline_y = min_timeline_y

        line_pen = QPen(self.palette().color(QPalette.WindowText))
        line_pen.setCosmetic(True)
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
        highlight_color = self.palette().color(QPalette.Highlight)

        # draw all frames
        for frame in range(start_frame, end_frame):
            tick_x = round(self._frame_to_x(frame))
            if tick_x < baseline_left - 2 or tick_x > baseline_right + 2:
                continue

            is_major = frame % self._major_tick_interval == 0
            marker_height = 13 if is_major else 9
            top = timeline_y - marker_height
            painter.drawLine(tick_x, timeline_y, tick_x, top)

            # draw frame label at major markers
            if is_major:
                text = str(frame)
                text_width = metrics.horizontalAdvance(text)
                text_height = metrics.height()
                text_top = timeline_y + 6
                max_text_top = rect.bottom() - text_height - 2
                if text_top > max_text_top:
                    text_top = max_text_top
                text_rect = QRect(
                    tick_x - text_width // 2,
                    text_top,
                    text_width,
                    text_height,
                )
                painter.drawText(text_rect, Qt.AlignCenter, text)

        loop_pen = QPen(highlight_color, 2)
        loop_pen.setCosmetic(True)
        loop_line_y = timeline_y - 20
        min_loop_y = rect.top() + 16
        if loop_line_y < min_loop_y:
            loop_line_y = min_loop_y

        start_pos = self._frame_to_x(self._loop_start)
        end_pos = self._frame_to_x(self._loop_end)
        self._loop_start_handle_rect = QRectF()
        self._loop_end_handle_rect = QRectF()

        # draw loop line
        if end_pos >= baseline_left and start_pos <= baseline_right:
            visible_start = max(baseline_left, int(round(start_pos)))
            visible_end = min(baseline_right, int(round(end_pos)))
            if visible_end <= visible_start:
                visible_end = visible_start + 1
            painter.setPen(loop_pen)
            painter.drawLine(visible_start, loop_line_y, visible_end, loop_line_y)

        handle_pen = QPen(self.palette().color(QPalette.WindowText))
        handle_pen.setCosmetic(True)
        handle_width = 10.0
        handle_height = 12.0

        # draw loop text
        start_center = round(start_pos)
        text = "Loop"
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        text_top = loop_line_y - (text_height + 2)
        text_rect = QRect(
            start_center + handle_width / 2 + 4,
            text_top,
            text_width,
            text_height,
        )
        painter.setPen(handle_pen)
        painter.drawText(text_rect, Qt.AlignLeft, text)
        
        # draw left loop handle
        if baseline_left <= start_pos <= baseline_right:
            start_rect = QRectF(
                start_center - handle_width / 2,
                loop_line_y - handle_height,
                handle_width,
                handle_height,
            )
            painter.setPen(handle_pen)
            painter.setBrush(highlight_color)
            painter.drawRoundedRect(start_rect, 3, 3)
            self._loop_start_handle_rect = start_rect

        # draw right loop handle
        if baseline_left <= end_pos <= baseline_right:
            end_center = round(end_pos)
            end_rect = QRectF(
                end_center - handle_width / 2,
                loop_line_y - handle_height,
                handle_width,
                handle_height,
            )
            painter.setPen(handle_pen)
            painter.setBrush(highlight_color)
            painter.drawRoundedRect(end_rect, 3, 3)
            self._loop_end_handle_rect = end_rect

        painter.setBrush(Qt.NoBrush)
        painter.setPen(line_pen)

        # draw current frame indicator line
        current_x = round(self._frame_to_x(self._current_frame))
        highlight_color = self.palette().color(QPalette.Highlight)
        highlight_pen = QPen(highlight_color, 2)
        highlight_pen.setCosmetic(True)
        painter.setPen(highlight_pen)
        painter.drawLine(current_x, timeline_y - 13, current_x, timeline_y + 5)

        # draw current frame indicator text
        label_text = str(self._current_frame)
        text_width = metrics.horizontalAdvance(label_text)
        text_height = metrics.height()
        padding_x = 6
        padding_y = 2
        total_width = text_width + padding_x * 2
        total_height = text_height + padding_y * 2

        label_gap = 6
        max_label_top = int(loop_line_y) + label_gap
        min_label_top = rect.top() + 4
        # display the current frame label as the same height as scale time labels.
        label_top = timeline_y + 4

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

        # draw keys
        if self._keyframes:
            outline_color = self.palette().color(QPalette.WindowText)
            selected_fill = QColor(255, 153, 0)
            unselected_fill = highlight_color

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

                fill_color = selected_fill if frame in self._selected_keyframes else unselected_fill
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

        painter.end()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _loop_handle_hit_test(self, pos: QPointF) -> Optional[str]:
        expanded_start = self._loop_start_handle_rect.adjusted(-4, -4, 4, 4)
        expanded_end = self._loop_end_handle_rect.adjusted(-4, -4, 4, 4)
        if expanded_start.contains(pos):
            return "start"
        if expanded_end.contains(pos):
            return "end"
        return None

    def _update_loop_start_from_x(self, x: float) -> None:
        frame = self._frame_from_x(x)
        if frame is None:
            return
        if frame < 0:
            frame = 0
        if frame >= self._loop_end:
            frame = self._loop_end - 1
        if frame == self._loop_start:
            return
        self._loop_start = frame
        if self._loop_end <= self._loop_start:
            self._loop_end = self._loop_start + 1
        self.loop_range_changed.emit(self._loop_start, self._loop_end)
        self.update()

    def _update_loop_end_from_x(self, x: float) -> None:
        frame = self._frame_from_x(x)
        if frame is None:
            return
        if frame <= self._loop_start:
            frame = self._loop_start + 1
        if frame == self._loop_end:
            return
        self._loop_end = frame
        self.loop_range_changed.emit(self._loop_start, self._loop_end)
        self.update()

    def _frame_to_x(self, frame: int) -> float:
        rect = self.rect()
        return rect.left() + self._left_margin + self._offset + frame * self._pixels_per_frame

    def _set_current_frame_from_x(self, x: float) -> None:
        frame = self._frame_from_x(x)
        if frame is None:
            return
        previous = self._current_frame
        self._current_frame = frame
        self._ensure_frame_visible(frame)
        if self._current_frame != previous:
            self.current_frame_changed.emit(self._current_frame)
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
            self._sync_selection_with_keyframes()
            return
        self._keyframes = keyframe_tuple
        self._sync_selection_with_keyframes()
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

    def selected_keyframes(self) -> tuple[int, ...]:
        return self._selected_keyframes

    def _handle_keyframe_click(self, frame: int, modifiers: Qt.KeyboardModifiers) -> None:
        if modifiers & Qt.ControlModifier:
            if frame in self._selected_keyframes:
                remaining = tuple(f for f in self._selected_keyframes if f != frame)
                self._selection_anchor = remaining[-1] if remaining else None
                self._set_selected_keyframes(remaining)
            else:
                combined = tuple(sorted((*self._selected_keyframes, frame)))
                self._selection_anchor = frame
                self._set_selected_keyframes(combined)
            return

        if modifiers & Qt.ShiftModifier and self._selection_anchor is not None:
            start = min(self._selection_anchor, frame)
            end = max(self._selection_anchor, frame)
            ranged = tuple(f for f in self._keyframes if start <= f <= end)
            self._set_selected_keyframes(ranged)
            return

        self._selection_anchor = frame
        self._set_selected_keyframes((frame,))

    def _set_selected_keyframes(self, frames: Iterable[int]) -> None:
        normalized = tuple(sorted({int(frame) for frame in frames if frame in self._keyframes}))
        if normalized != self._selected_keyframes:
            self._selected_keyframes = normalized
            selection_changed = True
        else:
            selection_changed = False

        if self._selection_anchor not in self._selected_keyframes:
            self._selection_anchor = (
                self._selected_keyframes[-1] if self._selected_keyframes else None
            )

        if selection_changed:
            self.keyframes_selection_changed.emit(self._selected_keyframes)
            self.update()

    def _sync_selection_with_keyframes(self) -> None:
        self._set_selected_keyframes(self._selected_keyframes)

    def _keyframe_at(self, pos: QPointF) -> Optional[int]:
        if not self._keyframes:
            return None
        rect = self.rect()
        baseline_left = rect.left() + self._left_margin
        baseline_right = rect.right() - self._right_margin
        if baseline_left > baseline_right:
            return None

        timeline_y = rect.bottom() - 30
        min_timeline_y = rect.top() + 40
        if timeline_y < min_timeline_y:
            timeline_y = min_timeline_y

        center_offset = 5
        center_y = timeline_y - center_offset
        half_height = 5
        half_width = 4
        hit_radius_x = half_width + 2
        hit_radius_y = half_height + 2
        x_pos = pos.x()
        y_pos = pos.y()
        if x_pos < baseline_left - hit_radius_x or x_pos > baseline_right + hit_radius_x:
            return None
        if abs(y_pos - center_y) > hit_radius_y:
            return None

        for frame in self._keyframes:
            key_x = round(self._frame_to_x(frame))
            if abs(key_x - x_pos) <= hit_radius_x:
                return frame
        return None
