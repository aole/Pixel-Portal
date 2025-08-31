import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication instance."""
    print("Creating QApplication")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    print("Destroying QApplication")
