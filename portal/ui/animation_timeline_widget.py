"""Interactive timeline widget for displaying animation frames and keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QMouseEvent, QPaintEvent, QPainter, QPen, QPalette
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget

from portal.core.animation_player import DEFAULT_TOTAL_FRAMES


@dataclass
class _TimelineLayout:
    """Pre-computed geometry values for rendering the timeline."""

    max_frame: int
    spacing: float
    track_y: float
    usable_width: float


class AnimationTimelineWidget(QWidget):
    """A minimal animation timeline widget displaying frames and keyed positions.

    The widget renders a horizontal scale with equally spaced frame markers. Keys
    are shown as dots aligned to their frame while a vertical line indicates the
    currently selected frame. Context menu actions allow basic key management.
    """

    keys_changed = Signal(list)
    current_frame_changed = Signal(int)
    key_add_requested = Signal(int)
    key_remove_requested = Signal(int)
    key_copy_requested = Signal(int)
    key_paste_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_total_frames = 0
        self._playback_total_frames = DEFAULT_TOTAL_FRAMES
        self._keys: Set[int] = {0}
        self._current_frame = 0
        self._margin = 24
        self._tick_height = 36
        self._preferred_frame_spacing = 16.0
        self._is_dragging = False
        self._has_copied_key = False

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

    def set_keys(self, frames: Iterable[int]) -> None:
        """Replace the existing keyed frames with *frames*."""

        new_keys = {max(0, int(frame)) for frame in frames}
        if not new_keys:
            new_keys = {0}
        if new_keys == self._keys:
            return
        self._keys = new_keys
        self._ensure_base_frame(max(self._keys))
        self.keys_changed.emit(self.keys())
        self.update()

    def has_copied_key(self) -> bool:
        return self._has_copied_key

    def set_has_copied_key(self, has_key: bool) -> None:
        has_key = bool(has_key)
        if has_key == self._has_copied_key:
            return
        self._has_copied_key = has_key

    def current_frame(self) -> int:
        return self._current_frame

    def set_current_frame(self, frame: int) -> None:
        frame = max(0, int(frame))
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self._ensure_base_frame(frame)
        self.current_frame_changed.emit(self._current_frame)
        self.update()

    def add_key(self, frame: int) -> None:
        frame = max(0, int(frame))
        if frame in self._keys:
            return
        self._keys.add(frame)
        self._ensure_base_frame(frame)
        self.keys_changed.emit(self.keys())
        self.update()

    def remove_key(self, frame: int) -> None:
        frame = int(frame)
        if frame not in self._keys:
            return
        if len(self._keys) == 1:
            return
        self._keys.remove(frame)
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

        active_tick_pen = QPen(frame_color, 1.5)
        inactive_tick_pen = QPen(muted_frame_color, 1.5)
        active_number_pen = QPen(frame_color)
        inactive_number_pen = QPen(muted_frame_color)
        active_key_pen = QPen(key_border, 1.5)
        inactive_key_pen = QPen(muted_key_border, 1.5)
        active_key_brush = QBrush(key_color)
        inactive_key_brush = QBrush(muted_key_color)

        playback_last_index = max(0, self._playback_total_frames - 1)

        start_x = self._margin
        end_x = self.width() - self._margin

        # Draw the main timeline bar.
        painter.setPen(QPen(guide_color, 2))
        painter.drawLine(start_x, layout.track_y, end_x, layout.track_y)

        # Draw frame ticks.
        for frame in range(layout.max_frame + 1):
            x = start_x + frame * layout.spacing
            if x > end_x + 1:
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
            x = start_x + frame * layout.spacing
            if x < start_x - 1 or x > end_x + 1:
                continue
            radius = 6
            if frame == self._current_frame:
                radius = 8
            is_within_playback = frame <= playback_last_index
            painter.setPen(active_key_pen if is_within_playback else inactive_key_pen)
            painter.setBrush(active_key_brush if is_within_playback else inactive_key_brush)
            painter.drawEllipse(QPointF(x, layout.track_y), radius, radius)

        # Draw the current frame indicator.
        current_x = start_x + self._current_frame * layout.spacing
        current_x = max(start_x, min(current_x, end_x))
        painter.setPen(QPen(current_color, 2, Qt.SolidLine))
        painter.drawLine(QPointF(current_x, 0), QPointF(current_x, self.height()))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            frame = self._frame_at_point(event)
            self.set_current_frame(frame)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.buttons() & Qt.LeftButton:
            self._is_dragging = True
        else:
            self._is_dragging = False
        if self._is_dragging:
            frame = self._frame_at_point(event)
            self.set_current_frame(frame)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            frame = self._frame_at_point(event)
            self.set_current_frame(frame)
            self._is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):  # noqa: N802 - Qt naming
        frame = self._frame_at_point(event)
        menu = QMenu(self)

        add_action = menu.addAction(f"Add Key @ Frame {frame}")
        add_action.setEnabled(frame not in self._keys)

        remove_action = menu.addAction(f"Remove Key @ Frame {frame}")
        remove_action.setEnabled(frame in self._keys and len(self._keys) > 1)

        menu.addSeparator()
        copy_frame = frame
        copy_action = menu.addAction(f"Copy Key @ Frame {copy_frame}")
        copy_action.setEnabled(copy_frame in self._keys)

        paste_action = menu.addAction(f"Paste Key @ Frame {frame}")
        paste_action.setEnabled(self._has_copied_key)

        chosen = menu.exec(event.globalPos())
        if chosen == add_action:
            self.key_add_requested.emit(frame)
        elif chosen == remove_action:
            self.key_remove_requested.emit(frame)
        elif chosen == copy_action:
            self.key_copy_requested.emit(copy_frame)
        elif chosen == paste_action:
            self.key_paste_requested.emit(frame)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _frame_at_point(self, event) -> int:
        pos = event.position() if hasattr(event, "position") else event.pos()
        if hasattr(pos, "toPoint"):
            pos = pos.toPoint()
        x = max(self._margin, min(pos.x(), self.width() - self._margin))
        layout = self._calculate_layout()
        if layout.spacing <= 0:
            return 0
        frame = round((x - self._margin) / layout.spacing)
        frame = max(0, min(frame, layout.max_frame))
        return frame

    def _calculate_layout(self) -> _TimelineLayout:
        width = max(1, self.width())
        height = max(1, self.height())
        usable_width = max(1.0, width - 2 * self._margin)
        dynamic_frames = max(1, int(usable_width // self._preferred_frame_spacing))
        max_key = max(self._keys) if self._keys else 0
        playback_max = max(0, self._playback_total_frames - 1)
        max_hint = max(self._base_total_frames, max_key, self._current_frame, playback_max)
        max_frame = max(dynamic_frames, max_hint)
        spacing = usable_width / max(1, max_frame)
        spacing = max(1.0, min(spacing, self._preferred_frame_spacing))
        track_y = height / 2
        return _TimelineLayout(max_frame=max_frame, spacing=spacing, track_y=track_y, usable_width=usable_width)

    def _ensure_base_frame(self, frame: int) -> None:
        if frame > self._base_total_frames:
            self._base_total_frames = frame
            self.updateGeometry()

