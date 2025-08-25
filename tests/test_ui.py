import pytest
from PySide6.QtWidgets import QApplication
from portal.ui import MainWindow
from portal.app import App

@pytest.fixture
def app(qtbot):
    q_app = QApplication.instance()
    if q_app is None:
        q_app = QApplication([])

    app_instance = App()
    window = MainWindow(app_instance)
    app_instance.set_window(window)
    qtbot.addWidget(window)
    window.show()
    return window

def test_shape_tool_change(app):
    # Default tool is Line
    assert app.shape_button.defaultAction().text() == "Line"

    # Change to Rectangle
    rect_action = [action for action in app.shape_button.menu().actions() if action.text() == "Rectangle"][0]
    rect_action.trigger()
    assert app.shape_button.defaultAction().text() == "Rectangle"

    # Change to Ellipse
    ellipse_action = [action for action in app.shape_button.menu().actions() if action.text() == "Ellipse"][0]
    ellipse_action.trigger()
    assert app.shape_button.defaultAction().text() == "Ellipse"
