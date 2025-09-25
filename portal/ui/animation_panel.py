from __future__ import annotations

import math
from typing import Iterable, Optional

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QPalette
from PySide6.QtWidgets import QSizePolicy, QWidget


class AnimationPanel(QWidget):
    """Timeline widget that exposes the current animation frame."""

    frame_selected = Signal(int)
    frame_double_clicked = Signal(int)
    loop_range_changed = Signal(int, int)
    keyframe_selection_changed = Signal(tuple)

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
        self._selection_anchor: int | None = None

    @property
    def selected_keyframes(self) -> tuple[int, ...]:
        return self._selected_keyframes

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
            self._is_dragging_frame = True
            modifiers = event.modifiers()
            keyframe = self._keyframe_hit_test(event.position())
            if keyframe is not None:
                if modifiers & Qt.ShiftModifier:
                    self._extend_selection_to(keyframe)
                elif modifiers & Qt.ControlModifier:
                    self._toggle_keyframe_selection(keyframe)
                else:
                    self._select_single_keyframe(keyframe)
                self._select_frame_at(event.position().x())
                event.accept()
                return
            if not (modifiers & (Qt.ControlModifier | Qt.ShiftModifier)):
                if self._selected_keyframes:
                    self._set_selected_keyframes(())
                self._selection_anchor = None
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
        if self._dragging_loop_start and event.buttons() & Qt.LeftButton:
            self._update_loop_start_from_x(event.position().x())
            event.accept()
            return
        if self._dragging_loop_end and event.buttons() & Qt.LeftButton:
            self._update_loop_end_from_x(event.position().x())
            event.accept()
            return
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
                self._select_frame_at(event.position().x())
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
        timeline_y = rect.bottom() - 24
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
        loop_line_y = timeline_y - 26
        min_loop_y = rect.top() + 16
        if loop_line_y < min_loop_y:
            loop_line_y = min_loop_y

        start_pos = self._frame_to_x(self._loop_start)
        end_pos = self._frame_to_x(self._loop_end)
        self._loop_start_handle_rect = QRectF()
        self._loop_end_handle_rect = QRectF()

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
        handle_height = 18.0

        if baseline_left <= start_pos <= baseline_right:
            start_center = round(start_pos)
            start_rect = QRectF(
                start_center - handle_width / 2,
                loop_line_y - handle_height / 2,
                handle_width,
                handle_height,
            )
            painter.setPen(handle_pen)
            painter.setBrush(highlight_color)
            painter.drawRoundedRect(start_rect, 3, 3)
            self._loop_start_handle_rect = start_rect

        if baseline_left <= end_pos <= baseline_right:
            end_center = round(end_pos)
            end_rect = QRectF(
                end_center - handle_width / 2,
                loop_line_y - handle_height / 2,
                handle_width,
                handle_height,
            )
            painter.setPen(handle_pen)
            painter.setBrush(highlight_color)
            painter.drawRoundedRect(end_rect, 3, 3)
            self._loop_end_handle_rect = end_rect

        painter.setBrush(Qt.NoBrush)
        painter.setPen(line_pen)

        if self._keyframes:
            outline_color = self.palette().color(QPalette.WindowText)
            base_fill = highlight_color
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

                is_selected = frame in self._selected_keyframes or (
                    not self._selected_keyframes and frame == self._current_frame
                )
                fill_color = base_fill if is_selected else inactive_fill
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

    def _keyframe_hit_test(self, pos: QPointF) -> Optional[int]:
        if not self._keyframes:
            return None
        rect = self.rect()
        baseline_left = rect.left() + self._left_margin
        baseline_right = rect.right() - self._right_margin
        if pos.x() < baseline_left - 8 or pos.x() > baseline_right + 8:
            return None

        timeline_y = rect.bottom() - 24
        min_timeline_y = rect.top() + 40
        if timeline_y < min_timeline_y:
            timeline_y = min_timeline_y
        center_y = timeline_y - 5
        half_width = 4
        half_height = 5

        hit_rect = QRectF(
            pos.x() - half_width,
            pos.y() - half_height,
            half_width * 2,
            half_height * 2,
        )

        closest: Optional[int] = None
        min_distance: float = float("inf")
        for frame in self._keyframes:
            key_x = self._frame_to_x(frame)
            key_rect = QRectF(
                key_x - half_width,
                center_y - half_height,
                half_width * 2,
                half_height * 2,
            )
            if not key_rect.adjusted(-2, -2, 2, 2).intersects(hit_rect):
                continue
            distance = abs(key_x - pos.x())
            if distance < min_distance:
                min_distance = distance
                closest = frame
        return closest

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
        self._sync_selection_with_available_keyframes()
        self.update()

    def _set_selected_keyframes(self, frames: Iterable[int]) -> None:
        unique = {int(frame) for frame in frames}
        normalized = tuple(sorted(unique))
        if normalized == self._selected_keyframes:
            return
        self._selected_keyframes = normalized
        self.keyframe_selection_changed.emit(self._selected_keyframes)
        self.update()

    def _select_single_keyframe(self, frame: int) -> None:
        self._selection_anchor = frame
        self._set_selected_keyframes((frame,))

    def _toggle_keyframe_selection(self, frame: int) -> None:
        current = list(self._selected_keyframes)
        if frame in current:
            current.remove(frame)
            if self._selection_anchor == frame:
                self._selection_anchor = current[-1] if current else None
        else:
            current.append(frame)
            self._selection_anchor = frame
        self._set_selected_keyframes(current)

    def _extend_selection_to(self, frame: int) -> None:
        if self._selection_anchor is None:
            self._select_single_keyframe(frame)
            return
        lower = min(self._selection_anchor, frame)
        upper = max(self._selection_anchor, frame)
        frames = [key for key in self._keyframes if lower <= key <= upper]
        if not frames:
            self._select_single_keyframe(frame)
            return
        self._set_selected_keyframes(frames)

    def _sync_selection_with_available_keyframes(self) -> None:
        if not self._selected_keyframes:
            if self._selection_anchor not in self._keyframes:
                self._selection_anchor = None
            return
        available = [frame for frame in self._selected_keyframes if frame in self._keyframes]
        if not available:
            self._selection_anchor = None
            self._set_selected_keyframes(())
            return
        if self._selection_anchor not in self._keyframes:
            self._selection_anchor = available[-1]
        if tuple(available) != self._selected_keyframes:
            self._set_selected_keyframes(available)

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
