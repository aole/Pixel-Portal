import os
import functools
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow
from portal.commands.action_manager import ActionManager


class MenuBarBuilder:
    def __init__(self, window: QMainWindow, action_manager: ActionManager):
        self.window = window
        self.action_manager = action_manager
        self.panels_menu = None
        self.toolbars_menu = None

    def set_panels(self, layer_manager_dock, preview_dock, ai_panel_dock):
        self.panels_menu.addAction(layer_manager_dock.toggleViewAction())
        self.panels_menu.addAction(preview_dock.toggleViewAction())
        self.panels_menu.addAction(ai_panel_dock.toggleViewAction())

    def set_toolbars(self, toolbars):
        for toolbar in toolbars:
            self.toolbars_menu.addAction(toolbar.toggleViewAction())

    def setup_menus(self):
        menu_bar = self.window.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_manager.new_action)
        file_menu.addAction(self.action_manager.open_action)
        file_menu.addAction(self.action_manager.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action_manager.load_palette_action)
        file_menu.addAction(self.action_manager.save_palette_as_png_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action_manager.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_manager.undo_action)
        edit_menu.addAction(self.action_manager.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.cut_action)
        edit_menu.addAction(self.action_manager.copy_action)
        edit_menu.addAction(self.action_manager.paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.paste_as_new_image_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.flip_action)
        edit_menu.addSeparator()

        select_menu = menu_bar.addMenu("&Select")
        select_menu.addAction(self.action_manager.select_all_action)
        select_menu.addAction(self.action_manager.select_none_action)
        select_menu.addAction(self.action_manager.invert_selection_action)

        image_menu = menu_bar.addMenu("&Image")
        image_menu.addAction(self.action_manager.resize_action)
        image_menu.addAction(self.action_manager.crop_action)

        layer_menu = menu_bar.addMenu("&Layer")
        layer_menu.addAction(self.action_manager.conform_to_palette_action)
        layer_menu.addAction(self.action_manager.remove_background_action)

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
        background_menu.addAction(self.action_manager.image_background_action)

        view_menu.addSeparator()
        view_menu.addAction(self.action_manager.tile_preview_action)

        windows_menu = menu_bar.addMenu("&Windows")
        self.panels_menu = windows_menu.addMenu("&Panels")
        self.toolbars_menu = windows_menu.addMenu("&Toolbars")

        scripting_menu = menu_bar.addMenu("&Scripting")
        self.populate_scripting_menu(scripting_menu)

    def populate_scripting_menu(self, scripting_menu):
        scripts_dir = 'scripts'
        if not os.path.exists(scripts_dir):
            return

        for filename in os.listdir(scripts_dir):
            if filename.endswith('.py'):
                script_path = os.path.join(scripts_dir, filename)
                action_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                action = QAction(action_name, self.window)
                action.triggered.connect(functools.partial(self.window.app.run_script, script_path))
                scripting_menu.addAction(action)
