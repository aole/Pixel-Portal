"""Interactive timeline widget for displaying animation frames and keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QMouseEvent, QPaintEvent, QPainter, QPen, QPalette
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget


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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_total_frames = 120
        self._keys: Set[int] = {0}
        self._current_frame = 0
        self._margin = 24
        self._tick_height = 18
        self._preferred_frame_spacing = 16.0

        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        return QSize(800, 120)

    def total_frames(self) -> int:
        """Return the number of frames represented on the timeline."""

        return self._base_total_frames

    def set_total_frames(self, frame_count: int) -> None:
        """Define the nominal number of frames displayed by the timeline."""

        frame_count = max(1, int(frame_count))
        if frame_count == self._base_total_frames:
            return
        self._base_total_frames = frame_count
        self.updateGeometry()
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

    def duplicate_last_key(self) -> None:
        if not self._keys:
            return
        last_key = max(self._keys)
        new_frame = last_key + 1
        while new_frame in self._keys:
            new_frame += 1
        self.add_key(new_frame)
        self.set_current_frame(new_frame)

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt naming
        super().paintEvent(event)
        layout = self._calculate_layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        palette = self.palette()
        guide_color = palette.color(QPalette.Mid)
        frame_color = palette.color(QPalette.Midlight)
        key_color = palette.color(QPalette.Highlight)
        key_border = key_color.darker(130)
        current_color = palette.color(QPalette.Highlight)

        start_x = self._margin
        end_x = self.width() - self._margin

        # Draw the main timeline bar.
        painter.setPen(QPen(guide_color, 2))
        painter.drawLine(start_x, layout.track_y, end_x, layout.track_y)

        # Draw frame ticks.
        tick_pen = QPen(frame_color, 1)
        for frame in range(layout.max_frame + 1):
            x = start_x + frame * layout.spacing
            if x > end_x + 1:
                break
            tick_height = self._tick_height
            if frame % 5 == 0:
                tick_height = int(self._tick_height * 1.4)
            painter.setPen(tick_pen)
            painter.drawLine(
                QPointF(x, layout.track_y - tick_height / 2),
                QPointF(x, layout.track_y + tick_height / 2),
            )

        # Draw keyed frames as circles.
        painter.setPen(QPen(key_border, 1.5))
        painter.setBrush(QBrush(key_color))
        for frame in self.keys():
            x = start_x + frame * layout.spacing
            if x < start_x - 1 or x > end_x + 1:
                continue
            radius = 6
            if frame == self._current_frame:
                radius = 8
            painter.drawEllipse(QPointF(x, layout.track_y), radius, radius)

        # Draw the current frame indicator.
        current_x = start_x + self._current_frame * layout.spacing
        current_x = max(start_x, min(current_x, end_x))
        painter.setPen(QPen(current_color, 2, Qt.SolidLine))
        painter.drawLine(QPointF(current_x, 0), QPointF(current_x, self.height()))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.LeftButton:
            frame = self._frame_at_point(event)
            self.set_current_frame(frame)
            event.accept()
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):  # noqa: N802 - Qt naming
        frame = self._frame_at_point(event)
        menu = QMenu(self)

        add_action = menu.addAction(f"Add Key @ Frame {frame}")
        add_action.setEnabled(frame not in self._keys)

        remove_action = menu.addAction(f"Remove Key @ Frame {frame}")
        remove_action.setEnabled(frame in self._keys and len(self._keys) > 1)

        menu.addSeparator()
        duplicate_action = menu.addAction("Duplicate Last Key")
        duplicate_action.setEnabled(bool(self._keys))

        chosen = menu.exec(event.globalPos())
        if chosen == add_action:
            self.add_key(frame)
        elif chosen == remove_action:
            self.remove_key(frame)
        elif chosen == duplicate_action:
            self.duplicate_last_key()

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
        usable_width = max(1, width - 2 * self._margin)
        max_key = max(self._keys) if self._keys else 0
        max_frame = max(self._base_total_frames, max_key, self._current_frame)
        spacing = usable_width / max(1, max_frame)
        spacing = max(1.0, min(spacing, self._preferred_frame_spacing))
        track_y = height / 2
        return _TimelineLayout(max_frame=max_frame, spacing=spacing, track_y=track_y, usable_width=usable_width)

    def _ensure_base_frame(self, frame: int) -> None:
        if frame > self._base_total_frames:
            self._base_total_frames = frame
            self.updateGeometry()

