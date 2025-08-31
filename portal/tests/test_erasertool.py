from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, Qt, QRect, QSize
from PySide6.QtGui import QMouseEvent, QColor, QImage
from portal.command import DrawCommand
from portal.tools.erasertool import EraserTool

from PySide6.QtCore import QRect

@pytest.fixture
def eraser_tool(qtbot):
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
    mock_canvas._document_size = QSize(256, 256)
    mock_canvas.is_erasing_preview = False
    mock_canvas.temp_image = None
    mock_canvas.original_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    tool = EraserTool(mock_canvas)
    return tool

def test_mouse_events(eraser_tool, qtbot):
    """
    This test should verify that the DrawCommand is executed with erase=True when the mouse is released.
    """
    tool = eraser_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    assert canvas.is_erasing_preview is True
    assert tool.points == [QPoint(10, 10)]
    assert canvas.temp_image is not None

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 20))
    assert tool.points == [QPoint(10, 10), QPoint(20, 20)]

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 20))

    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, DrawCommand)
    assert command.erase is True
    assert canvas.is_erasing_preview is False
    assert tool.points == []
    assert canvas.temp_image is None
    assert canvas.original_image is None
