# This file will contain tests for selection tools.
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QPainterPath, QMouseEvent, QColor, QImage
from portal.commands.selection_commands import selection_paths_equal
from portal.tools.baseselecttool import BaseSelectTool
from portal.tools.selectcircletool import SelectCircleTool
from portal.tools.selectcolortool import SelectColorTool
from portal.tools.selectlassotool import SelectLassoTool
from portal.tools.selectrectangletool import SelectRectangleTool

@pytest.fixture
def base_select_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.zoom = 1.0
    mock_canvas._document_size = QSize(64, 64)
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
    mock_canvas._document_size = QSize(64, 64)
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
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    canvas._update_selection_and_emit_size.assert_called()
    assert tool.start_point == QPoint(10, 10)

    # Mouse Move
    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(30, 40))
    canvas._update_selection_and_emit_size.assert_called()
    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(path, QPainterPath)
    # The bounding rect of the ellipse path should match the drawn rectangle
    assert path.boundingRect() == QRectF(10, 10, 21, 31)


    # Mouse Release
    canvas.selection_shape = canvas._update_selection_and_emit_size.call_args[0][0]
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
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
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(2, 2), QPoint(2, 2), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
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
    mock_canvas._document_size = QSize(64, 64)
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
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    canvas._update_selection_and_emit_size.assert_called()
    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(path, QPainterPath)
    assert path.currentPosition() == QPoint(10, 10)

    # Mouse Move
    canvas.selection_shape = path
    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 20))
    canvas._update_selection_and_emit_size.assert_called()
    updated_path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(updated_path, QPainterPath)
    assert updated_path.currentPosition() == QPoint(20, 20)
    canvas.selection_shape = updated_path


    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert tool._lasso_path is not None
    with patch.object(tool._lasso_path, "closeSubpath") as mock_close_subpath:
        tool.mouseReleaseEvent(release_event, QPoint(20, 20))
        mock_close_subpath.assert_called_once()
    canvas.selection_changed.emit.assert_called_with(True)


@pytest.fixture
def select_rectangle_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.selection_shape = None
    mock_canvas._document_size = QSize(64, 64)
    tool = SelectRectangleTool(mock_canvas)
    tool.moving_selection = False
    return tool


def test_select_rectangle_clamps_to_document_bounds(select_rectangle_tool, qtbot):
    tool = select_rectangle_tool
    canvas = tool.canvas
    canvas._document_size = QSize(32, 32)

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(-10, -10),
        QPoint(-10, -10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, QPoint(-10, -10))

    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(100, 100),
        QPoint(100, 100),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas._update_selection_and_emit_size.reset_mock()
    tool.mouseMoveEvent(move_event, QPoint(100, 100))

    path = canvas._update_selection_and_emit_size.call_args[0][0]
    rect = path.boundingRect()
    assert rect.left() >= 0
    assert rect.top() >= 0
    assert rect.right() <= canvas._document_size.width()
    assert rect.bottom() <= canvas._document_size.height()


def test_select_rectangle_reaches_top_left_edge(select_rectangle_tool, qtbot):
    tool = select_rectangle_tool
    canvas = tool.canvas

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(10, 10),
        QPoint(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, QPoint(10, 10))

    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(-5, -5),
        QPoint(-5, -5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, QPoint(-5, -5))

    rect = canvas._update_selection_and_emit_size.call_args[0][0].boundingRect()
    assert rect.left() == 0
    assert rect.top() == 0


def test_select_lasso_clamps_points_to_document(select_lasso_tool, qtbot):
    tool = select_lasso_tool
    canvas = tool.canvas
    canvas._document_size = QSize(16, 16)

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(-5, -5),
        QPoint(-5, -5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, QPoint(-5, -5))

    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert path.currentPosition() == QPoint(0, 0)

    canvas.selection_shape = path
    canvas._update_selection_and_emit_size.reset_mock()

    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(100, -5),
        QPoint(100, -5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, QPoint(100, -5))

    assert canvas.selection_shape.currentPosition() == QPoint(
        canvas._document_size.width(),
        0,
    )


