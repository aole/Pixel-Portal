# This file will contain tests for selection tools.
from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QPainterPath, QMouseEvent, QColor, QImage
from portal.tools.baseselecttool import BaseSelectTool
from portal.tools.selectcircletool import SelectCircleTool
from portal.tools.selectcolortool import SelectColorTool
from portal.tools.selectlassotool import SelectLassoTool
from portal.tools.selectrectangletool import SelectRectangleTool

@pytest.fixture
def base_select_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.zoom = 1.0
    tool = BaseSelectTool(mock_canvas)
    return tool

def test_is_on_selection_border(base_select_tool):
    """
    This test should check that True is returned when the position is
    on the selection border and False otherwise.
    """
    tool = base_select_tool
    canvas = tool.canvas

    path = QPainterPath()
    path.addRect(QRect(10, 10, 20, 20))
    canvas.selection_shape = path

    # Test a point on the border
    assert tool.is_on_selection_border(QPoint(10, 20)) is True
    # Test a point inside the selection
    assert tool.is_on_selection_border(QPoint(15, 15)) is False
    # Test a point outside the selection
    assert tool.is_on_selection_border(QPoint(50, 50)) is False

    # Test with no selection
    canvas.selection_shape = None
    assert tool.is_on_selection_border(QPoint(10, 20)) is False


@pytest.fixture
def select_circle_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    tool = SelectCircleTool(mock_canvas)
    tool.moving_selection = False
    return tool

def test_select_circle_mouse_events(select_circle_tool, qtbot):
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


@pytest.fixture
def select_color_tool(qtbot):
    mock_canvas = Mock()
    mock_document = Mock()
    image = QImage(10, 10, QImage.Format_ARGB32)
    image.fill(QColor("blue"))
    # Create a pattern of red pixels
    image.setPixelColor(2, 2, QColor("red"))
    image.setPixelColor(4, 4, QColor("red"))
    image.setPixelColor(6, 6, QColor("red"))
    mock_document.render.return_value = image
    mock_canvas.document = mock_document
    tool = SelectColorTool(mock_canvas)
    return tool

def test_select_color_mouse_press_event(select_color_tool):
    """
    This test should check that all pixels of the same color are selected.
    """
    tool = select_color_tool
    canvas = tool.canvas

    # Press on a red pixel
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(2, 2), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(event, QPoint(2, 2))

    canvas._update_selection_and_emit_size.assert_called_once()
    path = canvas._update_selection_and_emit_size.call_args[0][0]

    expected_path = QPainterPath()
    expected_path.addRect(QRect(2, 2, 1, 1))
    expected_path.addRect(QRect(4, 4, 1, 1))
    expected_path.addRect(QRect(6, 6, 1, 1))

    assert path == expected_path.simplified()


@pytest.fixture
def select_lasso_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    tool = SelectLassoTool(mock_canvas)
    tool.moving_selection = False
    return tool

def test_select_lasso_mouse_events(select_lasso_tool, qtbot):
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


@pytest.fixture
def select_rectangle_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    tool = SelectRectangleTool(mock_canvas)
    tool.moving_selection = False
    return tool

def test_select_rectangle_mouse_events(select_rectangle_tool, qtbot):
    """
    This test should check that a rectangular selection is created as the mouse is pressed, moved, and released.
    """
    tool = select_rectangle_tool
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
    assert path.boundingRect() == QRectF(10, 10, 21, 31)


    # Mouse Release
    canvas.selection_shape = canvas._update_selection_and_emit_size.call_args[0][0]
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseReleaseEvent(release_event, QPoint(30, 40))
    canvas.selection_changed.emit.assert_called_with(True)
