import sys
from PySide6.QtWidgets import QApplication
from portal.ui.ui import MainWindow
from portal.core.app import App
from portal.core.services.document_service import DocumentService
from portal.core.services.clipboard_service import ClipboardService

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    document_service = DocumentService()
    clipboard_service = ClipboardService(document_service)
    app = App(document_service=document_service, clipboard_service=clipboard_service)
    window = MainWindow(app)
    app.main_window = window
    window.show()
    app.undo_stack_changed.emit()
    sys.exit(q_app.exec())
