from PySide6.QtTest import QSignalSpy

from portal.core.document import Document
from portal.ui.timeline_widget import TimelineWidget


def test_timeline_widget_emits_selection(qapp):
    document = Document(4, 4)
    document.add_frame()

    widget = TimelineWidget()
    widget.set_document(document)

    spy = QSignalSpy(widget.frame_selected)
    widget.frame_list.setCurrentRow(0)
    qapp.processEvents()
    assert spy.count() == 1
    assert spy.at(0)[0] == 0

    spy = QSignalSpy(widget.frame_selected)
    widget.frame_list.setCurrentRow(1)
    qapp.processEvents()
    assert spy.count() == 1
    assert spy.at(0)[0] == 1


def test_timeline_widget_tracks_document_changes(qapp):
    document = Document(2, 2)
    widget = TimelineWidget()
    widget.set_document(document)

    assert widget.frame_list.count() == 1
    assert widget.frame_list.currentRow() == 0
    assert not widget.delete_button.isEnabled()

    document.add_frame()
    assert widget.frame_list.count() == 2
    assert widget.frame_list.currentRow() == 1
    assert widget.delete_button.isEnabled()

    document.select_frame(0)
    assert widget.frame_list.currentRow() == 0

    document.remove_frame(1)
    assert widget.frame_list.count() == 1
    assert widget.frame_list.currentRow() == 0
    assert not widget.delete_button.isEnabled()


def test_timeline_buttons_emit_indices(qapp):
    document = Document(2, 2)
    document.add_frame()

    widget = TimelineWidget()
    widget.set_document(document)
    widget.frame_list.setCurrentRow(1)

    add_spy = QSignalSpy(widget.add_frame_requested)
    delete_spy = QSignalSpy(widget.delete_frame_requested)
    duplicate_spy = QSignalSpy(widget.duplicate_frame_requested)

    widget.add_button.click()
    assert add_spy.count() == 1

    widget.delete_button.click()
    assert delete_spy.count() == 1
    assert delete_spy.at(0)[0] == 1

    widget.duplicate_button.click()
    assert duplicate_spy.count() == 1
    assert duplicate_spy.at(0)[0] == 1
