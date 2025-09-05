from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt
from portal.tools.basetool import BaseTool


class RotateTool(BaseTool):
    """
    A tool for rotating the layer.
    """
    name = "Rotate"
    icon = "icons/toolrotate.png"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)
