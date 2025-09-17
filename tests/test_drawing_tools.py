# This file will contain tests for drawing tools.
from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint, Qt, QRect, QSize
from PySide6.QtGui import QMouseEvent, QColor, QImage
from portal.core.command import DrawCommand, ShapeCommand, FillCommand, MoveCommand, CompositeCommand
from portal.core.drawing import Drawing
from portal.tools.pentool import PenTool
from portal.tools.linetool import LineTool
from portal.tools.rectangletool import RectangleTool
from portal.tools.ellipsetool import EllipseTool
from portal.tools.buckettool import BucketTool
from portal.tools.erasertool import EraserTool
from portal.tools.pickertool import PickerTool
from portal.tools.movetool import MoveTool
from PySide6.QtGui import QPainterPath, QPainter

def test_draw_line_wraps_across_edges():
    image = QImage(8, 8, QImage.Format_ARGB32)
    image.fill(QColor("transparent"))
    painter = QPainter(image)
    drawing = Drawing()
    painter.setPen(QColor("black"))
    drawing.draw_line_with_brush(
        painter,
        QPoint(6, 3),
        QPoint(10, 3),
        QSize(8, 8),
        "Square",
        1,
        False,
        False,
        wrap=True,
        erase=False,
    )
    painter.end()

    painted = {x for x in range(8) if image.pixelColor(x, 3).alpha() > 0}
    assert painted == {0, 1, 2, 6, 7}
@pytest.fixture
def pen_tool(qtbot):
    mock_canvas = Mock()
    mock_layer = Mock()
    mock_layer.image.rect.return_value = QRect(0, 0, 256, 256)
    mock_layer.visible = True
    mock_canvas.document.layer_manager.active_layer = mock_layer
    mock_canvas.document.width = 256
    mock_canvas.document.height = 256
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.drawing_context.pen_width = 1
    mock_canvas.drawing_context.brush_type = "Square"
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.drawing_context.pattern_brush = None
    mock_canvas.drawing_context.mirror_x_position = None
    mock_canvas.drawing_context.mirror_y_position = None
    mock_canvas.selection_shape = None
    mock_canvas._document_size = QSize(256, 256)
    mock_canvas.temp_image = None
    mock_canvas.original_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    mock_canvas.tile_preview_enabled = False
    mock_canvas.drawing = Drawing()
    mock_canvas.is_erasing_preview = False
    tool = PenTool(mock_canvas)
    return tool

