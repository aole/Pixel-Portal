import pytest
from portal.ui.canvas import Canvas
from portal.core.drawing_context import DrawingContext
from portal.core.document import Document

def test_segfault(qtbot):
    drawing_context = DrawingContext()
    canvas = Canvas(drawing_context)
    qtbot.addWidget(canvas)
    drawing_context.setParent(canvas)
    document = Document(256, 256)
    canvas.set_document(document)
