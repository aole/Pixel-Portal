import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from portal.main import MainWindow, App

def test_application_startup(qtbot):
    """Test that the main application window is created and shown."""
    with patch.object(sys, 'exit') as mock_exit:
        q_app = QApplication.instance() or QApplication(sys.argv)
        app = App()
        window = MainWindow(app)
        qtbot.addWidget(window)

        window.show()

        assert window.isVisible()
        mock_exit.assert_not_called()
