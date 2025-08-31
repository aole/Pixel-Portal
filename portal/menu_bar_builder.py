from PySide6.QtWidgets import QMainWindow
from .action_manager import ActionManager


class MenuBarBuilder:
    def __init__(self, window: QMainWindow, action_manager: ActionManager):
        self.window = window
        self.action_manager = action_manager

    def setup_menus(self):
        menu_bar = self.window.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_manager.new_action)
        file_menu.addAction(self.action_manager.open_action)
        file_menu.addAction(self.action_manager.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action_manager.load_palette_action)
        file_menu.addAction(self.action_manager.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_manager.undo_action)
        edit_menu.addAction(self.action_manager.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.paste_as_new_layer_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.clear_action)

        select_menu = menu_bar.addMenu("&Select")
        select_menu.addAction(self.action_manager.select_all_action)
        select_menu.addAction(self.action_manager.select_none_action)
        select_menu.addAction(self.action_manager.invert_selection_action)

        image_menu = menu_bar.addMenu("&Image")
        image_menu.addAction(self.action_manager.resize_action)
        image_menu.addAction(self.action_manager.crop_action)
        image_menu.addSeparator()
        image_menu.addAction(self.action_manager.flip_horizontal_action)
        image_menu.addAction(self.action_manager.flip_vertical_action)

        view_menu = menu_bar.addMenu("&View")
        background_menu = view_menu.addMenu("&Background")
        background_menu.addAction(self.action_manager.checkered_action)
        background_menu.addSeparator()
        background_menu.addAction(self.action_manager.white_action)
        background_menu.addAction(self.action_manager.black_action)
        background_menu.addAction(self.action_manager.gray_action)
        background_menu.addAction(self.action_manager.magenta_action)
        background_menu.addSeparator()
        background_menu.addAction(self.action_manager.custom_color_action)

        view_menu.addSeparator()
        view_menu.addAction(self.action_manager.ai_action)