def test_select_circle_reaches_top_left_edge(select_circle_tool, qtbot):
    tool = select_circle_tool
    canvas = tool.canvas

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(12, 12),
        QPoint(12, 12),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, QPoint(12, 12))

    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(-3, -7),
        QPoint(-3, -7),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, QPoint(-3, -7))

    rect = canvas._update_selection_and_emit_size.call_args[0][0].boundingRect()
    assert rect.left() == 0
    assert rect.top() == 0

def test_select_rectangle_mouse_events(select_rectangle_tool, qtbot):
    """
    This test should check that a rectangular selection is created as the mouse is pressed, moved, and released.
    """
    tool = select_rectangle_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    canvas._update_selection_and_emit_size.assert_called()
    assert tool.start_point == QPoint(10, 10)

    # Mouse Move
    canvas._update_selection_and_emit_size.reset_mock()
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(30, 40))
    canvas._update_selection_and_emit_size.assert_called()
    path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(path, QPainterPath)
    assert path.boundingRect() == QRectF(10, 10, 21, 31)


    # Mouse Release
    canvas.selection_shape = canvas._update_selection_and_emit_size.call_args[0][0]
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseReleaseEvent(release_event, QPoint(30, 40))
    canvas.selection_changed.emit.assert_called_with(True)


def test_select_rectangle_shift_adds_to_selection(select_rectangle_tool):
    tool = select_rectangle_tool
    canvas = tool.canvas

    base_selection = QPainterPath()
    base_selection.addRect(QRect(0, 0, 10, 10))
    canvas.selection_shape = base_selection

    start_point = QPoint(20, 20)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
    )
    tool.mousePressEvent(press_event, start_point)

    canvas._update_selection_and_emit_size.reset_mock()

    move_point = QPoint(30, 32)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
    )
    tool.mouseMoveEvent(move_event, move_point)

    canvas._update_selection_and_emit_size.assert_called()
    combined_path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(combined_path, QPainterPath)
    canvas.selection_shape = combined_path

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier,
    )
    tool.mouseReleaseEvent(release_event, move_point)

    expected_base = QPainterPath()
    expected_base.addRect(QRect(0, 0, 10, 10))

    dx = move_point.x() - start_point.x()
    dy = move_point.y() - start_point.y()
    size = min(abs(dx), abs(dy))
    adjusted_end = QPoint(
        start_point.x() + size * (1 if dx > 0 else -1),
        start_point.y() + size * (1 if dy > 0 else -1),
    )
    adjusted_end = tool._clamp_to_document(
        adjusted_end, extend_min=True, extend_max=True
    )

    expected_new = QPainterPath()
    expected_new.addRect(QRect(tool.start_point, adjusted_end).normalized())

    expected_combined = expected_base.united(expected_new).simplified()
    assert selection_paths_equal(combined_path, expected_combined)


def test_select_rectangle_alt_subtracts_from_selection(select_rectangle_tool):
    tool = select_rectangle_tool
    canvas = tool.canvas

    base_selection = QPainterPath()
    base_selection.addRect(QRect(0, 0, 30, 30))
    canvas.selection_shape = base_selection

    start_point = QPoint(5, 5)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
    )
    tool.mousePressEvent(press_event, start_point)

    canvas._update_selection_and_emit_size.reset_mock()

    move_point = QPoint(18, 17)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
    )
    tool.mouseMoveEvent(move_event, move_point)

    canvas._update_selection_and_emit_size.assert_called()
    combined_path = canvas._update_selection_and_emit_size.call_args[0][0]
    assert isinstance(combined_path, QPainterPath)
    canvas.selection_shape = combined_path

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
    )
    tool.mouseReleaseEvent(release_event, move_point)

    expected_base = QPainterPath()
    expected_base.addRect(QRect(0, 0, 30, 30))

    adjusted_end = tool._clamp_to_document(
        move_point, extend_min=True, extend_max=True
    )

    expected_new = QPainterPath()
    expected_new.addRect(QRect(tool.start_point, adjusted_end).normalized())

    expected_combined = expected_base.subtracted(expected_new).simplified()
    assert selection_paths_equal(combined_path, expected_combined)