def test_pen_mouse_events(pen_tool, qtbot):
    """
    This test should check that a path is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = pen_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    assert tool.points == [QPoint(10, 10)]
    assert canvas.temp_image is not None

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 20))
    assert tool.points == [QPoint(10, 10), QPoint(20, 20)]

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 20))

    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, DrawCommand)
    assert command.erase is False
    assert command.points == [QPoint(10, 10), QPoint(20, 20)]
    assert tool.points == []
    assert canvas.temp_image is None
    assert canvas.original_image is None


def test_pen_tile_preview_overlay(pen_tool, qtbot):
    tool = pen_tool
    canvas = tool.canvas
    canvas.tile_preview_enabled = True

    start_point = QPoint(10, 10)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, start_point)

    assert canvas.tile_preview_image is not None
    assert canvas.tile_preview_image.pixelColor(start_point).alpha() > 0
    assert canvas.is_erasing_preview is False

    end_point = QPoint(20, 20)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        end_point,
        end_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, end_point)

    assert canvas.tile_preview_image.pixelColor(end_point).alpha() > 0

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        end_point,
        end_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mouseReleaseEvent(release_event, end_point)

    assert canvas.tile_preview_image is None


@pytest.fixture
def eraser_tool(qtbot):
    mock_canvas = Mock()
    mock_layer = Mock()
    mock_layer.image.rect.return_value = QRect(0, 0, 256, 256)
    mock_layer.visible = True
    mock_canvas.document.layer_manager.active_layer = mock_layer
    mock_canvas.document.width = 256
    mock_canvas.document.height = 256
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.drawing_context.pen_width = 1
    mock_canvas.drawing_context.brush_type = "Square"
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.drawing_context.pattern_brush = None
    mock_canvas.drawing_context.mirror_x_position = None
    mock_canvas.drawing_context.mirror_y_position = None
    mock_canvas.selection_shape = None
    mock_canvas._document_size = QSize(256, 256)
    mock_canvas.is_erasing_preview = False
    mock_canvas.temp_image = None
    mock_canvas.original_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    mock_canvas.tile_preview_enabled = False
    mock_canvas.drawing = Drawing()
    tool = EraserTool(mock_canvas)
    return tool

def test_eraser_mouse_events(eraser_tool, qtbot):
    """
    This test should verify that the DrawCommand is executed with erase=True when the mouse is released.
    """
    tool = eraser_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(press_event, QPoint(10, 10))
    assert canvas.is_erasing_preview is True
    assert tool.points == [QPoint(10, 10)]
    assert canvas.temp_image is not None

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 20))
    assert tool.points == [QPoint(10, 10), QPoint(20, 20)]

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
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


def test_eraser_tile_preview_overlay(eraser_tool, qtbot):
    tool = eraser_tool
    canvas = tool.canvas
    canvas.tile_preview_enabled = True

    start_point = QPoint(10, 10)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mousePressEvent(press_event, start_point)

    assert canvas.is_erasing_preview is True
    assert canvas.tile_preview_image is not None
    assert canvas.tile_preview_image.pixelColor(start_point).alpha() > 0

    end_point = QPoint(20, 20)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        end_point,
        end_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, end_point)

    assert canvas.tile_preview_image.pixelColor(end_point).alpha() > 0

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        end_point,
        end_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mouseReleaseEvent(release_event, end_point)

    assert canvas.tile_preview_image is None
    assert canvas.is_erasing_preview is False


@pytest.fixture
def line_tool(qtbot):
    mock_canvas = Mock()
    mock_layer = Mock()
    mock_layer.image.rect.return_value = QRect(0, 0, 256, 256)
    mock_layer.visible = True
    mock_canvas.document.layer_manager.active_layer = mock_layer
    mock_canvas.document.width = 256
    mock_canvas.document.height = 256
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.drawing_context.pen_width = 1
    mock_canvas.drawing_context.brush_type = "Square"
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.drawing_context.pattern_brush = None
    mock_canvas.drawing_context.mirror_x_position = None
    mock_canvas.drawing_context.mirror_y_position = None
    mock_canvas.selection_shape = None
    mock_canvas._document_size = QSize(256, 256)
    mock_canvas.original_image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.original_image.fill(Qt.transparent)
    mock_canvas.temp_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    mock_canvas.tile_preview_enabled = False
    mock_canvas.drawing = Drawing()
    tool = LineTool(mock_canvas)
    return tool

def test_line_mouse_events(line_tool, qtbot):
    """
    This test should check that a line is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = line_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "line_tool_start")]
    assert tool.start_point == QPoint(10, 10)
    assert canvas.temp_image_replaces_active_layer is True

    # Mouse Move
    with patch.object(canvas.drawing, "draw_line_with_brush") as mock_draw_line:
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tool.mouseMoveEvent(move_event, QPoint(20, 20))
        assert canvas.temp_image is not None
        mock_draw_line.assert_called_once()

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
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


def test_line_tile_preview_overlay(line_tool, qtbot):
    tool = line_tool
    canvas = tool.canvas
    canvas.tile_preview_enabled = True

    start_point = QPoint(10, 10)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mousePressEvent(press_event, start_point)

    move_point = QPoint(20, 20)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, move_point)

    assert canvas.tile_preview_image is not None
    assert canvas.tile_preview_image.pixelColor(start_point).alpha() > 0
    assert canvas.tile_preview_image.pixelColor(move_point).alpha() > 0

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mouseReleaseEvent(release_event, move_point)

    assert canvas.tile_preview_image is None


@pytest.fixture
def picker_tool(qtbot):
    mock_canvas = Mock()
    mock_document = Mock()
    image = QImage(100, 100, QImage.Format_ARGB32)
    image.fill(QColor("blue"))
    image.setPixelColor(10, 10, QColor("red"))
    mock_document.render.return_value = image
    mock_canvas.document = mock_document
    mock_canvas.tile_preview_enabled = False
    tool = PickerTool(mock_canvas)
    return tool

