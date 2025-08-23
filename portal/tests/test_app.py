import sys
import unittest
from PySide6.QtWidgets import QApplication
from portal.ui import MainWindow

class TestPortalApp(unittest.TestCase):
    def test_main_window_creation(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()
        self.assertIsNotNone(window)

        menu_bar = window.menuBar()
        self.assertIsNotNone(menu_bar)

        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "&File":
                file_menu = action.menu()
                break

        self.assertIsNotNone(file_menu)

        exit_action = None
        for action in file_menu.actions():
            if action.text() == "&Exit":
                exit_action = action
                break

        self.assertIsNotNone(exit_action)

        window.close()

if __name__ == '__main__':
    unittest.main()
