from unittest.mock import MagicMock, patch
from PySide6.QtGui import QPainter, QColor, QImage
from portal.renderer import CanvasRenderer
from portal.document import Document
from portal.canvas import Canvas
from portal.drawing_context import DrawingContext

def test_paint(qtbot):
    """Test that the canvas is rendered correctly, including the background, document, border, grid, and cursor."""
    mock_canvas = MagicMock()
    mock_canvas.palette.return_value.color.return_value = QColor("red")
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
