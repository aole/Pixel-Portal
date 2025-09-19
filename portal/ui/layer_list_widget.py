from PySide6.QtWidgets import QListWidget, QApplication, QMenu
from PySide6.QtCore import Qt, Signal

class LayerListWidget(QListWidget):
    merge_down_requested = Signal(int)
    merge_down_current_frame_requested = Signal(int)
    select_opaque_requested = Signal(int)
    duplicate_requested = Signal(int)
    remove_background_requested = Signal(int)
    collapse_requested = Signal()

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
        merge_down_current_frame_action = menu.addAction("Merge Down (Current Frame)")
        select_opaque_action = menu.addAction("Select Opaque")
        duplicate_action = menu.addAction("Duplicate")
        remove_bg_action = menu.addAction("Remove Background")
        menu.addSeparator()
        collapse_action = menu.addAction("Collapse Layers")
        collapse_action.setEnabled(self.count() > 1)

        action = menu.exec(self.mapToGlobal(pos))

        if action == merge_down_action:
            self.merge_down_requested.emit(index)
        elif action == merge_down_current_frame_action:
            self.merge_down_current_frame_requested.emit(index)
        elif action == select_opaque_action:
            self.select_opaque_requested.emit(index)
        elif action == duplicate_action:
            self.duplicate_requested.emit(index)
        elif action == remove_bg_action:
            self.remove_background_requested.emit(index)
        elif action == collapse_action:
            self.collapse_requested.emit()

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        ):
            # Ctrl+click selects opaque pixels on the clicked layer without
            # changing which layer is active.
            item = self.itemAt(event.position().toPoint())
            if item:
                self.select_opaque_requested.emit(self.row(item))
            event.accept()
            return

        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            # Ctrl is pressed, so don't start the drag.
            # This is to prevent conflicts with the Ctrl+drag shortcut on the canvas.
            return
        super().startDrag(supportedActions)
