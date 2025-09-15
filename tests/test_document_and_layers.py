import pytest
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QCursor
from portal.core.document import Document
from portal.core.layer import Layer
from portal.core.layer_manager import LayerManager
from portal.core.drawing import Drawing
from PySide6.QtCore import QPoint, QSize
from portal.core.renderer import CanvasRenderer
from portal.ui.canvas import Canvas
from portal.core.drawing_context import DrawingContext
from portal.ui.background import Background
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QMouseEvent
from unittest.mock import MagicMock, patch, Mock
import os

@pytest.fixture
def drawing_context():
    return DrawingContext()

@pytest.fixture
def document():
    """Returns a Document with two layers."""
    doc = Document(100, 100)
    doc.layer_manager.add_layer("Layer 2")
    # Fill layers with some content for rendering tests
    layer1 = doc.layer_manager.layers[0]
    layer2 = doc.layer_manager.layers[1]
    layer1.image.fill(QColor(255, 0, 0, 128))  # Semi-transparent red
    layer2.image.fill(QColor(0, 0, 255, 128))  # Semi-transparent blue
    return doc

def test_clone(document):
    """Test that a deep copy of the document is created."""
    clone = document.clone()

    # Check that it's a new object
    assert clone is not document

    # Check that the properties are the same
    assert clone.width == document.width
    assert clone.height == document.height

    # Check that the layer manager is also a clone
    assert clone.layer_manager is not document.layer_manager
    assert len(clone.layer_manager.layers) == len(document.layer_manager.layers)

    # Check that the layers are clones
    for i in range(len(clone.layer_manager.layers)):
        assert clone.layer_manager.layers[i] is not document.layer_manager.layers[i]
        assert clone.layer_manager.layers[i].image.constBits() == document.layer_manager.layers[i].image.constBits()

def test_render(document):
    """Test that all visible layers are correctly composited into a single image."""
    rendered_image = document.render()

    # The expected color is a blend of semi-transparent red and semi-transparent blue
    # This is a simplified check. A more accurate check would involve calculating the exact blended color.
    # For now, we'll just check that it's not the color of either layer or the background.
    pixel_color = rendered_image.pixelColor(50, 50)
    assert pixel_color != QColor(255, 0, 0, 128)
    assert pixel_color != QColor(0, 0, 255, 128)
    assert pixel_color != QColor(0, 0, 0, 0)

    # Test with one layer hidden
    document.layer_manager.layers[0].visible = False
    rendered_image = document.render()
    pixel_color = rendered_image.pixelColor(50, 50)
    assert pixel_color == QColor(0, 0, 255, 128)

def test_save_load_tiff(document):
    """Test that a document with multiple layers can be saved and loaded as a TIFF file."""
    filepath = "test.tiff"
    document.save_tiff(filepath)

    loaded_document = Document.load_tiff(filepath)

    assert loaded_document.width == document.width
    assert loaded_document.height == document.height
    assert len(loaded_document.layer_manager.layers) == len(document.layer_manager.layers)

    for i in range(len(document.layer_manager.layers)):
        original_layer = document.layer_manager.layers[i]
        loaded_layer = loaded_document.layer_manager.layers[i]
        assert original_layer.name == loaded_layer.name
        assert original_layer.visible == loaded_layer.visible
        assert original_layer.opacity == loaded_layer.opacity
        assert original_layer.image.constBits() == loaded_layer.image.constBits()

    os.remove(filepath)

def test_flip_horizontal_vertical(document):
    """Test that all layers in the document are flipped correctly."""
    # Create a non-symmetrical image on each layer
    for layer in document.layer_manager.layers:
        layer.image.fill(QColor(0, 0, 0, 0))
        layer.image.setPixelColor(0, 0, QColor("red"))
        layer.image.setPixelColor(99, 99, QColor("blue"))

    for layer in document.layer_manager.layers:
        layer.flip_horizontal()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(99, 0) == QColor("red")
        assert layer.image.pixelColor(0, 99) == QColor("blue")

    for layer in document.layer_manager.layers:
        layer.flip_vertical()
    for layer in document.layer_manager.layers:
        assert layer.image.pixelColor(99, 99) == QColor("red")
        assert layer.image.pixelColor(0, 0) == QColor("blue")

