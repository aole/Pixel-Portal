import pytest
from unittest.mock import Mock, MagicMock
from PySide6.QtWidgets import QApplication, QMainWindow
from portal.action_manager import ActionManager

@pytest.fixture
def mock_main_window(qapp):
    window = QMainWindow()
    window.app = MagicMock()
    window.open_new_file_dialog = MagicMock()
    window.open_palette_dialog = MagicMock()
    window.open_resize_dialog = MagicMock()
    window.open_background_color_dialog = MagicMock()
    window.toggle_ai_panel = MagicMock()
    return window

def test_setup_actions(mock_main_window):
    # Create an instance of ActionManager
    action_manager = ActionManager(mock_main_window)

    # Mock the canvas
    canvas = MagicMock()

    # Call the method to be tested
    action_manager.setup_actions(canvas)

    # Verify that all actions are created
    assert action_manager.new_action is not None
    assert action_manager.open_action is not None
    assert action_manager.save_action is not None
    assert action_manager.load_palette_action is not None
    assert action_manager.exit_action is not None
    assert action_manager.undo_action is not None
    assert action_manager.redo_action is not None
    assert action_manager.paste_as_new_layer_action is not None
    assert action_manager.clear_action is not None
    assert action_manager.select_all_action is not None
    assert action_manager.select_none_action is not None
    assert action_manager.invert_selection_action is not None
    assert action_manager.resize_action is not None
    assert action_manager.crop_action is not None
    assert action_manager.flip_horizontal_action is not None
    assert action_manager.flip_vertical_action is not None
    assert action_manager.checkered_action is not None
    assert action_manager.white_action is not None
    assert action_manager.black_action is not None
    assert action_manager.gray_action is not None
    assert action_manager.magenta_action is not None
    assert action_manager.custom_color_action is not None
    assert action_manager.circular_brush_action is not None
    assert action_manager.square_brush_action is not None
    assert action_manager.mirror_x_action is not None
    assert action_manager.mirror_y_action is not None
    assert action_manager.grid_action is not None
    assert action_manager.ai_action is not None

    # Verify that actions are connected to the correct slots by triggering them
    action_manager.new_action.trigger()
    mock_main_window.open_new_file_dialog.assert_called_once()

    action_manager.open_action.trigger()
    mock_main_window.app.open_document.assert_called_once()

    action_manager.save_action.trigger()
    mock_main_window.app.save_document.assert_called_once()

    action_manager.load_palette_action.trigger()
    mock_main_window.open_palette_dialog.assert_called_once()

    action_manager.exit_action.trigger()
    mock_main_window.app.exit.assert_called_once()

    action_manager.undo_action.trigger()
    mock_main_window.app.undo.assert_called_once()

    action_manager.redo_action.trigger()
    mock_main_window.app.redo.assert_called_once()

    action_manager.paste_as_new_layer_action.trigger()
    mock_main_window.app.paste_as_new_layer.assert_called_once()

    action_manager.clear_action.trigger()
    mock_main_window.app.clear_layer.assert_called_once()

    action_manager.select_all_action.trigger()
    mock_main_window.app.select_all.assert_called_once()

    action_manager.select_none_action.trigger()
    mock_main_window.app.select_none.assert_called_once()

    action_manager.invert_selection_action.trigger()
    mock_main_window.app.invert_selection.assert_called_once()

    action_manager.resize_action.trigger()
    mock_main_window.open_resize_dialog.assert_called_once()

    action_manager.crop_action.setEnabled(True)
    action_manager.crop_action.trigger()
    mock_main_window.app.crop_to_selection.assert_called_once()

    action_manager.flip_horizontal_action.trigger()
    mock_main_window.app.flip_horizontal.assert_called_once()

    action_manager.flip_vertical_action.trigger()
    mock_main_window.app.flip_vertical.assert_called_once()

    action_manager.custom_color_action.trigger()
    mock_main_window.open_background_color_dialog.assert_called_once()

    action_manager.mirror_x_action.trigger()
    mock_main_window.app.set_mirror_x.assert_called_once()

    action_manager.mirror_y_action.trigger()
    mock_main_window.app.set_mirror_y.assert_called_once()

    action_manager.ai_action.trigger()
    mock_main_window.toggle_ai_panel.assert_called_once()
