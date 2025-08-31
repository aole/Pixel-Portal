from unittest.mock import Mock
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QColor
from portal.command import FillCommand
from portal.tools.buckettool import BucketTool

@pytest.fixture
def bucket_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.document.layer_manager.active_layer = Mock()
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.selection_shape = None
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False

    tool = BucketTool(mock_canvas)
    return tool

def test_mouse_press_event(bucket_tool, qtbot):
    """
    This test should verify that the FillCommand is executed when the mouse is pressed.
    """
    tool = bucket_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    doc_pos = QPoint(10, 10)

    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(event, doc_pos)

    assert blocker.signal_triggered
    assert isinstance(blocker.args[0], FillCommand)
