from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidgetItem,
    QPushButton, QHBoxLayout, QAbstractItemView
)
from portal.ui.layer_list_widget import LayerListWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from portal.core.app import App
from portal.ui.layer_item_widget import LayerItemWidget


class LayerManagerWidget(QWidget):
    """
    A widget to display and manage the layer stack.
    """
    layer_changed = Signal()  # Emitted when the layer structure changes

    def __init__(self, app: App, canvas):
        super().__init__()
        self.app = app
        self.canvas = canvas

        self.setWindowTitle("Layers")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Layer List
        self.layer_list = LayerListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layer_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.layer_list.model().rowsMoved.connect(self.on_layers_moved)
        self.layer_list.merge_down_requested.connect(self.merge_layer_down)
        self.layer_list.select_opaque_requested.connect(self.select_opaque)
        self.layer_list.duplicate_requested.connect(self.duplicate_layer_from_menu)
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
            self.layer_list.addItem(item)

            item_widget = LayerItemWidget(layer)
            item_widget.visibility_toggled.connect(
                lambda widget=item_widget: self.on_visibility_toggled(widget)
            )
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

    def on_visibility_toggled(self, widget):
        """Handles toggling layer visibility."""
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            if self.layer_list.itemWidget(item) == widget:
                actual_index = len(self.app.document.layer_manager.layers) - 1 - i
                self.app.document.layer_manager.toggle_visibility(actual_index)
                self.layer_changed.emit()
                return

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
            from portal.core.command import ClearLayerCommand
            selection = self.canvas.selection_shape
            command = ClearLayerCommand(active_layer, selection)
            self.app.execute_command(command)

    def add_layer(self):
        """Adds a new layer."""
        from portal.core.command import AddLayerCommand
        num_layers = len(self.app.document.layer_manager.layers)
        command = AddLayerCommand(self.app.document, name=f"Layer {num_layers + 1}")
        self.app.execute_command(command)

    def remove_layer(self):
        """Removes the selected layer."""
        current_row = self.layer_list.currentRow()
        if current_row == -1:
            return
        
        layer_manager = self.app.document.layer_manager
        actual_index = len(layer_manager.layers) - 1 - current_row

        if len(layer_manager.layers) == 1:
            # Last layer. Clear it instead of removing.
            from portal.core.command import ClearLayerCommand
            active_layer = layer_manager.active_layer
            if active_layer:
                selection = self.canvas.selection_shape
                command = ClearLayerCommand(active_layer, selection)
                self.app.execute_command(command)
        else:
            from portal.core.command import RemoveLayerCommand
            command = RemoveLayerCommand(layer_manager, actual_index)
            self.app.execute_command(command)

    def move_layer_up(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        
        from portal.core.command import MoveLayerCommand
        command = MoveLayerCommand(self.app.document.layer_manager, actual_index, actual_index + 1)
        self.app.execute_command(command)

    def move_layer_down(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        
        from portal.core.command import MoveLayerCommand
        command = MoveLayerCommand(self.app.document.layer_manager, actual_index, actual_index - 1)
        self.app.execute_command(command)

    def merge_layer_down(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        from portal.commands.layer_commands import MergeLayerDownCommand
        command = MergeLayerDownCommand(self.app.document.layer_manager, actual_index)
        self.app.execute_command(command)

    def select_opaque(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        layer = self.app.document.layer_manager.layers[actual_index]
        from portal.commands.selection_commands import SelectOpaqueCommand
        command = SelectOpaqueCommand(layer, self.canvas)
        self.app.execute_command(command)

    def duplicate_layer_from_menu(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        from portal.core.command import DuplicateLayerCommand
        command = DuplicateLayerCommand(self.app.document.layer_manager, actual_index)
        self.app.execute_command(command)