def test_resize(document):
    """Test that all layers in the document are resized correctly."""
    new_width = 200
    new_height = 200
    document.resize(new_width, new_height, "nearest")

    assert document.width == new_width
    assert document.height == new_height
    for layer in document.layer_manager.layers:
        assert layer.image.width() == new_width
        assert layer.image.height() == new_height

def test_crop(document):
    """Test that all layers in the document are cropped correctly."""
    crop_rect = QRect(10, 10, 50, 50)
    document.crop(crop_rect)

    assert document.width == crop_rect.width()
    assert document.height == crop_rect.height()
    assert document.layer_manager.width == crop_rect.width()
    assert document.layer_manager.height == crop_rect.height()
    for layer in document.layer_manager.layers:
        assert layer.image.width() == crop_rect.width()
        assert layer.image.height() == crop_rect.height()


def test_crop_expands_document_when_selection_is_larger():
    """Cropping with a selection larger than the document should expand the canvas."""
    doc = Document(10, 10)
    base_layer = doc.layer_manager.layers[0]
    base_layer.image.fill(QColor(0, 0, 0, 0))
    base_layer.image.setPixelColor(0, 0, QColor("red"))

    selection_rect = QRect(-5, -3, 20, 20)
    doc.crop(selection_rect)

    assert doc.width == selection_rect.width()
    assert doc.height == selection_rect.height()
    assert doc.layer_manager.width == selection_rect.width()
    assert doc.layer_manager.height == selection_rect.height()

    assert base_layer.image.width() == selection_rect.width()
    assert base_layer.image.height() == selection_rect.height()
    assert base_layer.image.pixelColor(5, 3) == QColor("red")

    doc.layer_manager.add_layer("Post Crop")
    new_layer = doc.layer_manager.active_layer
    assert new_layer.image.width() == selection_rect.width()
    assert new_layer.image.height() == selection_rect.height()


def test_set_layer_opacity_command(document):
    """Test that setting layer opacity is undoable and affects rendering."""
    top_layer = document.layer_manager.layers[1]
    bottom_color = document.layer_manager.layers[0].image.pixelColor(50, 50)
    blended_before = document.render().pixelColor(50, 50)

    from portal.core.command import SetLayerOpacityCommand

    command = SetLayerOpacityCommand(top_layer, 0.0)
    command.execute()
    assert top_layer.opacity == 0.0
    rendered = document.render()
    assert rendered.pixelColor(50, 50) == bottom_color

    command.undo()
    assert top_layer.opacity == 1.0
    rendered_after = document.render()
    assert rendered_after.pixelColor(50, 50) == blended_before


def test_layer_manager_opacity_preview_and_commit():
    """Layer opacity previews while dragging and commits with undo support."""
    from PySide6.QtWidgets import QApplication
    app_qt = QApplication.instance() or QApplication([])
    from portal.core.app import App
    from portal.ui.layer_manager_widget import LayerManagerWidget
    from unittest.mock import MagicMock

    app = App()
    app.new_document(10, 10)
    canvas = MagicMock()
    lm_widget = LayerManagerWidget(app, canvas)

    item = lm_widget.layer_list.item(0)
    item_widget = lm_widget.layer_list.itemWidget(item)
    layer = item_widget.layer

    lm_widget.on_opacity_preview_changed(item_widget, 50)
    assert layer.opacity == 0.5

    lm_widget.on_opacity_changed(item_widget, 50, 25)
    assert layer.opacity == 0.25

    app.undo()
    assert layer.opacity == 0.5


@pytest.fixture
def layer():
    """Returns a Layer instance."""
    return Layer(100, 100, "Test Layer")

def test_layer_creation(layer):
    """Test that a layer is created with the correct name, visibility, and opacity."""
    assert layer.name == "Test Layer"
    assert layer.visible is True
    assert layer.opacity == 1.0
    assert layer.image.width() == 100
    assert layer.image.height() == 100

