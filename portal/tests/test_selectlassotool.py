from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath
from portal.tools.selectlassotool import SelectLassoTool

@pytest.fixture
def select_lasso_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    tool = SelectLassoTool(mock_canvas)
    tool.moving_selection = False
    return tool

def test_mouse_events(select_lasso_tool, qtbot):
    """
    This test should verify that a lasso selection is created as the mouse is pressed, moved, and released.
    """
    tool = select_lasso_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    canvas._update_selection_and_emit_size.assert_called()
    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(path, QPainterPath)
    assert path.currentPosition() == QPoint(10, 10)

    # Mouse Move
    canvas.selection_shape = path
    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 20))
    canvas._update_selection_and_emit_size.assert_called_with(path)
    assert path.currentPosition() == QPoint(20, 20)


    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with patch.object(path, "closeSubpath") as mock_close_subpath:
        tool.mouseReleaseEvent(release_event, QPoint(20, 20))
        mock_close_subpath.assert_called_once()
    canvas.selection_changed.emit.assert_called_with(True)
