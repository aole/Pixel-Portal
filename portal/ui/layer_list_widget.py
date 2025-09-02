from PySide6.QtWidgets import QListWidget, QApplication
from PySide6.QtCore import Qt

class LayerListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def startDrag(self, supportedActions):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            # Ctrl is pressed, so don't start the drag.
            # This is to prevent conflicts with the Ctrl+drag shortcut on the canvas.
            return
        super().startDrag(supportedActions)
