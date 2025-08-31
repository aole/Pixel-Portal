from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, QRect, Qt, QRectF
from PySide6.QtGui import QMouseEvent, QPainterPath
from portal.tools.selectcircletool import SelectCircleTool

@pytest.fixture
def select_circle_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    tool = SelectCircleTool(mock_canvas)
    tool.moving_selection = False
    return tool

def test_mouse_events(select_circle_tool, qtbot):
    """
    This test should verify that a circular selection is created as the mouse is pressed, moved, and released.
    """
    tool = select_circle_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    canvas._update_selection_and_emit_size.assert_called()
    assert tool.start_point == QPoint(10, 10)

    # Mouse Move
    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(30, 40))
    canvas._update_selection_and_emit_size.assert_called()
    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(path, QPainterPath)
    # The bounding rect of the ellipse path should match the drawn rectangle
    assert path.boundingRect() == QRectF(10, 10, 21, 31)


    # Mouse Release
    canvas.selection_shape = canvas._update_selection_and_emit_size.call_args[0][0]
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseReleaseEvent(release_event, QPoint(30, 40))
    canvas.selection_changed.emit.assert_called_with(True)
