from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from portal.new_file_dialog import NewFileDialog

def test_new_file_dialog(qtbot):
    """Test that the dialog is created and that the new_document method is called on the app when the dialog is accepted."""
    mock_app = MagicMock()
    dialog = NewFileDialog(mock_app)
    qtbot.addWidget(dialog)

    dialog.width_input.setText("128")
    dialog.height_input.setText("128")
    dialog.accept()

    mock_app.new_document.assert_called_once_with(128, 128)
