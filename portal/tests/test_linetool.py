from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QMouseEvent, QColor, QImage
from portal.command import DrawCommand
from portal.tools.linetool import LineTool

@pytest.fixture
def line_tool(qtbot):
    mock_canvas = Mock()
    mock_layer = Mock()
    mock_layer.image.rect.return_value = QRect(0, 0, 256, 256)
    mock_canvas.document.layer_manager.active_layer = mock_layer
    mock_canvas.document.width = 256
    mock_canvas.document.height = 256
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.drawing_context.pen_width = 1
    mock_canvas.drawing_context.brush_type = "SolidPattern"
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.selection_shape = None
    mock_canvas._document_size = (256, 256)
    mock_canvas.original_image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.temp_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    tool = LineTool(mock_canvas)
    return tool

def test_mouse_events(line_tool, qtbot):
    """
    This test should check that a line is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = line_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "line_tool_start")]
    assert tool.start_point == QPoint(10, 10)
    assert canvas.temp_image_replaces_active_layer is True

    # Mouse Move
    with patch.object(canvas.drawing, "draw_line_with_brush") as mock_draw_line:
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tool.mouseMoveEvent(move_event, QPoint(20, 20))
        assert canvas.temp_image is not None
        mock_draw_line.assert_called_once()

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 20))

    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, DrawCommand)
    assert command.points == [QPoint(10, 10), QPoint(20, 20)]
    assert command.erase is False
    assert canvas.temp_image is None
    assert canvas.original_image is None
    assert canvas.temp_image_replaces_active_layer is False
