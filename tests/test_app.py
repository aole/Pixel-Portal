import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from portal.ui import MainWindow
from portal.app import App


@pytest.fixture
def app(qtbot):
    q_app = QApplication.instance()
    if q_app is None:
        q_app = QApplication(sys.argv)

    app = App()
    window = MainWindow(app)
    app.set_window(window)
    qtbot.addWidget(window)
    window.show()
    yield app
    window.close()


def test_main_window_creation(app):
    assert app.window is not None

    menu_bar = app.window.menuBar()
    assert menu_bar is not None

    file_menu = None
    for action in menu_bar.actions():
        if action.text() == "&File":
            file_menu = action.menu()
            break
    assert file_menu is not None

    exit_action = None
    for action in file_menu.actions():
        if action.text() == "&Exit":
            exit_action = action
            break
    assert exit_action is not None


def test_draw_and_drag(app):
    # 1. Start with a fresh document
    app.new_document(32, 32)
    canvas = app.window.canvas

    # 2. Draw with the right mouse button (which should not do anything)
    start_pos = QPoint(10, 10)
    end_pos = QPoint(20, 20)
    QTest.mousePress(canvas, Qt.RightButton, Qt.NoModifier, start_pos)
    QTest.mouseMove(canvas, end_pos)
    QTest.mouseRelease(canvas, Qt.RightButton, Qt.NoModifier, end_pos)

    # 3. Drag with the middle mouse button
    drag_start_pos = QPoint(15, 15)
    drag_end_pos = QPoint(25, 30)
    QTest.mousePress(canvas, Qt.MiddleButton, Qt.NoModifier, drag_start_pos)
    QTest.mouseMove(canvas, drag_end_pos)
    QTest.mouseRelease(canvas, Qt.MiddleButton, Qt.NoModifier, drag_end_pos)

    # 4. Check if the document offset has been updated
    expected_offset_x = drag_end_pos.x() - drag_start_pos.x()
    expected_offset_y = drag_end_pos.y() - drag_start_pos.y()
    assert canvas.x_offset == expected_offset_x
    assert canvas.y_offset == expected_offset_y

def test_selection_menu(app):
    # 1. Start with a fresh document
    app.new_document(32, 32)

    # 2. Find the selection menu and its actions
    menu_bar = app.window.menuBar()
    select_menu = None
    for action in menu_bar.actions():
        if action.text() == "&Select":
            select_menu = action.menu()
            break
    assert select_menu is not None

    select_all_action = None
    select_none_action = None
    invert_selection_action = None
    for action in select_menu.actions():
        if action.text() == "Select &All":
            select_all_action = action
        elif action.text() == "Select &None":
            select_none_action = action
        elif action.text() == "&Invert Selection":
            invert_selection_action = action
    assert select_all_action is not None
    assert select_none_action is not None
    assert invert_selection_action is not None

    # 3. Test "Select All"
    select_all_action.trigger()
    assert not app.document.selection.isEmpty()
    assert app.document.selection.controlPointRect().width() == 32
    assert app.document.selection.controlPointRect().height() == 32

    # 4. Test "Select None"
    select_none_action.trigger()
    assert app.document.selection.isEmpty()

    # 5. Test "Invert Selection"
    invert_selection_action.trigger()
    assert not app.document.selection.isEmpty()
    assert app.document.selection.controlPointRect().width() == 32
    assert app.document.selection.controlPointRect().height() == 32