def test_pick_color(picker_tool):
    """
    This test should verify that the correct color is picked from the rendered image.
    """
    tool = picker_tool
    canvas = tool.canvas

    # Test picking a colored pixel
    tool.pick_color(QPoint(10, 10))
    canvas.drawing_context.set_pen_color.assert_called_with("#ff0000")

    # Test picking a transparent pixel (alpha = 0)
    canvas.drawing_context.set_pen_color.reset_mock()
    image = canvas.document.render()
    image.setPixelColor(20, 20, QColor(0,0,0,0))
    tool.pick_color(QPoint(20, 20))
    canvas.drawing_context.set_pen_color.assert_not_called()

    # Test picking outside the image
    canvas.drawing_context.set_pen_color.reset_mock()
    tool.pick_color(QPoint(200, 200))
    canvas.drawing_context.set_pen_color.assert_not_called()


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
    mock_canvas.tile_preview_enabled = False
    tool = MoveTool(mock_canvas)
    return tool

def test_move_mouse_events_no_selection(move_tool, qtbot):
    """
    This test should verify that the layer content is moved correctly when there is no selection.
    """
    tool = move_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("cut_selection", "move_tool_start_no_selection")]

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 30), QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with patch.object(QPainter, "drawImage") as mock_draw_image:
        tool.mouseMoveEvent(move_event, QPoint(20, 30))
        mock_draw_image.assert_called_with(QPoint(10, 20), canvas.original_image)

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 30), QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 30))
    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, MoveCommand)
    assert command.delta == QPoint(10, 20)

def test_move_mouse_events_with_selection(move_tool, qtbot):
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
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("cut_selection", "move_tool_start")]

    # Mouse Move
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 30), QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mouseMoveEvent(move_event, QPoint(20, 30))
    expected_path = selection_path.translated(10, 20)
    assert canvas.selection_shape == expected_path

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 30), QPoint(20, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(20, 30))
    assert blocker.signal_triggered
    command = blocker.args[0]
    if isinstance(command, CompositeCommand):
        move_commands = [cmd for cmd in command.commands if isinstance(cmd, MoveCommand)]
        assert move_commands, "Composite command should include a MoveCommand"
        move_command = move_commands[0]
    else:
        move_command = command
    assert move_command.delta == QPoint(10, 20)
    assert move_command.original_selection_shape == selection_path


@pytest.fixture
def bucket_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.document.layer_manager.active_layer = Mock()
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.selection_shape = None
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.tile_preview_enabled = False

    tool = BucketTool(mock_canvas)
    return tool

def test_bucket_mouse_press_event(bucket_tool, qtbot):
    """
    This test should verify that the FillCommand is executed when the mouse is pressed.
    """
    tool = bucket_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    doc_pos = QPoint(10, 10)

    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(event, doc_pos)

    assert blocker.signal_triggered
    assert isinstance(blocker.args[0], FillCommand)


@pytest.fixture
def ellipse_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.document.layer_manager.active_layer = Mock()
    mock_canvas.document.layer_manager.active_layer.visible = True
    mock_canvas.drawing_context.pen_color = QColor("red")
    mock_canvas.drawing_context.pen_width = 1
    mock_canvas.drawing_context.brush_type = "Square"
    mock_canvas.drawing_context.mirror_x = False
    mock_canvas.drawing_context.mirror_y = False
    mock_canvas.drawing_context.pattern_brush = None
    mock_canvas.drawing_context.mirror_x_position = None
    mock_canvas.drawing_context.mirror_y_position = None
    mock_canvas.selection_shape = None
    mock_canvas._document_size = QSize(256, 256)
    mock_canvas.original_image = QImage(256, 256, QImage.Format_ARGB32)
    mock_canvas.original_image.fill(Qt.transparent)
    mock_canvas.temp_image = None
    mock_canvas.temp_image_replaces_active_layer = False
    mock_canvas.tile_preview_enabled = False
    mock_canvas.drawing = Drawing()
    tool = EllipseTool(mock_canvas)
    return tool

