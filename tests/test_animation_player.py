from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer

from portal.core.animation_player import AnimationPlayer, DEFAULT_TOTAL_FRAMES


def test_animation_player_default_total_frames():
    player = AnimationPlayer()
    assert player.total_frames == DEFAULT_TOTAL_FRAMES


def test_animation_player_advances_and_loops(qapp):
    player = AnimationPlayer()
    player.set_total_frames(3)
    player.set_fps(60)

    frames: list[int] = []
    loop = QEventLoop()

    def on_frame(frame: int) -> None:
        frames.append(frame)
        if len(frames) >= 4:
            player.pause()
            if loop.isRunning():
                loop.quit()

    player.frame_changed.connect(on_frame)
    player.play()

    QTimer.singleShot(500, loop.quit)
    loop.exec()

    assert len(frames) >= 4
    assert frames[:4] == [1, 2, 0, 1]

    player.stop()


def test_animation_player_stop_resets_frame(qapp):
    player = AnimationPlayer()
    player.set_total_frames(5)
    player.set_current_frame(3)

    player.play()
    qapp.processEvents()
    player.stop()

    assert player.current_frame == 0
    assert not player.is_playing


def test_animation_player_clamps_when_frame_count_shrinks(qapp):
    player = AnimationPlayer()
    player.set_total_frames(6)
    player.set_current_frame(5)

    observed: list[int] = []
    player.frame_changed.connect(observed.append)

    player.set_total_frames(3)

    assert player.current_frame == 2
    assert observed == [2]


def test_animation_player_respects_loop_range_when_setting(qapp):
    player = AnimationPlayer()
    player.set_total_frames(6)
    player.set_current_frame(5)

    player.set_loop_range(2, 4)

    assert player.loop_start == 2
    assert player.loop_end == 4
    assert player.current_frame == 2


def test_animation_player_stop_returns_to_loop_start(qapp):
    player = AnimationPlayer()
    player.set_total_frames(5)
    player.set_loop_range(1, 3)
    player.set_current_frame(2)

    player.play()
    qapp.processEvents()
    player.stop()

    assert player.current_frame == 1
    assert not player.is_playing


def test_animation_player_play_starts_within_loop(qapp):
    player = AnimationPlayer()
    player.set_total_frames(5)
    player.set_current_frame(0)
    player.set_loop_range(2, 4)

    player.play()
    qapp.processEvents()
    assert player.current_frame == 2
    player.pause()


def test_animation_player_loop_range_updates_when_total_shrinks(qapp):
    player = AnimationPlayer()
    player.set_total_frames(6)
    player.set_loop_range(1, 5)

    player.set_total_frames(3)

    assert player.loop_start == 1
    assert player.loop_end == 2


def test_animation_player_advances_with_custom_loop(qapp):
    player = AnimationPlayer()
    player.set_total_frames(5)
    player.set_loop_range(1, 2)
    player.set_fps(60)

    frames: list[int] = []
    loop = QEventLoop()

    def on_frame(frame: int) -> None:
        frames.append(frame)
        if len(frames) >= 4:
            player.pause()
            if loop.isRunning():
                loop.quit()

    player.frame_changed.connect(on_frame)
    player.play()

    QTimer.singleShot(500, loop.quit)
    loop.exec()

    assert len(frames) >= 4
    assert frames[:4] == [2, 1, 2, 1]
