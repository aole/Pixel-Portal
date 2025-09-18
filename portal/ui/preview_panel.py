from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QToolButton
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QSignalBlocker

from portal.core.animation_player import AnimationPlayer

class PreviewPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self._playback_total_frames = 1
        self._current_playback_frame = 0
        self._current_document_id = None

        self.preview_player = AnimationPlayer(self)
        self.preview_player.frame_changed.connect(self._on_preview_frame_changed)
        self.preview_player.playing_changed.connect(self._on_preview_player_state_changed)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(6)

        self.preview_play_button = QToolButton(self)
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

    def set_playback_total_frames(self, total_frames: int) -> None:
        total_frames = max(1, int(total_frames))
        self._playback_total_frames = total_frames
        self.preview_player.set_total_frames(total_frames)
        self._current_playback_frame = self.preview_player.current_frame

    def set_playback_fps(self, fps: float) -> None:
        self.preview_player.set_fps(fps)

    def update_preview(self, playback_index: int | None = None) -> None:
        document = self.app.document
        if document is None:
            self.preview_label.clear()
            self.preview_label.setFixedSize(0, 0)
            return

        if playback_index is None and self.preview_player.is_playing:
            playback_index = self.preview_player.current_frame
        elif playback_index is not None:
            try:
                playback_index = int(playback_index)
            except (TypeError, ValueError):
                playback_index = None
            else:
                playback_index = max(0, min(playback_index, self._playback_total_frames - 1))

        pixmap = self._pixmap_for_document(document, playback_index)
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
        if not playing:
            self.update_preview()

    def _on_preview_frame_changed(self, frame: int) -> None:
        self._current_playback_frame = frame
        self.update_preview(playback_index=frame)

    def _pixmap_for_document(self, document, playback_index: int | None) -> QPixmap | None:
        image = None
        frame_manager = getattr(document, "frame_manager", None)
        if playback_index is not None and frame_manager is not None:
            resolved_index = frame_manager.resolve_key_frame_index(playback_index)
            if resolved_index is not None and 0 <= resolved_index < len(frame_manager.frames):
                image = frame_manager.frames[resolved_index].render()

        if image is None:
            try:
                image = document.render_current_frame()
            except ValueError:
                image = None

        if image is None:
            return None

        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return None

        if pixmap.width() > 128 or pixmap.height() > 128:
            pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.FastTransformation)
        return pixmap