def test_ellipse_mouse_events(ellipse_tool, qtbot):
    """
    This test should check that an ellipse is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = ellipse_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "ellipse_tool_start")]
    assert tool.start_point == QPoint(10, 10)
    assert canvas.temp_image_replaces_active_layer is True

    # Mouse Move
    with patch.object(canvas.drawing, "draw_ellipse") as mock_draw_ellipse:
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tool.mouseMoveEvent(move_event, QPoint(30, 40))
        assert canvas.temp_image is not None
        mock_draw_ellipse.assert_called_once()
        # We can do more detailed checks on the arguments if needed

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
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


def test_ellipse_tile_preview_overlay(ellipse_tool, qtbot):
    tool = ellipse_tool
    canvas = tool.canvas
    canvas.tile_preview_enabled = True

    start_point = QPoint(10, 10)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mousePressEvent(press_event, start_point)

    move_point = QPoint(30, 40)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, move_point)

    assert canvas.tile_preview_image is not None
    top_center = QPoint((start_point.x() + move_point.x()) // 2, start_point.y())
    assert canvas.tile_preview_image.pixelColor(top_center).alpha() > 0

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mouseReleaseEvent(release_event, move_point)

    assert canvas.tile_preview_image is None


def test_rectangle_tile_preview_overlay(rectangle_tool, qtbot):
    tool = rectangle_tool
    canvas = tool.canvas
    canvas.tile_preview_enabled = True

    start_point = QPoint(10, 10)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        start_point,
        start_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mousePressEvent(press_event, start_point)

    move_point = QPoint(30, 40)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tool.mouseMoveEvent(move_event, move_point)

    assert canvas.tile_preview_image is not None
    assert canvas.tile_preview_image.pixelColor(start_point).alpha() > 0
    top_edge_point = QPoint(move_point.x(), start_point.y())
    assert canvas.tile_preview_image.pixelColor(top_edge_point).alpha() > 0

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        move_point,
        move_point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(tool.command_generated):
        tool.mouseReleaseEvent(release_event, move_point)

    assert canvas.tile_preview_image is None


from portal.ui.canvas import Canvas
from portal.core.drawing_context import DrawingContext
from portal.core.document import Document

@pytest.fixture
def rectangle_tool(qtbot):
    drawing_context = DrawingContext()
    canvas = Canvas(drawing_context)
    qtbot.addWidget(canvas)
    drawing_context.setParent(canvas)
    document = Document(256, 256)
    canvas.set_document(document)
    drawing_context.pen_color = QColor("red")
    drawing_context.pen_width = 1
    drawing_context.brush_type = "Square"
    drawing_context.mirror_x = False
    drawing_context.mirror_y = False
    drawing_context.pattern_brush = None
    canvas.selection_shape = None
    canvas.original_image = QImage(256, 256, QImage.Format_ARGB32)
    canvas.original_image.fill(Qt.transparent)
    canvas.temp_image = None
    canvas.temp_image_replaces_active_layer = False
    canvas.tile_preview_enabled = False
    tool = RectangleTool(canvas)
    return tool

def test_rectangle_mouse_events(rectangle_tool, qtbot):
    """
    This test should check that a rectangle is drawn correctly as the mouse is pressed, moved, and released.
    """
    tool = rectangle_tool
    canvas = tool.canvas

    # Mouse Press
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mousePressEvent(press_event, QPoint(10, 10))
    assert blocker.signal_triggered
    assert blocker.args == [("get_active_layer_image", "rectangle_tool_start")]
    assert tool.start_point == QPoint(10, 10)
    assert canvas.temp_image_replaces_active_layer is True

    # Mouse Move
    with patch.object(canvas.drawing, "draw_rect") as mock_draw_rect:
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        tool.mouseMoveEvent(move_event, QPoint(30, 40))
        assert canvas.temp_image is not None
        mock_draw_rect.assert_called_once()

    # Mouse Release
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(30, 40), QPoint(30, 40), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(tool.command_generated) as blocker:
        tool.mouseReleaseEvent(release_event, QPoint(30, 40))

    assert blocker.signal_triggered
    command = blocker.args[0]
    assert isinstance(command, ShapeCommand)
    assert command.shape_type == 'rectangle'
    assert command.rect == QRect(10, 10, 21, 31)
    assert canvas.temp_image is None
    assert canvas.original_image is None
    assert canvas.temp_image_replaces_active_layer is False
