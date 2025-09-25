from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QToolButton
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtCore import Qt, QSignalBlocker, QObject, Signal, QTimer


class NullAnimationPlayer(QObject):
    """Lightweight stand-in that keeps the preview UI responsive."""

    frame_changed = Signal(int)
    playing_changed = Signal(bool)
    fps_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_frame = 0
        self._is_playing = False
        self._loop_start = 0
        self._loop_end = 0
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._advance_frame)
        self.fps = 12.0
        self._update_timer_interval()

    @property
    def current_frame(self) -> int:
        return self._current_frame

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play(self) -> None:  # pragma: no cover - no runtime effect
        if not self._is_playing:
            self._is_playing = True
            self._ensure_current_frame_in_range()
            self._update_timer_interval()
            self._timer.start()
            self.playing_changed.emit(True)

    def pause(self) -> None:  # pragma: no cover - no runtime effect
        if self._is_playing:
            self._is_playing = False
            self._timer.stop()
            self.playing_changed.emit(False)

    def stop(self) -> None:  # pragma: no cover - no runtime effect
        changed = self._is_playing
        self._is_playing = False
        self._timer.stop()
        if changed:
            self.playing_changed.emit(False)
        if self._current_frame != self._loop_start:
            self._current_frame = self._loop_start
            self.frame_changed.emit(self._current_frame)

    def set_loop_range(self, start: int, end: int) -> None:
        self._loop_start = max(0, int(start))
        try:
            normalized_end = int(end)
        except (TypeError, ValueError):
            normalized_end = self._loop_start + 1
        self._loop_end = max(self._loop_start + 1, normalized_end)
        self._current_frame = min(
            max(self._current_frame, self._loop_start), self._loop_end
        )

    def set_current_frame(self, frame: int) -> None:
        frame = max(self._loop_start, min(int(frame), self._loop_end))
        if frame != self._current_frame:
            self._current_frame = frame
            self.frame_changed.emit(self._current_frame)

    def set_fps(self, fps: float) -> None:
        try:
            self.fps = float(fps)
        except (TypeError, ValueError):
            self.fps = 12.0
        self._update_timer_interval()
        self.fps_changed.emit(self.fps)

    def _update_timer_interval(self) -> None:
        fps = getattr(self, "fps", 12.0)
        if fps <= 0:
            fps = 12.0
        interval = int(round(1000.0 / fps))
        if interval < 10:
            interval = 10
        was_active = self._timer.isActive()
        self._timer.setInterval(interval)
        if was_active:
            self._timer.start()

    def _ensure_current_frame_in_range(self) -> None:
        clamped = max(self._loop_start, min(self._current_frame, self._loop_end))
        if clamped != self._current_frame:
            self._current_frame = clamped
            self.frame_changed.emit(self._current_frame)

    def _advance_frame(self) -> None:
        if not self._is_playing:
            return
        if self._loop_end <= self._loop_start:
            next_frame = self._loop_start
        else:
            next_frame = self._current_frame + 1
            if next_frame > self._loop_end:
                next_frame = self._loop_start
        if next_frame != self._current_frame:
            self._current_frame = next_frame
            self.frame_changed.emit(self._current_frame)

class PreviewPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self._current_playback_frame = 0
        self._current_document_id = None
        self._loop_start = 0
        self._loop_end = 0

        self.preview_player = NullAnimationPlayer(self)
        self.preview_player.frame_changed.connect(self._on_preview_frame_changed)
        self.preview_player.playing_changed.connect(self._on_preview_player_state_changed)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(6)

        self._play_icon = QIcon("icons/play.png")
        self._pause_icon = QIcon("icons/pause.png")

        self.preview_play_button = QToolButton(self)
        self.preview_play_button.setIcon(self._play_icon)
        self.preview_play_button.setText("Play")
        self.preview_play_button.setCheckable(True)
        self.preview_play_button.toggled.connect(self._on_preview_play_toggled)
        self.layout.addWidget(
            self.preview_play_button,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        self.layout.addWidget(
            self.preview_label,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        self.layout.addStretch(1)

        self.update_preview()

    def set_playback_fps(self, fps: float) -> None:
        self.preview_player.set_fps(fps)

    def set_loop_range(self, start: int, end: int) -> None:
        self._loop_start = max(0, int(start))
        try:
            normalized_end = int(end)
        except (TypeError, ValueError):
            normalized_end = self._loop_start + 1
        self._loop_end = max(self._loop_start + 1, normalized_end)
        self.preview_player.set_loop_range(self._loop_start, self._loop_end)
        if (
            self.preview_player.current_frame < self._loop_start
            or self.preview_player.current_frame > self._loop_end
        ):
            self.preview_player.set_current_frame(self._loop_start)

    def update_preview(self, playback_index: int | None = None) -> None:
        document = self.app.document
        if document is None:
            self.preview_label.clear()
            self.preview_label.setFixedSize(0, 0)
            return

        if playback_index is None:
            playback_index = self.preview_player.current_frame

        pixmap = self._pixmap_for_document(document)
        if pixmap is None:
            self.preview_label.clear()
            self.preview_label.setFixedSize(0, 0)
            return

        self.preview_label.setPixmap(pixmap)
        self.preview_label.setFixedSize(pixmap.size())

    def handle_document_changed(self) -> None:
        document = self.app.document
        document_id = id(document) if document is not None else None
        if self._current_document_id != document_id:
            self._current_document_id = document_id
            self.preview_player.stop()
        self.update_preview()

    def stop_preview_playback(self) -> None:
        self.preview_player.stop()

    def _on_preview_play_toggled(self, checked: bool) -> None:
        if checked:
            self.preview_player.play()
        else:
            self.preview_player.pause()

    def _on_preview_player_state_changed(self, playing: bool) -> None:
        with QSignalBlocker(self.preview_play_button):
            self.preview_play_button.setChecked(playing)
        self.preview_play_button.setText("Pause" if playing else "Play")
        self.preview_play_button.setIcon(
            self._pause_icon if playing else self._play_icon
        )
        if not playing:
            self.update_preview()

    def _on_preview_frame_changed(self, frame: int) -> None:
        self._current_playback_frame = frame
        self._sync_document_frame(frame)
        self.update_preview(playback_index=frame)

    def _pixmap_for_document(self, document) -> QPixmap | None:
        image: QImage | None = None
        render_fallback = getattr(document, "render", None)
        if callable(render_fallback):
            try:
                candidate = render_fallback()
            except ValueError:
                image = None
            else:
                image = self._coerce_qimage(candidate)

        if image is None:
            return None

        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return None

        if pixmap.width() > 128 or pixmap.height() > 128:
            pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.FastTransformation)
        return pixmap

    @staticmethod
    def _coerce_qimage(image) -> QImage | None:
        if isinstance(image, QImage):
            return image
        if isinstance(image, QPixmap):
            return image.toImage()
        return None

    def _sync_document_frame(self, frame: int) -> None:
        document = getattr(self.app, "document", None)
        layer_manager = getattr(document, "layer_manager", None) if document else None
        if layer_manager is None:
            return

        try:
            normalized_frame = int(frame)
        except (TypeError, ValueError):
            normalized_frame = layer_manager.current_frame

        if normalized_frame == layer_manager.current_frame:
            return

        self.app.select_frame(normalized_frame)
