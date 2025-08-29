import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from portal.app import App
from portal.layer_manager_widget import LayerManagerWidget

@pytest.fixture
def app_with_widget(qtbot):
    """Pytest fixture to create an App and a LayerManagerWidget."""
    app = App()
    widget = LayerManagerWidget(app)
    qtbot.addWidget(widget)
    return app, widget

def test_widget_creation(app_with_widget):
    """Test that the LayerManagerWidget can be created."""
    app, widget = app_with_widget
    assert widget is not None
    assert widget.app == app

def test_refresh_layers(app_with_widget):
    """Test that the layer list refreshes correctly."""
    app, widget = app_with_widget

    # Initial state
    assert widget.layer_list.count() == 1
    item_widget = widget.layer_list.itemWidget(widget.layer_list.item(0))
    assert item_widget.label.text() == "Background"

    # Add a layer and refresh
    app.document.layer_manager.add_layer("New Layer")
    widget.refresh_layers()
    assert widget.layer_list.count() == 2

    item_widget_0 = widget.layer_list.itemWidget(widget.layer_list.item(0))
    assert item_widget_0.label.text() == "New Layer" # List is reversed

    item_widget_1 = widget.layer_list.itemWidget(widget.layer_list.item(1))
    assert item_widget_1.label.text() == "Background"

def test_add_layer_button(app_with_widget, qtbot):
    """Test the 'Add Layer' button functionality."""
    app, widget = app_with_widget
    initial_count = len(app.document.layer_manager.layers)

    # In the test setup, there's no MainWindow, so the app.window is not set.
    # We need to manually connect the signal to the refresh method for this test.
    app.document.layer_manager.layer_structure_changed.connect(widget.refresh_layers)

    with qtbot.waitSignal(app.document.layer_manager.layer_structure_changed, timeout=1000):
        widget.add_button.click()

    assert len(app.document.layer_manager.layers) == initial_count + 1
    assert widget.layer_list.count() == initial_count + 1
    assert app.document.layer_manager.active_layer.name.startswith("Layer")

def test_remove_layer_button(app_with_widget):
    """Test the 'Remove Layer' button functionality."""
    app, widget = app_with_widget
    app.document.layer_manager.add_layer("To Be Removed")
    widget.refresh_layers()

    initial_count = len(app.document.layer_manager.layers)
    widget.layer_list.setCurrentRow(0) # Select "To Be Removed"
    widget.remove_button.click()

    assert len(app.document.layer_manager.layers) == initial_count - 1
    assert widget.layer_list.count() == initial_count - 1


def test_rename_layer(app_with_widget, qtbot):
    """Test that a layer can be renamed through the UI."""
    app, widget = app_with_widget

    item_widget = widget.layer_list.itemWidget(widget.layer_list.item(0))
    editable_label = item_widget.label  # This is the EditableLabel

    # Simulate double-click on the internal NameLabel
    qtbot.mouseDClick(editable_label.label, Qt.MouseButton.LeftButton)

    # Check that we are in edit mode
    assert editable_label.stack.currentWidget() == editable_label.edit

    # Change the text
    editable_label.edit.setText("New Name")

    # Simulate finishing editing
    editable_label.edit.editingFinished.emit()

    # Check that the layer name is updated
    assert app.document.layer_manager.layers[0].name == "New Name"
    assert editable_label.text() == "New Name"
