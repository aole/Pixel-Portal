import sys
import unittest
from PySide6.QtWidgets import QApplication
from portal.main import MainWindow

class TestPortalApp(unittest.TestCase):
    def test_main_window_creation(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()
        self.assertIsNotNone(window)
        window.close()

if __name__ == '__main__':
    unittest.main()