def test_clear(layer):
    """Test that the layer is filled with a transparent color."""
    layer.image.fill(QColor("blue"))
    layer.clear()
    for x in range(layer.image.width()):
        for y in range(layer.image.height()):
            assert layer.image.pixelColor(x, y) == QColor(0, 0, 0, 0)

def test_clone(layer):
    """Test that a deep copy of the layer is created."""
    layer.image.fill(QColor("red"))
    clone = layer.clone()

    assert clone is not layer
    assert clone.name == layer.name
    assert clone.visible == layer.visible
    assert clone.opacity == layer.opacity
    assert clone.image.constBits() == layer.image.constBits()

    # Modify the clone and check that the original is not affected
    clone.name = "Cloned Layer"
    clone.visible = False
    clone.image.fill(QColor("green"))

    assert layer.name == "Test Layer"
    assert layer.visible is True
    assert layer.image.pixelColor(50, 50) == QColor("red")


@pytest.fixture
def layer_manager():
    """Returns a LayerManager instance."""
    return LayerManager(100, 100)

def test_add_layer(layer_manager):
    """Test that a new layer is added to the top of the stack."""
    initial_layer_count = len(layer_manager.layers)
    layer_manager.add_layer("New Layer")
    assert len(layer_manager.layers) == initial_layer_count + 1
    assert layer_manager.layers[-1].name == "New Layer"
    assert layer_manager.active_layer_index == initial_layer_count


def test_remove_layer(layer_manager):
    """Test that the layer at the given index is removed."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    initial_layer_count = len(layer_manager.layers)
    layer_to_remove_index = 1
    layer_manager.remove_layer(layer_to_remove_index)
    assert len(layer_manager.layers) == initial_layer_count - 1
    assert layer_manager.active_layer_index == 1


def test_select_layer(layer_manager):
    """Test that the layer at the given index is selected as the active one."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_select_index = 1
    layer_manager.select_layer(layer_to_select_index)
    assert layer_manager.active_layer_index == layer_to_select_index


def test_move_layer_up(layer_manager):
    """Test that the layer at the given index is moved up one step in the stack."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_move_index = 1
    layer_to_move = layer_manager.layers[layer_to_move_index]
    layer_manager.move_layer_up(layer_to_move_index)
    assert layer_manager.layers[layer_to_move_index + 1] == layer_to_move


def test_move_layer_down(layer_manager):
    """Test that the layer at the given index is moved down one step in the stack."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    layer_to_move_index = 2
    layer_to_move = layer_manager.layers[layer_to_move_index]
    layer_manager.move_layer_down(layer_to_move_index)
    assert layer_manager.layers[layer_to_move_index - 1] == layer_to_move


