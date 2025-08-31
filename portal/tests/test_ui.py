from unittest.mock import MagicMock, patch
from PySide6.QtGui import QColor, QImage
from portal.ui import ColorButton, ActiveColorButton, MainWindow

def test_color_button(qtbot):
    """Test that the set_pen_color method is called on the app when a color button is clicked."""
    mock_drawing_context = MagicMock()
    button = ColorButton(QColor("red"), mock_drawing_context)
    qtbot.addWidget(button)

    button.click()

    mock_drawing_context.set_pen_color.assert_called_once_with("#ff0000")

@patch("PySide6.QtWidgets.QColorDialog.getColor")
def test_active_color_button(mock_get_color, qtbot):
    """Test that the color dialog is opened and that the set_pen_color method is called on the app when a color is selected."""
    mock_drawing_context = MagicMock()
    mock_drawing_context.pen_color = QColor("blue")
    mock_get_color.return_value = QColor("green")

    button = ActiveColorButton(mock_drawing_context)
    qtbot.addWidget(button)

    button.click()

    mock_get_color.assert_called_once()
    mock_drawing_context.set_pen_color.assert_called_once_with(QColor("green"))

def test_update_dynamic_palette(qtbot, qapp):
    """Test that the saturation and value buttons are updated correctly when the pen color changes."""
    mock_app = MagicMock()
    mock_app.drawing_context.pen_color = QColor("red")
    mock_app.drawing_context.pen_width = 1
    mock_document = MagicMock()
    mock_document.width = 64
    mock_document.height = 64
    mock_document.render.return_value = QImage(64, 64, QImage.Format_RGB32)
    mock_app.document = mock_document

    # Mock methods that would otherwise cause issues in a test environment
    with patch.object(MainWindow, 'load_palette', return_value=[]), \
         patch.object(MainWindow, 'update_palette'), \
         patch.object(MainWindow, 'update_brush_button'):
        window = MainWindow(mock_app)
        qtbot.addWidget(window)

        new_color = QColor("blue")
        window.update_dynamic_palette(new_color)

        # Check the first saturation button's color
        h, _, v, a = new_color.getHsv()
        expected_color = QColor.fromHsv(h, 0, v, a)
        assert window.saturation_buttons[0].color == expected_color.name()

        # Check the first value button's color
        h, s, _, a = new_color.getHsv()
        expected_color = QColor.fromHsv(h, s, 0, a)
        assert window.value_buttons[0].color == expected_color.name()
