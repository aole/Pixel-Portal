import sys
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from portal.ui import MainWindow
from portal.app import App

class TestPortalApp(unittest.TestCase):
    def setUp(self):
        self.q_app = QApplication.instance()
        if self.q_app is None:
            self.q_app = QApplication(sys.argv)

        self.app = App()
        self.window = MainWindow(self.app)
        self.app.set_window(self.window)
        self.canvas = self.window.canvas

    def tearDown(self):
        self.window.close()

    def test_main_window_creation(self):
        self.assertIsNotNone(self.window)

        menu_bar = self.window.menuBar()
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

    def test_draw_and_drag(self):
        # 1. Start with a fresh document
        self.app.new_document(32, 32)

        # 2. Draw with the right mouse button (which should not do anything)
        start_pos = QPoint(10, 10)
        end_pos = QPoint(20, 20)
        QTest.mousePress(self.canvas, Qt.RightButton, Qt.NoModifier, start_pos)
        QTest.mouseMove(self.canvas, end_pos)
        QTest.mouseRelease(self.canvas, Qt.RightButton, Qt.NoModifier, end_pos)

        # 3. Drag with the middle mouse button
        drag_start_pos = QPoint(15, 15)
        drag_end_pos = QPoint(25, 30)
        QTest.mousePress(self.canvas, Qt.MiddleButton, Qt.NoModifier, drag_start_pos)
        QTest.mouseMove(self.canvas, drag_end_pos)
        QTest.mouseRelease(self.canvas, Qt.MiddleButton, Qt.NoModifier, drag_end_pos)

        # 4. Check if the document offset has been updated
        expected_offset_x = drag_end_pos.x() - drag_start_pos.x()
        expected_offset_y = drag_end_pos.y() - drag_start_pos.y()
        self.assertEqual(self.app.document.x_offset, expected_offset_x)
        self.assertEqual(self.app.document.y_offset, expected_offset_y)

if __name__ == '__main__':
    unittest.main()
