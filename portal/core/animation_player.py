"""Timing helper for driving animation playback."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal


DEFAULT_TOTAL_FRAMES = 1
DEFAULT_PLAYBACK_FPS = 12.0


class AnimationPlayer(QObject):
    """Advance frames at a fixed rate and emit updates for listeners."""

    frame_changed = Signal(int)
    playing_changed = Signal(bool)
    fps_changed = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fps = DEFAULT_PLAYBACK_FPS
        self._total_frames = DEFAULT_TOTAL_FRAMES
        self._current_frame = 0
        self._is_playing = False
        self._loop_start = 0
        self._loop_end = max(0, self._total_frames - 1)
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
    def loop_start(self) -> int:
        return self._loop_start

    @property
    def loop_end(self) -> int:
        return self._loop_end

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
        if self._loop_start > self._loop_end:
            self._loop_start = max(0, min(self._loop_start, self._total_frames - 1))
            self._loop_end = self._loop_start
        if self._current_frame < self._loop_start or self._current_frame > self._loop_end:
            self.set_current_frame(self._loop_start)
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
        target = self._loop_start if self._loop_start <= self._loop_end else 0
        if self._current_frame != target or was_playing:
            self.set_current_frame(target)

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
        if self._total_frames == 1:
            return
        self._total_frames = 1
        self._loop_start = 0
        self._loop_end = 0
        if self._current_frame != 0:
            self.set_current_frame(0)

    def set_loop_range(self, start: int, end: int) -> None:
        if self._loop_start == 0 and self._loop_end == 0:
            return
        self._loop_start = 0
        self._loop_end = 0
        if self._current_frame != 0:
            self.set_current_frame(0)

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
        if next_frame > self._loop_end or next_frame >= self._total_frames:
            next_frame = self._loop_start
        if next_frame < self._loop_start:
            next_frame = self._loop_start
        if next_frame == self._current_frame:
            return
        self._current_frame = next_frame
        self.frame_changed.emit(self._current_frame)
