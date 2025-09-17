from portal.core.command import Command
from PySide6.QtGui import QPainterPath, QImage, qAlpha


def clone_selection_path(path: QPainterPath | None) -> QPainterPath | None:
    if path is None:
        return None
    return QPainterPath(path)


def selection_paths_equal(
    first: QPainterPath | None, second: QPainterPath | None
) -> bool:
    if first is None or second is None:
        return first is None and second is None
    return first == second


class SelectionChangeCommand(Command):
    def __init__(
        self,
        canvas,
        previous_selection: QPainterPath | None,
        new_selection: QPainterPath | None,
    ) -> None:
        self.canvas = canvas
        self.previous_selection = clone_selection_path(previous_selection)
        self.new_selection = clone_selection_path(new_selection)

    def execute(self) -> None:
        self.canvas._update_selection_and_emit_size(
            clone_selection_path(self.new_selection)
        )

    def undo(self) -> None:
        self.canvas._update_selection_and_emit_size(
            clone_selection_path(self.previous_selection)
        )


class SelectOpaqueCommand(Command):
    def __init__(self, layer, canvas) -> None:
        self.layer = layer
        self.canvas = canvas
        self.previous_selection = clone_selection_path(self.canvas.selection_shape)

    def execute(self) -> None:
        path = QPainterPath()
        image = self.layer.image
        image = image.convertToFormat(QImage.Format_ARGB32)

        for y in range(image.height()):
            for x in range(image.width()):
                if qAlpha(image.pixel(x, y)) > 0:
                    path.addRect(x, y, 1, 1)

        self.canvas._update_selection_and_emit_size(path.simplified())

    def undo(self) -> None:
        self.canvas._update_selection_and_emit_size(
            clone_selection_path(self.previous_selection)
        )
