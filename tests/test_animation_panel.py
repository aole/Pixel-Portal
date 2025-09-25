import pytest

from PySide6.QtCore import QPointF, Qt

from portal.ui.animation_panel import AnimationPanel


def _frame_center(panel: AnimationPanel, frame: int) -> QPointF:
    rect = panel.rect()
    timeline_y = rect.bottom() - 24
    min_timeline_y = rect.top() + 40
    if timeline_y < min_timeline_y:
        timeline_y = min_timeline_y
    center_y = timeline_y - 5
    return QPointF(panel._frame_to_x(frame), center_y)


@pytest.fixture
def animation_panel(qtbot):
    panel = AnimationPanel()
    qtbot.addWidget(panel)
    panel.resize(400, 120)
    panel.show()
    qtbot.waitExposed(panel)
    return panel


def test_click_selects_single_key(animation_panel, qtbot):
    panel = animation_panel
    panel.set_keyframes([2, 4, 8])
    qtbot.wait(0)

    pos = _frame_center(panel, 4).toPoint()
    qtbot.mouseClick(panel, Qt.LeftButton, Qt.NoModifier, pos)
    qtbot.wait(0)

    assert panel.selected_keyframes == (4,)


def test_ctrl_click_toggles_selection(animation_panel, qtbot):
    panel = animation_panel
    panel.set_keyframes([1, 3, 5])
    qtbot.wait(0)

    qtbot.mouseClick(panel, Qt.LeftButton, Qt.NoModifier, _frame_center(panel, 1).toPoint())
    qtbot.wait(0)
    qtbot.mouseClick(
        panel,
        Qt.LeftButton,
        Qt.ControlModifier,
        _frame_center(panel, 5).toPoint(),
    )
    qtbot.wait(0)

    assert panel.selected_keyframes == (1, 5)

    qtbot.mouseClick(
        panel,
        Qt.LeftButton,
        Qt.ControlModifier,
        _frame_center(panel, 1).toPoint(),
    )
    qtbot.wait(0)

    assert panel.selected_keyframes == (5,)


def test_shift_click_extends_selection(animation_panel, qtbot):
    panel = animation_panel
    panel.set_keyframes([2, 4, 6, 8])
    qtbot.wait(0)

    qtbot.mouseClick(panel, Qt.LeftButton, Qt.NoModifier, _frame_center(panel, 4).toPoint())
    qtbot.wait(0)
    qtbot.mouseClick(
        panel,
        Qt.LeftButton,
        Qt.ShiftModifier,
        _frame_center(panel, 8).toPoint(),
    )
    qtbot.wait(0)

    assert panel.selected_keyframes == (4, 6, 8)
