from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from .app import App
from .layer_item_widget import LayerItemWidget


class LayerManagerWidget(QWidget):
    """
    A widget to display and manage the layer stack.
    """
    layer_changed = Signal()  # Emitted when the layer structure changes

    def __init__(self, app: App):
        super().__init__()
        self.app = app

        self.setWindowTitle("Layers")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Layer List
        self.layer_list = QListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layer_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.layer_list.itemChanged.connect(self.on_visibility_changed)
        self.layer_list.model().rowsMoved.connect(self.on_layers_moved)
        self.layout.addWidget(self.layer_list)

        # Toolbar
        self.toolbar = QHBoxLayout()
        self.layout.addLayout(self.toolbar)

        self.add_button = QPushButton(QIcon("icons/layernew.png"), "")
        self.add_button.clicked.connect(self.add_layer)
        self.toolbar.addWidget(self.add_button)

        self.remove_button = QPushButton(QIcon("icons/layerdelete.png"), "")
        self.remove_button.clicked.connect(self.remove_layer)
        self.toolbar.addWidget(self.remove_button)

        self.duplicate_button = QPushButton(QIcon("icons/layerduplicate.png"), "")
        self.duplicate_button.clicked.connect(self.duplicate_layer)
        self.toolbar.addWidget(self.duplicate_button)

        self.clear_button = QPushButton(QIcon("icons/layerclear.png"), "")
        self.clear_button.clicked.connect(self.clear_layer)
        self.toolbar.addWidget(self.clear_button)

        self.move_up_button = QPushButton(QIcon("icons/layerup.png"), "")
        self.move_up_button.clicked.connect(self.move_layer_up)
        self.toolbar.addWidget(self.move_up_button)

        self.move_down_button = QPushButton(QIcon("icons/layerdown.png"), "") # Placeholder icon
        self.move_down_button.clicked.connect(self.move_layer_down)
        self.toolbar.addWidget(self.move_down_button)

        self.refresh_layers()

    def refresh_layers(self):
        """Refreshes the layer list from the document's layer manager."""
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in reversed(self.app.document.layer_manager.layers):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
            self.layer_list.addItem(item)

            item_widget = LayerItemWidget(layer)
            item.setSizeHint(item_widget.sizeHint())
            self.layer_list.setItemWidget(item, item_widget)

        if self.app.document.layer_manager.active_layer:
            active_index = len(self.app.document.layer_manager.layers) - 1 - self.app.document.layer_manager.active_layer_index
            self.layer_list.setCurrentRow(active_index)
        self.layer_list.blockSignals(False)

    def on_selection_changed(self):
        """Handles changing the active layer."""
        selected_items = self.layer_list.selectedItems()
        if not selected_items:
            return

        # QListWidget is populated in reverse order
        index_in_list = self.layer_list.row(selected_items[0])
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        self.app.document.layer_manager.select_layer(actual_index)
        self.layer_changed.emit()

    def on_visibility_changed(self, item: QListWidgetItem):
        """Handles toggling layer visibility."""
        index_in_list = self.layer_list.row(item)
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list

        is_visible = item.checkState() == Qt.Checked
        if self.app.document.layer_manager.layers[actual_index].visible != is_visible:
            self.app.document.layer_manager.toggle_visibility(actual_index)
            self.layer_changed.emit()

    def on_layers_moved(self, parent, start, end, destination, row):
        """Handles reordering layers via drag-and-drop."""
        # This is complex to map back to the LayerManager.
        # For now, we will use buttons for moving layers.
        # A more robust implementation would handle this.
        self.refresh_layers() # Simple refresh for now
        self.layer_changed.emit()

    def clear_layer(self):
        """Clears the active layer."""
        active_layer = self.app.document.layer_manager.active_layer
        if active_layer:
            active_layer.clear()
            self.app.add_undo_state()
            self.layer_changed.emit()

    def add_layer(self):
        """Adds a new layer."""
        num_layers = len(self.app.document.layer_manager.layers)
        self.app.document.layer_manager.add_layer(f"Layer {num_layers + 1}")
        self.app.add_undo_state()
        self.refresh_layers()
        self.layer_changed.emit()

    def remove_layer(self):
        """Removes the selected layer."""
        current_row = self.layer_list.currentRow()
        if current_row == -1:
            return

        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        try:
            self.app.document.layer_manager.remove_layer(actual_index)
            self.refresh_layers()
            self.layer_changed.emit()
        except (ValueError, IndexError) as e:
            print(f"Error removing layer: {e}") # Replace with proper logging/statusbar message

    def duplicate_layer(self):
        """Duplicates the selected layer."""
        current_row = self.layer_list.currentRow()
        if current_row == -1:
            return

        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        self.app.document.layer_manager.duplicate_layer(actual_index)
        self.app.add_undo_state()
        self.refresh_layers()
        self.layer_changed.emit()

    def move_layer_up(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        if actual_index < len(self.app.document.layer_manager.layers) - 1:
            self.app.document.layer_manager.move_layer_up(actual_index)
            self.refresh_layers()
            self.layer_changed.emit()

    def move_layer_down(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        if actual_index > 0:
            self.app.document.layer_manager.move_layer_down(actual_index)
            self.refresh_layers()
            self.layer_changed.emit()