def test_merge_layer_down(layer_manager):
    """Test that the layer at the given index is merged with the layer below it."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    initial_layer_count = len(layer_manager.layers)
    layer_to_merge_index = 2
    layer_manager.merge_layer_down(layer_to_merge_index)
    assert len(layer_manager.layers) == initial_layer_count - 1


def test_toggle_visibility(layer_manager):
    """Test that toggling visibility emits a command."""
    layer_manager.add_layer("Layer 1")
    layer_to_toggle_index = 1

    spy = Mock()
    layer_manager.command_generated.connect(spy)

    layer_manager.toggle_visibility(layer_to_toggle_index)

    spy.assert_called_once()
    command = spy.call_args[0][0]
    from portal.commands.layer_commands import SetLayerVisibleCommand
    assert isinstance(command, SetLayerVisibleCommand)
    assert command.layer_index == layer_to_toggle_index
    assert command.visible is False # The initial visibility is True


def test_clone(layer_manager):
    """Test that a deep copy of the layer manager is created."""
    layer_manager.add_layer("Layer 1")
    layer_manager.add_layer("Layer 2")
    new_manager = layer_manager.clone()
    assert new_manager is not layer_manager
    assert len(new_manager.layers) == len(layer_manager.layers)
    for i in range(len(new_manager.layers)):
        assert new_manager.layers[i] is not layer_manager.layers[i]


@pytest.fixture
def drawing():
    """Returns a Drawing instance."""
    return Drawing()

@pytest.fixture
def image():
    """Returns a blank QImage."""
    return QImage(100, 100, QImage.Format_ARGB32)

def test_draw_brush(drawing, image):
    """Test that the correct brush is drawn at the specified point, including mirrored points."""
    painter = QPainter(image)
    point = QPoint(25, 25)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 10
    painter.setPen(QColor("red"))

    drawing.draw_brush(painter, point, doc_size, brush_type, width, True, True)
    painter.end()

    # Check original and mirrored points
    assert image.pixelColor(25, 25) == QColor("red")
    assert image.pixelColor(74, 25) == QColor("red")
    assert image.pixelColor(25, 74) == QColor("red")
    assert image.pixelColor(74, 74) == QColor("red")

def test_erase_brush(drawing, image):
    """Test that the correct brush is used to erase at the specified point, including mirrored points."""
    image.fill(QColor("red"))
    painter = QPainter(image)
    point = QPoint(25, 25)
    doc_size = QSize(100, 100)
    width = 10

    drawing.erase_brush(painter, point, doc_size, width, True, True)
    painter.end()

    # Check original and mirrored points
    assert image.pixelColor(25, 25) == QColor(0, 0, 0, 0)
    assert image.pixelColor(74, 25) == QColor(0, 0, 0, 0)
    assert image.pixelColor(25, 74) == QColor(0, 0, 0, 0)
    assert image.pixelColor(74, 74) == QColor(0, 0, 0, 0)

def test_draw_line_with_brush(drawing, image):
    """Test that a line is drawn correctly using the selected brush."""
    painter = QPainter(image)
    start_point = QPoint(10, 10)
    end_point = QPoint(90, 90)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 5
    painter.setPen(QColor("blue"))

    drawing.draw_line_with_brush(painter, start_point, end_point, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a point along the line
    assert image.pixelColor(50, 50) == QColor("blue")

def test_draw_rect(drawing, image):
    """Test that a rectangle is drawn correctly."""
    painter = QPainter(image)
    rect = QRect(20, 20, 60, 60)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 1
    painter.setPen(QColor("green"))

    drawing.draw_rect(painter, rect, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a corner of the rectangle
    assert image.pixelColor(20, 20) == QColor("green")

def test_draw_ellipse(drawing, image):
    """Test that an ellipse is drawn correctly."""
    painter = QPainter(image)
    rect = QRect(20, 20, 60, 60)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 1
    painter.setPen(QColor("purple"))

    drawing.draw_ellipse(painter, rect, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a point on the ellipse's circumference
    assert image.pixelColor(50, 20).alpha() != 0

def test_flood_fill(drawing):
    """Test that the flood_fill algorithm correctly fills the area."""
    layer = Layer(100, 100, "Test Layer")
    # Create a black square to be filled
    for x in range(40, 60):
        for y in range(40, 60):
            layer.image.setPixelColor(x, y, QColor("black"))

    fill_pos = QPoint(50, 50)
    fill_color = QColor("yellow")

    drawing.flood_fill(layer, fill_pos, fill_color, None)

    # Check that the center of the square is now yellow
    assert layer.image.pixelColor(50, 50) == fill_color
    # Check that a point outside the square is not yellow
    assert layer.image.pixelColor(30, 30) != fill_color


def test_paint(qtbot):
    """Test that the canvas is rendered correctly, including the background, document, border, grid, and cursor."""
    mock_canvas = MagicMock()
    mock_canvas.palette.return_value.color.return_value = QColor("red")
    mock_canvas.tile_preview_enabled = False
    mock_drawing_context = MagicMock()
    mock_document = MagicMock()
    mock_painter = MagicMock(spec=QPainter)

    renderer = CanvasRenderer(mock_canvas, mock_drawing_context)

    with patch.object(renderer, '_draw_background') as mock_draw_background, \
         patch.object(renderer, '_draw_document') as mock_draw_document, \
         patch.object(renderer, '_draw_border') as mock_draw_border, \
         patch.object(renderer, 'draw_grid') as mock_draw_grid, \
         patch.object(renderer, 'draw_cursor') as mock_draw_cursor:

        renderer.paint(mock_painter, mock_document)

        mock_draw_background.assert_called_once()
        mock_draw_document.assert_called_once()
        mock_draw_border.assert_called_once()
        mock_draw_grid.assert_called_once()
        mock_draw_cursor.assert_called_once()

def test_eraser_preview_layer_order(qtbot):
    """Test that the eraser preview renders the layers in the correct order."""
    drawing_context = DrawingContext()
    canvas = Canvas(drawing_context)
    qtbot.addWidget(canvas)
    drawing_context.setParent(canvas)
    document = Document(64, 64)
    canvas.resize(64, 64)
    canvas.set_document(document)
    canvas.zoom = 1.0
    canvas.background.color = QColor("white")

    # Layer 1 (bottom): Red
    document.layer_manager.layers[0].image.fill(QColor("red"))

    # Layer 2 (middle): Green
    document.layer_manager.add_layer("Middle Layer")
    document.layer_manager.active_layer.image.fill(QColor("green"))

    # Layer 3 (top): Blue
    document.layer_manager.add_layer("Top Layer")
    document.layer_manager.active_layer.image.fill(QColor("blue"))

    # Set active layer to the middle layer
    document.layer_manager.select_layer(1)

    # Start eraser preview
    canvas.is_erasing_preview = True
    canvas.temp_image = QImage(64, 64, QImage.Format_ARGB32)
    canvas.temp_image.fill(QColor("black")) # Erase everything

    # Render the canvas
    image = QImage(64, 64, QImage.Format_ARGB32)
    painter = QPainter(image)
    canvas.renderer.paint(painter, document)
    painter.end()

    # The top layer should be blue, the middle layer should be transparent (erased), and the bottom layer should be red.
    # So the final color should be blue, since it's on top.
    assert image.pixelColor(32, 32) == QColor("blue")

    # Now let's make the top layer invisible
    document.layer_manager.layers[2].visible = False

    # Render the canvas again
    painter = QPainter(image)
    canvas.renderer.paint(painter, document)
    painter.end()

    # The top layer is invisible, the middle layer is erased (transparent), so we should see the bottom layer, which is red.
    assert image.pixelColor(32, 32) == QColor("red")


def test_background_creation_checkered():
    bg = Background()
    assert bg.is_checkered is True
    assert bg.color is None

def test_background_creation_with_color():
    color = QColor("red")
    bg = Background(color)
    assert bg.is_checkered is False
    assert bg.color == color


@pytest.fixture
def canvas(qapp, drawing_context):
    canvas = Canvas(drawing_context)
    canvas.set_document(Document(100, 100))
    drawing_context.set_pen_color(QColor("red"))
    drawing_context.set_pen_width(5)
    drawing_context.set_brush_type("Square")
    canvas.on_tool_changed("Pen")
    return canvas

def test_pen_tool_emits_command(canvas):
    """
    Test that using the Pen tool correctly emits the command_generated signal
    with the right data.
    """
    spy = Mock()
    canvas.command_generated.connect(spy)

    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)

    canvas.mousePressEvent(press_event)
    canvas.mouseMoveEvent(move_event)
    canvas.mouseReleaseEvent(release_event)

    spy.assert_called_once()
    command = spy.call_args[0][0]
    from portal.core.command import DrawCommand
    assert isinstance(command, DrawCommand)
    assert len(command.points) == 2
    assert command.points[0] == canvas.get_doc_coords(QPoint(10, 10))
    assert command.points[1] == canvas.get_doc_coords(QPoint(20, 20))
    assert command.color == QColor("red")
    assert command.width == 5
    assert command.brush_type == "Square"
    assert command.erase is False
    assert command.selection_shape is None

def test_set_background(canvas):
    """Test that the background is updated correctly."""
    from portal.ui.background import Background
    background = Background(QColor("blue"))
    canvas.set_background(background)
    assert canvas.background == background

def test_select_all(canvas):
    """Test that a selection is created for the entire document."""
    from PySide6.QtCore import QRect
    canvas.select_all()
    assert canvas.selection_shape is not None
    assert canvas.selection_shape.boundingRect() == QRect(0, 0, canvas.document.width, canvas.document.height)

def test_select_none(canvas):
    """Test that the selection is cleared."""
    canvas.select_all()
    assert canvas.selection_shape is not None
    canvas.select_none()
    assert canvas.selection_shape is None

def test_invert_selection(canvas):
    """Test that the selection is inverted correctly."""
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import QRect
    rect = QRect(0, 0, 50, 50)
    path = QPainterPath()
    path.addRect(rect)
    canvas.selection_shape = path
    canvas.invert_selection()
    assert not canvas.selection_shape.contains(QPoint(25, 25))
    assert canvas.selection_shape.contains(QPoint(75, 75))

def test_get_doc_coords(canvas):
    """Test that canvas coordinates are correctly converted to document coordinates."""
    canvas.zoom = 2.0
    canvas.x_offset = 0
    canvas.y_offset = 0
    canvas_width = canvas.width()
    canvas_height = canvas.height()
    canvas_center = QPoint(canvas_width / 2, canvas_height / 2)
    doc_center = canvas.get_doc_coords(canvas_center)
    assert doc_center == QPoint(canvas.document.width / 2, canvas.document.height / 2)

def test_get_canvas_coords(canvas):
    """Test that document coordinates are correctly converted to canvas coordinates."""
    canvas.zoom = 2.0
    canvas.x_offset = 0
    canvas.y_offset = 0
    canvas_width = canvas.width()
    canvas_height = canvas.height()
    doc_center = QPoint(canvas.document.width / 2, canvas.document.height / 2)
    canvas_center = canvas.get_canvas_coords(doc_center)
    assert canvas_center == QPoint(canvas_width / 2, canvas_height / 2)

def test_mouse_press_event(canvas):
    """Test that the correct tool's mousePressEvent is called."""
    mock_tool = Mock()
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mousePressEvent(event)
    mock_tool.mousePressEvent.assert_called_once()

