import pytest
from PySide6.QtWidgets import QApplication
import threading

# Try to fix segfaults in the test suite by increasing the stack size
threading.stack_size(134217728)

@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication instance."""
    print("Creating QApplication")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    print("Destroying QApplication")
