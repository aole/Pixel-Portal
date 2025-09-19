"""Interactive timeline widget for displaying animation frames and keys."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Iterable, List, Set

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QBrush,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPalette,
    QPolygonF,
)
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget

from portal.core.animation_player import DEFAULT_TOTAL_FRAMES


@dataclass
class _TimelineLayout:
    """Pre-computed geometry values for rendering the timeline."""

    max_frame: int
    spacing: float
    track_y: float
    usable_width: float
    max_offset: float
    scrub_top: float
    scrub_bottom: float


@dataclass
class _KeyDragState:
    """Runtime information captured while dragging keyed frames."""

    is_dragging: bool = False
    candidate_frame: int | None = None
    candidate_modifiers: Qt.KeyboardModifiers = Qt.NoModifier
    initial_keys: Set[int] = field(default_factory=set)
    other_keys: Set[int] = field(default_factory=set)
    all_keys: Set[int] = field(default_factory=set)
    start_frame: int = 0
    last_offset: int = 0
    has_moved: bool = False
    defer_selection: bool = False
    follow_current_frame: bool = False
    start_current_frame: int = 0

    def clear(self) -> None:
        self.is_dragging = False
        self.candidate_frame = None
        self.candidate_modifiers = Qt.NoModifier
        self.initial_keys.clear()
        self.other_keys.clear()
        self.all_keys.clear()
        self.start_frame = 0
        self.last_offset = 0
        self.has_moved = False
        self.defer_selection = False
        self.follow_current_frame = False
        self.start_current_frame = 0

    @property
    def pending(self) -> bool:
        """Return True if a drag candidate is waiting to activate."""

        return self.candidate_frame is not None

class AnimationTimelineWidget(QWidget):
    """A minimal animation timeline widget displaying frames and keyed positions.

    The widget renders a horizontal scale with equally spaced frame markers. Keys
    are shown as dots aligned to their frame while a triangular scrub indicator
    beneath the scale highlights the currently selected frame. Context menu
    actions allow basic key management.
    """

    keys_changed = Signal(list)
    selected_keys_changed = Signal(list)
    current_frame_changed = Signal(int)
    key_add_requested = Signal(int)
    key_remove_requested = Signal(int)
    keys_remove_requested = Signal(list)
    key_copy_requested = Signal(int)
    key_paste_requested = Signal(int)
    frame_insert_requested = Signal(int)
    frame_delete_requested = Signal(int)
    key_move_requested = Signal(list, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_total_frames = 0
        self._playback_total_frames = DEFAULT_TOTAL_FRAMES
        self._keys: Set[int] = {0}
        self._selected_keys: Set[int] = set()
        self._selection_anchor: int | None = None
        self._current_frame = 0
        self._margin = 24
        self._tick_height = 36
        self._preferred_frame_spacing = 16.0
        self._is_dragging = False
        self._is_panning = False
        self._has_copied_key = False
        self._scroll_offset = 0.0
        self._last_pan_x = 0.0
        self._scrub_gap = 10.0
        self._scrub_channel_height = 12.0
        self._scrub_triangle_half_width = 8.0
        self._scrub_tolerance = 4.0
        self._key_hit_padding = 4.0
        self._document_frame_count = 1
        self._drag_state = _KeyDragState()
        self._drag_state.clear()

        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        return QSize(800, 120)

    def total_frames(self) -> int:
        """Return the highest frame index currently represented."""

        highest_key = max(self._keys) if self._keys else 0
        return max(self._base_total_frames, highest_key)

    def playback_total_frames(self) -> int:
        """Return the playback range (frame count) used for highlighting."""

        return self._playback_total_frames

    def set_total_frames(self, frame_count: int) -> None:
        """Define the minimum highest frame index displayed by the timeline."""

        frame_count = max(0, int(frame_count))
        if frame_count == self._base_total_frames:
            return
        self._base_total_frames = frame_count
        self.updateGeometry()
        self.update()

    def set_playback_total_frames(self, frame_count: int) -> None:
        """Define the playback frame count used for colouring the timeline."""

        frame_count = max(1, int(frame_count))
        if frame_count == self._playback_total_frames:
            return
        self._playback_total_frames = frame_count
        self.update()

    def keys(self) -> List[int]:
        """Return the keyed frames sorted ascending."""

        return sorted(self._keys)

    def selected_keys(self) -> List[int]:
        """Return the currently selected keyed frames sorted ascending."""

        return sorted(self._selected_keys)

    def set_keys(self, frames: Iterable[int]) -> None:
        """Replace the existing keyed frames with *frames*."""

        new_keys = {max(0, int(frame)) for frame in frames}
        if not new_keys:
            new_keys = {0}
        added_keys = new_keys - self._keys
        if new_keys == self._keys:
            return
        self._keys = new_keys
        self._clear_key_drag_state()
        self._ensure_base_frame(max(self._keys))
        if added_keys:
            self._set_selection(set(), anchor=None)
        else:
            self._sync_selection_with_keys()
        self.keys_changed.emit(self.keys())
        self.update()

    def set_selected_keys(self, frames: Iterable[int]) -> None:
        """Replace the selected keyed frames with *frames*."""

        requested = {int(frame) for frame in frames}
        self._set_selection(requested)

    def has_copied_key(self) -> bool:
        return self._has_copied_key

    def set_has_copied_key(self, has_key: bool) -> None:
        has_key = bool(has_key)
        if has_key == self._has_copied_key:
            return
        self._has_copied_key = has_key

    def set_document_frame_count(self, frame_count: int) -> None:
        frame_count = max(0, int(frame_count))
        if frame_count == self._document_frame_count:
            return
        self._document_frame_count = frame_count

    def current_frame(self) -> int:
        return self._current_frame

    def set_current_frame(self, frame: int) -> None:
        self._set_current_frame_internal(frame, emit_signal=True)

    def _set_current_frame_internal(self, frame: int, *, emit_signal: bool) -> None:
        frame = max(0, int(frame))
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self._ensure_base_frame(frame)
        self._ensure_frame_visible(frame)
        if emit_signal:
            self.current_frame_changed.emit(self._current_frame)
        self.update()

    def add_key(self, frame: int) -> None:
        frame = max(0, int(frame))
        if frame in self._keys:
            return
        self._keys.add(frame)
        self._ensure_base_frame(frame)
        self._set_selection(set(), anchor=None)
        self.keys_changed.emit(self.keys())
        self.update()

    def remove_key(self, frame: int) -> None:
        frame = int(frame)
        if frame not in self._keys:
            return
        if len(self._keys) == 1:
            return
        self._keys.remove(frame)
        self._sync_selection_with_keys()
        self.keys_changed.emit(self.keys())
        self.update()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt naming
        super().paintEvent(event)
        layout = self._calculate_layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font_metrics = painter.fontMetrics()

        palette = self.palette()
        guide_color = palette.color(QPalette.Mid)
        frame_color = palette.color(QPalette.WindowText)
        key_color = palette.color(QPalette.Highlight)
        key_border = key_color.darker(130)
        selected_key_color = QColor("#FFAA41")
        selected_key_border = selected_key_color.darker(130)
        current_color = palette.color(QPalette.Highlight)

        def muted(color: QColor) -> QColor:
            muted_color = QColor(color)
            alpha = color.alpha()
            if alpha == 0:
                return muted_color
            new_alpha = max(0, min(255, int(round(alpha * 0.45))))
            muted_color.setAlpha(new_alpha)
            return muted_color

        muted_frame_color = muted(frame_color)
        muted_key_color = muted(key_color)
        muted_key_border = muted(key_border)
        muted_selected_key_color = muted(selected_key_color)
        muted_selected_key_border = muted(selected_key_border)

        active_tick_pen = QPen(frame_color, 1.5)
        inactive_tick_pen = QPen(muted_frame_color, 1.5)
        active_number_pen = QPen(frame_color)
        inactive_number_pen = QPen(muted_frame_color)
        active_key_pen = QPen(key_border, 1.5)
        inactive_key_pen = QPen(muted_key_border, 1.5)
        active_key_brush = QBrush(key_color)
        inactive_key_brush = QBrush(muted_key_color)
        active_selected_key_pen = QPen(selected_key_border, 1.5)
        inactive_selected_key_pen = QPen(muted_selected_key_border, 1.5)
        active_selected_key_brush = QBrush(selected_key_color)
        inactive_selected_key_brush = QBrush(muted_selected_key_color)

        playback_last_index = max(0, self._playback_total_frames - 1)

        visible_start_x = self._margin
        visible_end_x = self.width() - self._margin

        # Draw the main timeline bar.
        painter.setPen(QPen(guide_color, 2))
        painter.drawLine(visible_start_x, layout.track_y, visible_end_x, layout.track_y)

        # Draw frame ticks.
        for frame in range(layout.max_frame + 1):
            x = self._margin + frame * layout.spacing - self._scroll_offset
            if x < visible_start_x - layout.spacing:
                continue
            if x > visible_end_x + layout.spacing:
                break
            tick_height = self._tick_height
            is_major_tick = frame % 5 == 0
            if is_major_tick:
                tick_height = int(self._tick_height * 1.4)
            is_within_playback = frame <= playback_last_index
            painter.setPen(active_tick_pen if is_within_playback else inactive_tick_pen)
            painter.drawLine(
                QPointF(x, layout.track_y - tick_height / 2),
                QPointF(x, layout.track_y + tick_height / 2),
            )
            if is_major_tick and layout.spacing >= 8:
                label_height = font_metrics.height()
                number_rect = QRectF(
                    x - layout.spacing / 2,
                    layout.track_y - tick_height / 2 - label_height - 4,
                    layout.spacing,
                    label_height,
                )
                painter.setPen(active_number_pen if is_within_playback else inactive_number_pen)
                painter.drawText(number_rect, Qt.AlignHCenter | Qt.AlignBottom, str(frame))

        # Draw keyed frames as circles.
        for frame in self.keys():
            x = self._margin + frame * layout.spacing - self._scroll_offset
            if x < visible_start_x - 1 or x > visible_end_x + 1:
                continue
            radius = 6
            if frame == self._current_frame:
                radius = 8
            is_within_playback = frame <= playback_last_index
            is_selected = frame in self._selected_keys
            if is_selected:
                painter.setPen(
                    active_selected_key_pen if is_within_playback else inactive_selected_key_pen
                )
                painter.setBrush(
                    active_selected_key_brush
                    if is_within_playback
                    else inactive_selected_key_brush
                )
            else:
                painter.setPen(active_key_pen if is_within_playback else inactive_key_pen)
                painter.setBrush(active_key_brush if is_within_playback else inactive_key_brush)
            painter.drawEllipse(QPointF(x, layout.track_y), radius, radius)

        # Draw the scrub lines.
        painter.setPen(QPen(guide_color, 2))
        painter.drawLine(
            QPointF(visible_start_x, layout.scrub_top),
            QPointF(visible_end_x, layout.scrub_top),
        )
        painter.drawLine(
            QPointF(visible_start_x, layout.scrub_bottom),
            QPointF(visible_end_x, layout.scrub_bottom),
        )

        # Draw the current frame indicator as a triangle.
        current_x = self._margin + self._current_frame * layout.spacing - self._scroll_offset
        current_x = max(visible_start_x, min(current_x, visible_end_x))
        triangle = QPolygonF(
            [
                QPointF(current_x, layout.scrub_top),
                QPointF(current_x - self._scrub_triangle_half_width, layout.scrub_bottom),
                QPointF(current_x + self._scrub_triangle_half_width, layout.scrub_bottom),
            ]
        )
        painter.setPen(QPen(current_color, 1.5))
        painter.setBrush(QBrush(current_color))
        painter.drawPolygon(triangle)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            self._clear_key_drag_state()
            modifiers = event.modifiers()
            ctrl_down = self._is_control_modifier(modifiers)
            shift_down = bool(modifiers & Qt.ShiftModifier)
            key_frame = self._key_at_point(event)
            if key_frame is not None:
                self._is_dragging = False
                if not ctrl_down and not shift_down and key_frame in self._selected_keys:
                    self._prepare_key_drag(
                        key_frame,
                        modifiers=modifiers,
                        defer_selection=True,
                    )
                    self.set_current_frame(key_frame)
                else:
                    self._handle_key_click(key_frame, modifiers)
                    if not ctrl_down and not shift_down:
                        self._prepare_key_drag(
                            key_frame,
                            modifiers=modifiers,
                            defer_selection=False,
                        )
                        self.set_current_frame(key_frame)
                    else:
                        self._clear_key_drag_state()
                event.accept()
                return
            frame = self._frame_at_point(event)
            if self._is_point_in_scrub_area(event):
                self._clear_key_drag_state()
                self._is_dragging = True
                self.set_current_frame(frame)
                event.accept()
                return
            self._is_dragging = False
            self.set_current_frame(frame)
            if not ctrl_down and not shift_down:
                self._set_selection(set(), anchor=None)
            event.accept()
            return
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._last_pan_x = self._event_x(event)
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            frame = self._frame_at_point(event)
            if frame not in self._keys:
                self.key_add_requested.emit(frame)
            self.set_current_frame(frame)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if self._is_panning:
            if event.buttons() & Qt.MiddleButton:
                self._update_pan(event)
                event.accept()
                return
            self._is_panning = False
            self._last_pan_x = 0.0
            self.unsetCursor()
        if self._drag_state.is_dragging or self._drag_state.pending:
            if event.buttons() & Qt.LeftButton:
                frame = self._frame_at_point(event)
                self._update_key_drag(frame)
                event.accept()
                return
            if not self._drag_state.is_dragging:
                self._clear_key_drag_state()
        if not (event.buttons() & Qt.LeftButton):
            self._is_dragging = False
        if self._is_dragging:
            frame = self._frame_at_point(event)
            self.set_current_frame(frame)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            if self._finish_key_drag(event):
                return
            if self._is_dragging:
                frame = self._frame_at_point(event)
                self.set_current_frame(frame)
                event.accept()
            self._is_dragging = False
            return
        if event.button() == Qt.MiddleButton:
            self._is_panning = False
            self._last_pan_x = 0.0
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):  # noqa: N802 - Qt naming
        frame = self._frame_at_point(event)
        menu = QMenu(self)

        if self._document_frame_count:
            max_frame_index = self._document_frame_count - 1
        else:
            max_frame_index = 0
        frame_for_frame_ops = max(0, min(frame, max_frame_index))
        has_frame = 0 <= frame < self._document_frame_count

        insert_action = menu.addAction(
            f"Insert Frame After {frame_for_frame_ops}"
        )
        insert_action.setEnabled(has_frame and self._document_frame_count > 0)

        delete_action = menu.addAction(f"Delete Frame {frame_for_frame_ops}")
        delete_action.setEnabled(has_frame and self._document_frame_count > 1)

        menu.addSeparator()

        add_action = menu.addAction(f"Add Key @ Frame {frame}")
        add_action.setEnabled(frame not in self._keys)

        selected_keys = self.selected_keys()
        if selected_keys:
            if len(selected_keys) == 1:
                remove_label = "Remove Selected Key"
            else:
                remove_label = "Remove Selected Keys"
        else:
            remove_label = f"Remove Key @ Frame {frame}"

        remove_action = menu.addAction(remove_label)
        remove_action.setEnabled(
            (frame in self._keys or bool(selected_keys)) and len(self._keys) > 1
        )

        menu.addSeparator()
        copy_frame = frame
        copy_action = menu.addAction(f"Copy Key @ Frame {copy_frame}")
        copy_action.setEnabled(copy_frame in self._keys)

        paste_action = menu.addAction(f"Paste Key @ Frame {frame}")
        paste_action.setEnabled(self._has_copied_key)

        chosen = menu.exec(event.globalPos())
        if chosen == insert_action:
            self.frame_insert_requested.emit(frame_for_frame_ops)
        elif chosen == delete_action:
            self.frame_delete_requested.emit(frame_for_frame_ops)
        elif chosen == add_action:
            self.key_add_requested.emit(frame)
        elif chosen == remove_action:
            if selected_keys:
                unique_selection = sorted(set(selected_keys))
                if len(unique_selection) == 1:
                    self.key_remove_requested.emit(unique_selection[0])
                else:
                    self.keys_remove_requested.emit(unique_selection)
            else:
                self.key_remove_requested.emit(frame)
        elif chosen == copy_action:
            self.key_copy_requested.emit(copy_frame)
        elif chosen == paste_action:
            self.key_paste_requested.emit(frame)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _frame_at_point(self, event) -> int:
        x = self._event_x(event)
        x = max(self._margin, min(x, self.width() - self._margin))
        layout = self._calculate_layout()
        if layout.spacing <= 0:
            return 0
        frame = round((x + self._scroll_offset - self._margin) / layout.spacing)
        frame = max(0, min(frame, layout.max_frame))
        return frame

    def _key_at_point(self, event: QMouseEvent) -> int | None:
        layout = self._calculate_layout()
        if layout.spacing <= 0:
            return None
        event_x = self._event_x(event)
        event_y = self._event_y(event)
        closest_frame: int | None = None
        closest_distance_sq = float("inf")
        for frame in self._keys:
            x = self._margin + frame * layout.spacing - self._scroll_offset
            radius = 6
            if frame == self._current_frame:
                radius = 8
            radius += self._key_hit_padding
            dx = event_x - x
            dy = event_y - layout.track_y
            if abs(dx) > radius or abs(dy) > radius:
                continue
            distance_sq = dx * dx + dy * dy
            if distance_sq <= radius * radius and distance_sq < closest_distance_sq:
                closest_distance_sq = distance_sq
                closest_frame = frame
        return closest_frame

    def _handle_key_click(self, frame: int, modifiers: Qt.KeyboardModifiers) -> None:
        ctrl = self._is_control_modifier(modifiers)
        shift = bool(modifiers & Qt.ShiftModifier)
        if shift:
            anchor = self._selection_anchor
            if anchor is None or anchor not in self._keys:
                anchor = frame
            start = min(anchor, frame)
            end = max(anchor, frame)
            range_keys = {key for key in self._keys if start <= key <= end}
            if ctrl:
                new_selection = set(self._selected_keys) | range_keys
            else:
                new_selection = range_keys
            self._set_selection(new_selection, anchor=anchor)
            return
        if ctrl:
            new_selection = set(self._selected_keys)
            anchor = self._selection_anchor
            if frame in new_selection:
                new_selection.remove(frame)
                if anchor == frame:
                    anchor = min(new_selection) if new_selection else None
            else:
                new_selection.add(frame)
                anchor = frame
            self._set_selection(new_selection, anchor=anchor)
            return
        self._set_selection({frame}, anchor=frame)

    def _sync_selection_with_keys(self) -> None:
        if not self._keys:
            self._set_selection(set(), anchor=None)
            return
        current_selection = set(self._selected_keys)
        self._set_selection(current_selection, prefer_existing_anchor=True)

    def _set_selection(
        self,
        frames: Set[int],
        anchor: int | None = None,
        *,
        prefer_existing_anchor: bool = False,
    ) -> None:
        valid_frames = {frame for frame in frames if frame in self._keys}
        new_anchor = anchor
        if prefer_existing_anchor and self._selection_anchor in valid_frames:
            new_anchor = self._selection_anchor
        if new_anchor is None and valid_frames:
            new_anchor = min(valid_frames)
        if new_anchor is not None and new_anchor not in valid_frames:
            new_anchor = min(valid_frames) if valid_frames else None
        selection_changed = valid_frames != self._selected_keys
        if selection_changed:
            self._selected_keys = valid_frames
            self.selected_keys_changed.emit(self.selected_keys())
            self.update()
        else:
            self._selected_keys = valid_frames
        if not valid_frames:
            new_anchor = None
        self._selection_anchor = new_anchor

    def _is_control_modifier(self, modifiers: Qt.KeyboardModifiers) -> bool:
        return bool(modifiers & (Qt.ControlModifier | Qt.MetaModifier))

    def _calculate_layout(self) -> _TimelineLayout:
        width = max(1, self.width())
        height = max(1, self.height())
        usable_width = max(1.0, width - 2 * self._margin)
        max_key = max(self._keys) if self._keys else 0
        playback_max = max(0, self._playback_total_frames - 1)
        max_hint = max(self._base_total_frames, max_key, self._current_frame, playback_max)
        spacing = self._preferred_frame_spacing
        if usable_width < spacing:
            spacing = max(1.0, usable_width)
        visible_capacity = max(1, int(ceil(usable_width / spacing)))
        max_frame = max(visible_capacity, max_hint)
        track_y = height / 2
        track_bottom = track_y + self._tick_height / 2
        scrub_top_limit = height - self._scrub_channel_height - 6
        scrub_top = track_bottom + self._scrub_gap
        scrub_top = min(scrub_top, scrub_top_limit)
        min_scrub_top = track_bottom + 2
        if scrub_top < min_scrub_top:
            scrub_top = min_scrub_top
        scrub_bottom = min(height - 4, scrub_top + self._scrub_channel_height)
        if scrub_bottom < scrub_top:
            scrub_bottom = scrub_top
        content_end = self._margin + max_frame * spacing
        max_offset = max(0.0, content_end - (width - self._margin))
        if self._scroll_offset < 0:
            self._scroll_offset = 0.0
        elif self._scroll_offset > max_offset:
            self._scroll_offset = max_offset
        return _TimelineLayout(
            max_frame=max_frame,
            spacing=spacing,
            track_y=track_y,
            usable_width=usable_width,
            max_offset=max_offset,
            scrub_top=scrub_top,
            scrub_bottom=scrub_bottom,
        )

    def _ensure_base_frame(self, frame: int) -> None:
        if frame > self._base_total_frames:
            self._base_total_frames = frame
            self.updateGeometry()

    def _ensure_frame_visible(self, frame: int) -> None:
        layout = self._calculate_layout()
        if layout.spacing <= 0:
            return
        left_bound = self._margin
        right_bound = self.width() - self._margin
        frame_world_x = self._margin + frame * layout.spacing
        frame_visible_x = frame_world_x - self._scroll_offset
        if frame_visible_x < left_bound:
            new_offset = frame_world_x - left_bound
            new_offset = max(0.0, min(new_offset, layout.max_offset))
            if new_offset != self._scroll_offset:
                self._scroll_offset = new_offset
                self.update()
        elif frame_visible_x > right_bound:
            new_offset = frame_world_x - right_bound
            new_offset = max(0.0, min(new_offset, layout.max_offset))
            if new_offset != self._scroll_offset:
                self._scroll_offset = new_offset
                self.update()

    def _update_pan(self, event: QMouseEvent) -> None:
        layout = self._calculate_layout()
        if layout.spacing <= 0:
            return
        x = self._event_x(event)
        delta = x - self._last_pan_x
        if delta == 0:
            return
        self._last_pan_x = x
        new_offset = self._scroll_offset - delta
        new_offset = max(0.0, min(new_offset, layout.max_offset))
        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self.update()

    def _event_x(self, event: QMouseEvent) -> float:
        pos = event.position() if hasattr(event, "position") else event.pos()
        return float(pos.x())

    def _event_y(self, event: QMouseEvent) -> float:
        pos = event.position() if hasattr(event, "position") else event.pos()
        return float(pos.y())

    def _is_point_in_scrub_area(self, event: QMouseEvent) -> bool:
        layout = self._calculate_layout()
        y = self._event_y(event)
        top = layout.scrub_top - self._scrub_tolerance
        bottom = layout.scrub_bottom + self._scrub_tolerance
        return top <= y <= bottom

    def _prepare_key_drag(
        self,
        frame: int,
        *,
        modifiers: Qt.KeyboardModifiers,
        defer_selection: bool,
    ) -> None:
        initial_selection = set(self._selected_keys)
        if not initial_selection or frame not in initial_selection:
            self._clear_key_drag_state()
            return
        state = self._drag_state
        state.clear()
        state.candidate_frame = frame
        state.candidate_modifiers = modifiers
        state.initial_keys.update(initial_selection)
        state.other_keys.update(key for key in self._keys if key not in state.initial_keys)
        state.all_keys.update(self._keys)
        state.start_frame = frame
        state.last_offset = 0
        state.has_moved = False
        state.defer_selection = defer_selection
        state.follow_current_frame = self._current_frame in initial_selection
        state.start_current_frame = self._current_frame

    def _clear_key_drag_state(self) -> None:
        self._drag_state.clear()

    def _clamp_key_drag_delta(self, delta: int) -> int:
        state = self._drag_state
        if not state.initial_keys:
            return 0
        min_key = min(state.initial_keys)
        min_delta = -min_key
        return max(min_delta, delta)

    def _update_key_drag(self, frame: int) -> None:
        state = self._drag_state
        if not state.pending:
            return
        delta = frame - state.start_frame
        clamped_delta = self._clamp_key_drag_delta(delta)
        if not state.is_dragging and (clamped_delta != 0 or state.has_moved):
            state.is_dragging = True
        if clamped_delta == state.last_offset:
            if delta != 0:
                state.has_moved = True
            return
        if clamped_delta != 0:
            state.has_moved = True
        self._apply_key_drag_delta(clamped_delta)
        state.last_offset = clamped_delta

    def _apply_key_drag_delta(self, delta: int) -> None:
        state = self._drag_state
        if not state.initial_keys:
            return
        shifted_keys = {max(0, frame + delta) for frame in state.initial_keys}
        remaining_keys = {frame for frame in state.other_keys if frame not in shifted_keys}
        updated_keys = remaining_keys | shifted_keys
        if not updated_keys:
            updated_keys = {0}
        if updated_keys != self._keys:
            self._keys = updated_keys
        self._ensure_base_frame(max(updated_keys))
        anchor = self._selection_anchor
        if anchor in state.initial_keys:
            anchor = anchor + delta
        self._set_selection(shifted_keys, anchor=anchor, prefer_existing_anchor=True)
        if state.follow_current_frame:
            target_frame = state.start_current_frame + delta
            self._set_current_frame_internal(target_frame, emit_signal=False)
        else:
            self.update()
        self.keys_changed.emit(self.keys())

    def _finish_key_drag(self, event: QMouseEvent) -> bool:
        state = self._drag_state
        if not state.pending and not state.is_dragging and not state.has_moved:
            return False
        if state.is_dragging or state.has_moved:
            moved_keys = self.keys()
            follow_current = state.follow_current_frame
            final_frame = self._current_frame
            initial_selection = sorted(state.initial_keys)
            if initial_selection and set(moved_keys) != state.all_keys:
                self.key_move_requested.emit(initial_selection, state.last_offset)
            if follow_current:
                self._set_current_frame_internal(final_frame, emit_signal=False)
                self.current_frame_changed.emit(final_frame)
            self._clear_key_drag_state()
            event.accept()
            return True
        if state.defer_selection and state.candidate_frame is not None:
            self._handle_key_click(state.candidate_frame, state.candidate_modifiers)
            modifiers = state.candidate_modifiers
            if not self._is_control_modifier(modifiers) and not (
                modifiers & Qt.ShiftModifier
            ):
                self.set_current_frame(state.candidate_frame)
        self._clear_key_drag_state()
        event.accept()
        return True

