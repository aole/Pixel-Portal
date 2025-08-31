from unittest.mock import MagicMock
from PySide6.QtGui import QImage, QPixmap
from portal.preview_panel import PreviewPanel

def test_update_preview(qtbot):
    """Test that the preview is updated with a scaled version of the rendered document."""
    mock_app = MagicMock()
    mock_document = MagicMock()
    mock_app.document = mock_document

    # Create a 200x200 image, which should be scaled down to 128x128
    image = QImage(200, 200, QImage.Format_RGB32)
    mock_document.render.return_value = image

    panel = PreviewPanel(mock_app)
    qtbot.addWidget(panel)

    # The constructor calls update_preview, so reset the mock before calling it again.
    mock_document.render.reset_mock()

    panel.update_preview()

    mock_document.render.assert_called_once()
    pixmap = panel.preview_label.pixmap()
    assert not pixmap.isNull()
    assert pixmap.width() == 128
    assert pixmap.height() == 128
