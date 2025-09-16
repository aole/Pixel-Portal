from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor

from portal.core.command import DrawCommand
from portal.core.document import Document


def test_drawing_is_isolated_between_frames():
    document = Document(3, 3)

    first_manager = document.frame_manager.active_layer_manager
    assert first_manager is not None

    first_layer = first_manager.active_layer
    assert first_layer is not None
    first_layer.image.fill(QColor(0, 0, 0, 0))

    draw_red = DrawCommand(
        layer=first_layer,
        points=[QPoint(0, 0)],
        color=QColor("red"),
        width=1,
        brush_type="Square",
        document=document,
        selection_shape=None,
    )
    draw_red.execute()

    assert first_layer.image.pixelColor(0, 0) == QColor("red")
    assert first_layer.image.pixelColor(1, 1).alpha() == 0

    document.add_frame()

    second_manager = document.frame_manager.active_layer_manager
    assert second_manager is not None

    second_layer = second_manager.active_layer
    assert second_layer is not None
    second_layer.image.fill(QColor(0, 0, 0, 0))

    draw_blue = DrawCommand(
        layer=second_layer,
        points=[QPoint(1, 1)],
        color=QColor("blue"),
        width=1,
        brush_type="Square",
        document=document,
        selection_shape=None,
    )
    draw_blue.execute()

    assert second_layer.image.pixelColor(1, 1) == QColor("blue")
    assert second_layer.image.pixelColor(0, 0).alpha() == 0

    document.select_frame(0)
    first_layer_again = document.frame_manager.active_layer_manager.active_layer
    assert first_layer_again.image.pixelColor(0, 0) == QColor("red")
    assert first_layer_again.image.pixelColor(1, 1).alpha() == 0

    document.select_frame(1)
    second_layer_again = document.frame_manager.active_layer_manager.active_layer
    assert second_layer_again.image.pixelColor(1, 1) == QColor("blue")
    assert second_layer_again.image.pixelColor(0, 0).alpha() == 0
