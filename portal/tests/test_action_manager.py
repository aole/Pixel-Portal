import unittest
from unittest.mock import Mock, MagicMock
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QObject
from portal.action_manager import ActionManager

# Ensure a QApplication instance exists
app = QApplication.instance()
if app is None:
    app = QApplication([])

class MockMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app = MagicMock()
        self.open_new_file_dialog = MagicMock()
        self.open_palette_dialog = MagicMock()
        self.open_resize_dialog = MagicMock()
        self.open_background_color_dialog = MagicMock()
        self.open_ai_dialog = MagicMock()

class TestActionManager(unittest.TestCase):
    def test_setup_actions(self):
        # Create a mock main_window and app
        main_window = MockMainWindow()

        # Create an instance of ActionManager
        action_manager = ActionManager(main_window)

        # Mock the canvas
        canvas = MagicMock()

        # Call the method to be tested
        action_manager.setup_actions(canvas)

        # Verify that all actions are created
        self.assertIsNotNone(action_manager.new_action)
        self.assertIsNotNone(action_manager.open_action)
        self.assertIsNotNone(action_manager.save_action)
        self.assertIsNotNone(action_manager.load_palette_action)
        self.assertIsNotNone(action_manager.exit_action)
        self.assertIsNotNone(action_manager.undo_action)
        self.assertIsNotNone(action_manager.redo_action)
        self.assertIsNotNone(action_manager.paste_as_new_layer_action)
        self.assertIsNotNone(action_manager.clear_action)
        self.assertIsNotNone(action_manager.select_all_action)
        self.assertIsNotNone(action_manager.select_none_action)
        self.assertIsNotNone(action_manager.invert_selection_action)
        self.assertIsNotNone(action_manager.resize_action)
        self.assertIsNotNone(action_manager.crop_action)
        self.assertIsNotNone(action_manager.flip_horizontal_action)
        self.assertIsNotNone(action_manager.flip_vertical_action)
        self.assertIsNotNone(action_manager.checkered_action)
        self.assertIsNotNone(action_manager.white_action)
        self.assertIsNotNone(action_manager.black_action)
        self.assertIsNotNone(action_manager.gray_action)
        self.assertIsNotNone(action_manager.magenta_action)
        self.assertIsNotNone(action_manager.custom_color_action)
        self.assertIsNotNone(action_manager.circular_brush_action)
        self.assertIsNotNone(action_manager.square_brush_action)
        self.assertIsNotNone(action_manager.mirror_x_action)
        self.assertIsNotNone(action_manager.mirror_y_action)
        self.assertIsNotNone(action_manager.grid_action)
        self.assertIsNotNone(action_manager.ai_action)

        # Verify that actions are connected to the correct slots by triggering them
        action_manager.new_action.trigger()
        main_window.open_new_file_dialog.assert_called_once()

        action_manager.open_action.trigger()
        main_window.app.open_document.assert_called_once()

        action_manager.save_action.trigger()
        main_window.app.save_document.assert_called_once()

        action_manager.load_palette_action.trigger()
        main_window.open_palette_dialog.assert_called_once()

        action_manager.exit_action.trigger()
        main_window.app.exit.assert_called_once()

        action_manager.undo_action.trigger()
        main_window.app.undo.assert_called_once()

        action_manager.redo_action.trigger()
        main_window.app.redo.assert_called_once()

        action_manager.paste_as_new_layer_action.trigger()
        main_window.app.paste_as_new_layer.assert_called_once()

        action_manager.clear_action.trigger()
        main_window.app.clear_layer.assert_called_once()

        action_manager.select_all_action.trigger()
        main_window.app.select_all.assert_called_once()

        action_manager.select_none_action.trigger()
        main_window.app.select_none.assert_called_once()

        action_manager.invert_selection_action.trigger()
        main_window.app.invert_selection.assert_called_once()

        action_manager.resize_action.trigger()
        main_window.open_resize_dialog.assert_called_once()

        action_manager.crop_action.setEnabled(True)
        action_manager.crop_action.trigger()
        main_window.app.crop_to_selection.assert_called_once()

        action_manager.flip_horizontal_action.trigger()
        main_window.app.flip_horizontal.assert_called_once()

        action_manager.flip_vertical_action.trigger()
        main_window.app.flip_vertical.assert_called_once()

        action_manager.custom_color_action.trigger()
        main_window.open_background_color_dialog.assert_called_once()

        action_manager.mirror_x_action.trigger()
        main_window.app.set_mirror_x.assert_called_once()

        action_manager.mirror_y_action.trigger()
        main_window.app.set_mirror_y.assert_called_once()

        action_manager.ai_action.trigger()
        main_window.open_ai_dialog.assert_called_once()


if __name__ == '__main__':
    unittest.main()
