from unittest.mock import MagicMock, patch
from PySide6.QtGui import QPainter, QColor
from portal.renderer import CanvasRenderer

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
