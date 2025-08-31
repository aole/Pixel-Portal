from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QMouseEvent, QColor, QImage, QPainterPath, QPainter
from portal.command import MoveCommand
from portal.tools.movetool import MoveTool

@pytest.fixture
def move_tool(qtbot):
    mock_canvas = Mock()
    mock_layer = Mock()
    mock_layer.image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.document.layer_manager.active_layer = mock_layer
    mock_canvas.selection_shape = None
    mock_canvas.original_image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.temp_image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.temp_image_replaces_active_layer = False
    tool = MoveTool(mock_canvas)
    return tool

def test_mouse_events_no_selection(move_tool, qtbot):
    """
    This test should verify that the layer content is moved correctly when there is no selection.
    """
    tool = move_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "move_tool_start_no_selection")]

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with patch.object(QPainter, "drawImage") as mock_draw_image:
        tool.mouseMoveEvent(move_event, QPoint(20, 30))
        mock_draw_image.assert_called_with(QPoint(10, 20), canvas.original_image)

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 30))
    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, MoveCommand)
    assert command.delta == QPoint(10, 20)

def test_mouse_events_with_selection(move_tool, qtbot):
    """
    This test should verify that the layer content is moved correctly when there is a selection.
    """
    tool = move_tool
    canvas = tool.canvas

    selection_path = QPainterPath()
    selection_path.addRect(QRect(5, 5, 50, 50))
    canvas.selection_shape = selection_path
    tool.original_selection_shape = selection_path

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("cut_selection", "move_tool_start")]

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 30))
    expected_path = selection_path.translated(10, 20)
    assert canvas.selection_shape == expected_path

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 30))
    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, MoveCommand)
    assert command.delta == QPoint(10, 20)
    assert command.original_selection_shape == selection_path
