from PySide6.QtWidgets import QListWidget, QApplication, QMenu
from PySide6.QtCore import Qt, Signal

class LayerListWidget(QListWidget):
    merge_down_requested = Signal(int)
    select_opaque_requested = Signal(int)
    duplicate_requested = Signal(int)
    remove_background_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        index = self.row(item)
        menu = QMenu()
        merge_down_action = menu.addAction("Merge Down")
        select_opaque_action = menu.addAction("Select Opaque")
        duplicate_action = menu.addAction("Duplicate")
        remove_bg_action = menu.addAction("Remove Background")

        action = menu.exec(self.mapToGlobal(pos))

        if action == merge_down_action:
            self.merge_down_requested.emit(index)
        elif action == select_opaque_action:
            self.select_opaque_requested.emit(index)
        elif action == duplicate_action:
            self.duplicate_requested.emit(index)
        elif action == remove_bg_action:
            self.remove_background_requested.emit(index)

    def startDrag(self, supportedActions):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            # Ctrl is pressed, so don't start the drag.
            # This is to prevent conflicts with the Ctrl+drag shortcut on the canvas.
            return
        super().startDrag(supportedActions)
