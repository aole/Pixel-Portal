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
        self.layer_list.remove_background_requested.connect(self.remove_background_from_menu)
        self.layer_list.collapse_requested.connect(self.collapse_layers_from_menu)
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

        self._updating_layers = False

        self.refresh_layers()

    def refresh_layers(self):
        """Refreshes the layer list from the document's layer manager."""
        self._updating_layers = True
        self.layer_list.blockSignals(True)
        try:
            self.layer_list.clear()
            for layer in reversed(self.app.document.layer_manager.layers):
                item = QListWidgetItem()
                self.layer_list.addItem(item)

                item_widget = LayerItemWidget(layer)
                item_widget.visibility_toggled.connect(
                    lambda widget=item_widget: self.on_visibility_toggled(widget)
                )
                item_widget.opacity_preview_changed.connect(
                    lambda value, widget=item_widget: self.on_opacity_preview_changed(widget, value)
                )
                item_widget.opacity_changed.connect(
                    lambda old, new, widget=item_widget: self.on_opacity_changed(widget, old, new)
                )
                item.setSizeHint(item_widget.sizeHint())
                self.layer_list.setItemWidget(item, item_widget)

            if self.app.document.layer_manager.active_layer:
                active_index = (
                    len(self.app.document.layer_manager.layers)
                    - 1
                    - self.app.document.layer_manager.active_layer_index
                )
                self.layer_list.setCurrentRow(active_index)
        finally:
            self.layer_list.blockSignals(False)
            self._updating_layers = False

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

    def on_opacity_preview_changed(self, widget, value):
        """Preview layer opacity while dragging."""
        widget.layer.opacity = value / 100.0
        self.layer_changed.emit()

    def on_opacity_changed(self, widget, old_value, new_value):
        """Commit an undoable change to layer opacity."""
        # Restore old value so the command captures it correctly
        widget.layer.opacity = old_value / 100.0
        from portal.core.command import SetLayerOpacityCommand
        command = SetLayerOpacityCommand(widget.layer, new_value / 100.0)
        self.app.execute_command(command)
        self.layer_changed.emit()

    def on_layers_moved(self, _parent, start, end, _destination, row):
        """Handles reordering layers via drag-and-drop."""
        if self._updating_layers:
            return

        move_count = end - start + 1
        if move_count != 1:
            # QListWidget is configured for single selection, but guard just in case.
            self.refresh_layers()
            return

        final_row = row
        if row > start:
            final_row -= move_count

        total_rows = self.layer_list.count()
        if total_rows == 0:
            return

        final_row = max(0, min(final_row, total_rows - move_count))

        if final_row == start:
            # No effective change.
            return

        document = self.app.document
        layer_manager = document.layer_manager
        total_layers = len(layer_manager.layers)

        from_index = total_layers - 1 - start
        to_index = total_layers - 1 - final_row

        if from_index == to_index:
            return

        from portal.core.command import MoveLayerCommand

        command = MoveLayerCommand(document, from_index, to_index)
        self.app.execute_command(command)

        # Ensure the canvas reflects the new layer order immediately.
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
            command = RemoveLayerCommand(self.app.document, actual_index)
            self.app.execute_command(command)

    def move_layer_up(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        
        from portal.core.command import MoveLayerCommand
        command = MoveLayerCommand(self.app.document, actual_index, actual_index + 1)
        self.app.execute_command(command)

    def move_layer_down(self):
        current_row = self.layer_list.currentRow()
        if current_row == -1: return
        actual_index = len(self.app.document.layer_manager.layers) - 1 - current_row
        
        from portal.core.command import MoveLayerCommand
        command = MoveLayerCommand(self.app.document, actual_index, actual_index - 1)
        self.app.execute_command(command)

    def merge_layer_down(self, index_in_list):
        document = self.app.document
        if document is None:
            return
        actual_index = len(document.layer_manager.layers) - 1 - index_in_list
        from portal.commands.layer_commands import MergeLayerDownCommand
        command = MergeLayerDownCommand(document, actual_index)
        self.app.execute_command(command)

    def select_opaque(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        layer = self.app.document.layer_manager.layers[actual_index]
        self.app.select_opaque_for_layer(layer)

    def duplicate_layer_from_menu(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        from portal.core.command import DuplicateLayerCommand
        command = DuplicateLayerCommand(self.app.document, actual_index)
        self.app.execute_command(command)

    def remove_background_from_menu(self, index_in_list):
        actual_index = len(self.app.document.layer_manager.layers) - 1 - index_in_list
        self.app.document.layer_manager.select_layer(actual_index)
        main_window = getattr(self.app, "main_window", None)
        if main_window is not None:
            main_window.open_remove_background_dialog()

    def collapse_layers_from_menu(self):
        document = self.app.document
        if document is None:
            return
        from portal.commands.layer_commands import CollapseLayersCommand
        command = CollapseLayersCommand(document)
        self.app.execute_command(command)
