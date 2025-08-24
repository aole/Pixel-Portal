import pytest
from PySide6.QtGui import QColor
from portal.document import Document

def test_document_render(qtbot):
    """Test the Document.render() method."""
    doc = Document(1, 1)

    # With one transparent layer, image should be transparent
    rendered_image = doc.render()
    assert rendered_image.pixelColor(0, 0).alpha() == 0

    # Draw on the layer and re-render
    red = QColor("red")
    doc.layer_manager.active_layer.image.setPixelColor(0, 0, red)
    rendered_image = doc.render()
    assert rendered_image.pixelColor(0, 0) == red

    # Add a second layer, draw on it, and render
    blue = QColor("blue")
    doc.layer_manager.add_layer("Top Layer")
    doc.layer_manager.active_layer.image.setPixelColor(0, 0, blue)
    rendered_image = doc.render()
    assert rendered_image.pixelColor(0, 0) == blue # Top layer should be on top

    # Hide top layer and render
    doc.layer_manager.toggle_visibility(1)
    rendered_image = doc.render()
    assert rendered_image.pixelColor(0, 0) == red