def test_mouse_move_event(canvas):
    """Test that the correct tool's mouseMoveEvent is called and cursor position is updated."""
    mock_tool = Mock()
    mock_tool.cursor = QCursor(Qt.CrossCursor)
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mouseMoveEvent(event)
    mock_tool.mouseMoveEvent.assert_called_once()
    assert canvas.cursor_doc_pos != QPoint(0, 0)

def test_mouse_release_event(canvas):
    """Test that the correct tool's mouseReleaseEvent is called."""
    mock_tool = Mock()
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mouseReleaseEvent(event)
    mock_tool.mouseReleaseEvent.assert_called_once()

def test_wheel_event(canvas):
    """Test that the zoom level and offsets are updated correctly."""
    from PySide6.QtGui import QWheelEvent
    initial_zoom = canvas.zoom
    initial_x_offset = canvas.x_offset
    initial_y_offset = canvas.y_offset
    event_in = QWheelEvent(QPoint(50, 50), QPoint(50, 50), QPoint(0, 120), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    canvas.wheelEvent(event_in)
    assert canvas.zoom > initial_zoom
    assert canvas.x_offset != initial_x_offset
    assert canvas.y_offset != initial_y_offset
    event_out = QWheelEvent(QPoint(50, 50), QPoint(50, 50), QPoint(0, -120), QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    canvas.wheelEvent(event_out)
    assert canvas.zoom == pytest.approx(initial_zoom)

def test_toggle_grid(canvas):
    """Test that the grid visibility is toggled and the canvas is updated."""
    from unittest.mock import patch
    assert not canvas.grid_visible
    with patch.object(canvas, 'update') as mock_update:
        canvas.toggle_grid()
        assert canvas.grid_visible
        mock_update.assert_called_once()
    with patch.object(canvas, 'update') as mock_update:
        canvas.toggle_grid()
        assert not canvas.grid_visible
        mock_update.assert_called_once()


@pytest.fixture
def app(qapp):
    """Returns an App instance."""
    from portal.core.app import App
    from portal.ui.ui import MainWindow

    # Mock the main window and other UI components
    # to avoid actual window creation during tests.
    app = App()
    app.main_window = MagicMock(spec=MainWindow)
    app.main_window.canvas = MagicMock(spec=Canvas)
    return app


class TestClipboard:
    def test_copy_layer(self, app):
        """Test that the entire layer is copied to the clipboard when there is no selection."""
        from PySide6.QtWidgets import QApplication

        # Setup document and layer
        app.new_document(10, 10)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("red"))

        # Mock selection to be empty
        app.main_window.canvas.selection_shape = None

        # Perform copy
        app.clipboard_service.copy()

        # Verify clipboard
        clipboard = QApplication.clipboard()
        clipboard_image = clipboard.image()
        assert not clipboard_image.isNull()
        assert clipboard_image.size() == active_layer.image.size()
        assert clipboard_image.pixelColor(5, 5) == QColor("red")

    def test_copy_selection(self, app):
        """Test that only the selected area is copied to the clipboard."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPainterPath

        # Setup document and layer
        app.new_document(20, 20)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("blue"))

        # Mock selection
        selection_rect = QRect(5, 5, 10, 10)
        selection_shape = QPainterPath()
        selection_shape.addRect(selection_rect)
        app.main_window.canvas.selection_shape = selection_shape

        # Perform copy
        app.clipboard_service.copy()

        # Verify clipboard
        clipboard = QApplication.clipboard()
        clipboard_image = clipboard.image()
        assert not clipboard_image.isNull()
        assert clipboard_image.size() == selection_rect.size()
        assert clipboard_image.pixelColor(0, 0) == QColor("blue")

    def test_cut_layer(self, app):
        """Test that the entire layer is copied and then cleared."""
        from PySide6.QtWidgets import QApplication

        # Setup document and layer
        app.new_document(10, 10)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("green"))

        # Mock selection to be empty
        app.main_window.canvas.selection_shape = None

        # Perform cut
        app.clipboard_service.cut()

        # Verify clipboard
        clipboard = QApplication.clipboard()
        clipboard_image = clipboard.image()
        assert not clipboard_image.isNull()
        assert clipboard_image.pixelColor(5, 5) == QColor("green")

        # Verify layer is cleared
        assert active_layer.image.pixelColor(5, 5) == QColor(0, 0, 0, 0)

    def test_cut_selection(self, app):
        """Test that the selected area is copied and then cleared."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPainterPath

        # Setup document and layer
        app.new_document(20, 20)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("purple"))
        # Fill a non-selected area to ensure it's not cleared
        active_layer.image.setPixelColor(1, 1, QColor("red"))


        # Mock selection
        selection_rect = QRect(5, 5, 10, 10)
        selection_shape = QPainterPath()
        selection_shape.addRect(selection_rect)
        app.main_window.canvas.selection_shape = selection_shape

        # Perform cut
        app.clipboard_service.cut()

        # Verify clipboard
        clipboard = QApplication.clipboard()
        clipboard_image = clipboard.image()
        assert not clipboard_image.isNull()
        assert clipboard_image.size() == selection_rect.size()
        assert clipboard_image.pixelColor(0, 0) == QColor("purple")

        # Verify selected area is cleared
        assert active_layer.image.pixelColor(7, 7) == QColor(0, 0, 0, 0)
        # Verify non-selected area is not cleared
        assert active_layer.image.pixelColor(1, 1) == QColor("red")

    def test_paste(self, app):
        """Test that the image from the clipboard is pasted as a new layer."""
        from PySide6.QtWidgets import QApplication

        # Setup document
        app.new_document(10, 10)
        initial_layer_count = len(app.document.layer_manager.layers)

        # Put an image on the clipboard
        image_to_paste = QImage(5, 5, QImage.Format_ARGB32)
        image_to_paste.fill(QColor("yellow"))
        QApplication.clipboard().setImage(image_to_paste)

        # Mock no selection
        app.main_window.canvas.selection_shape = None

        # Perform paste
        app.clipboard_service.paste()

        # Verify new layer
        assert len(app.document.layer_manager.layers) == initial_layer_count + 1
        pasted_layer = app.document.layer_manager.active_layer
        assert pasted_layer.name == "Pasted Layer"
        assert pasted_layer.image.size() == app.document.render().size()
        assert pasted_layer.image.pixelColor(2, 2) == QColor("yellow")
        assert pasted_layer.image.pixelColor(7, 7) == QColor(0, 0, 0, 0)

    def test_paste_as_new_image(self, app):
        """Test that a new document is created with the image from the clipboard."""
        from PySide6.QtWidgets import QApplication

        # Put an image on the clipboard
        image_to_paste = QImage(30, 40, QImage.Format_ARGB32)
        image_to_paste.fill(QColor("orange"))
        QApplication.clipboard().setImage(image_to_paste)

        # Perform paste as new image
        app.clipboard_service.paste_as_new_image()

        # Verify new document
        assert app.document.width == 30
        assert app.document.height == 40
        assert len(app.document.layer_manager.layers) == 2 # Pasted layer + initial layer
        pasted_layer = app.document.layer_manager.active_layer
        assert pasted_layer.name == "Pasted Layer"
        assert pasted_layer.image.pixelColor(15, 15) == QColor("orange")

    def test_paste_in_selection_smaller_image(self, app):
        """Test pasting an image smaller than the selection."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPainterPath

        app.new_document(20, 20)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("blue"))

        selection_rect = QRect(5, 5, 10, 10)
        selection_shape = QPainterPath()
        selection_shape.addRect(selection_rect)
        app.main_window.canvas.selection_shape = selection_shape

        image_to_paste = QImage(6, 6, QImage.Format_ARGB32)
        image_to_paste.fill(QColor("yellow"))
        QApplication.clipboard().setImage(image_to_paste)

        app.clipboard_service.paste()

        new_layer = app.document.layer_manager.active_layer
        assert new_layer is not active_layer
        # Image (6x6) is pasted at selection top-left (5,5).
        assert new_layer.image.pixelColor(5, 5) == QColor("yellow") # Top-left of pasted
        assert new_layer.image.pixelColor(10, 10) == QColor("yellow") # Bottom-right of pasted
        assert new_layer.image.pixelColor(11, 11) == QColor(0, 0, 0, 0) # Outside pasted
        assert active_layer.image.pixelColor(10, 10) == QColor("blue") # Original layer unchanged

    def test_paste_in_selection_larger_image(self, app):
        """Test pasting an image larger than the selection (cropping)."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPainterPath

        app.new_document(20, 20)
        active_layer = app.document.layer_manager.active_layer
        active_layer.image.fill(QColor("blue"))

        selection_rect = QRect(5, 5, 10, 10)
        selection_shape = QPainterPath()
        selection_shape.addRect(selection_rect)
        app.main_window.canvas.selection_shape = selection_shape

        image_to_paste = QImage(12, 12, QImage.Format_ARGB32)
        image_to_paste.fill(QColor("yellow"))
        # Create a red pixel that should be cropped out
        image_to_paste.setPixelColor(0, 0, QColor("red"))
        QApplication.clipboard().setImage(image_to_paste)

        app.clipboard_service.paste()

        new_layer = app.document.layer_manager.active_layer
        assert new_layer is not active_layer
        # Image (12x12) is pasted at selection top-left (5,5).
        # The selection path will clip the drawing.
        assert new_layer.image.pixelColor(4, 4) == QColor(0, 0, 0, 0) # Outside selection
        # The red pixel at (0,0) of the original image is at (5,5) on the canvas.
        assert new_layer.image.pixelColor(5, 5) == QColor("red")
        # A yellow pixel from the original image.
        assert new_layer.image.pixelColor(6, 6) == QColor("yellow")
        # Check that the image is cropped. The image is 12x12, pasted at 5,5, so it ends at 16,16.
        # The selection is 10x10, so it ends at 14,14. The pixel at 15,15 should be transparent.
        assert new_layer.image.pixelColor(15, 15) == QColor(0, 0, 0, 0)
