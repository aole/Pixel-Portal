"""Timing helper for driving animation playback."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal


DEFAULT_TOTAL_FRAMES = 24


class AnimationPlayer(QObject):
    """Advance frames at a fixed rate and emit updates for listeners."""

    frame_changed = Signal(int)
    playing_changed = Signal(bool)
    fps_changed = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fps = 12.0
        self._total_frames = DEFAULT_TOTAL_FRAMES
        self._current_frame = 0
        self._is_playing = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def fps(self) -> float:
        return self._fps

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def current_frame(self) -> int:
        return self._current_frame

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------
    def play(self) -> None:
        if self._is_playing:
            return
        if self._total_frames <= 0:
            return
        self._is_playing = True
        self._timer.start(self._interval_for_fps())
        self.playing_changed.emit(True)

    def pause(self) -> None:
        if not self._is_playing:
            return
        self._timer.stop()
        self._is_playing = False
        self.playing_changed.emit(False)

    def stop(self) -> None:
        was_playing = self._is_playing
        self.pause()
        if self._current_frame != 0 or was_playing:
            self.set_current_frame(0)

    def set_fps(self, fps: float) -> None:
        try:
            fps_value = float(fps)
        except (TypeError, ValueError):
            return
        if fps_value <= 0:
            fps_value = 1.0
        if abs(fps_value - self._fps) < 1e-6:
            return
        self._fps = fps_value
        if self._is_playing:
            self._timer.start(self._interval_for_fps())
        self.fps_changed.emit(self._fps)

    def set_total_frames(self, frame_count: int) -> None:
        frame_count = int(frame_count)
        if frame_count < 1:
            frame_count = 1
        if frame_count == self._total_frames:
            return
        self._total_frames = frame_count
        max_index = self._total_frames - 1
        if self._current_frame > max_index:
            self.set_current_frame(max_index)

    def set_current_frame(self, frame: int) -> None:
        if self._total_frames <= 0:
            return
        frame = int(frame)
        max_index = self._total_frames - 1
        if frame < 0:
            frame = 0
        elif frame > max_index:
            frame = max_index
        if frame == self._current_frame:
            return
        self._current_frame = frame
        self.frame_changed.emit(self._current_frame)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _interval_for_fps(self) -> int:
        if self._fps <= 0:
            return 1000
        return max(1, int(1000 / self._fps))

    def _advance_frame(self) -> None:
        if self._total_frames <= 0:
            return
        if self._total_frames == 1:
            return
        next_frame = self._current_frame + 1
        if next_frame >= self._total_frames:
            next_frame = 0
        if next_frame == self._current_frame:
            return
        self._current_frame = next_frame
        self.frame_changed.emit(self._current_frame)
