import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from PySide6.QtWidgets import QApplication
import sys
import threading

# It's good practice to keep this, as it can help with stack-related issues.
threading.stack_size(134217728)


@pytest.fixture
def qapp():
    """
    Creates a new QApplication for each test function, ensuring a clean environment.
    """
    # Use sys.argv to avoid issues on some platforms.
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    app.quit()
    