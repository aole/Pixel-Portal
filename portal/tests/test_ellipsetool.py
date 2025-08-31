from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QColor, QImage
from portal.command import ShapeCommand
from portal.tools.ellipsetool import EllipseTool

@pytest.fixture
def ellipse_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.document.layer_manager.active_layer = Mock()
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
    tool = EllipseTool(mock_canvas)
    return tool

def test_mouse_events(ellipse_tool, qtbot):
    """
    This test should check that an ellipse is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = ellipse_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "ellipse_tool_start")]
    assert tool.start_point == QPoint(10, 10)
    assert canvas.temp_image_replaces_active_layer is True

    # Mouse Move
    with patch.object(canvas.drawing, "draw_ellipse") as mock_draw_ellipse:
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tool.mouseMoveEvent(move_event, QPoint(30, 40))
        assert canvas.temp_image is not None
        mock_draw_ellipse.assert_called_once()
        # We can do more detailed checks on the arguments if needed

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(30, 40))

    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, ShapeCommand)
    assert command.shape_type == 'ellipse'
    assert command.rect == QRect(10, 10, 21, 31)
    assert canvas.temp_image is None
    assert canvas.original_image is None
    assert canvas.temp_image_replaces_active_layer is False
