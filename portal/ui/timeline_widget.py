"""Timeline widget for navigating and managing document frames."""

from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QListView,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:  # pragma: no cover - import only used for type hints
    from portal.core.document import Document


class TimelineWidget(QWidget):
    """Display document frames horizontally with management controls."""

    frame_selected = Signal(int)
    add_frame_requested = Signal()
    delete_frame_requested = Signal(int)
    duplicate_frame_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._document: Optional["Document"] = None
        self._unsubscribe: Optional[Callable[[], None]] = None

        self.frame_list = QListWidget(self)
        self.frame_list.setFlow(QListView.LeftToRight)
        self.frame_list.setWrapping(False)
        self.frame_list.setSpacing(6)
        self.frame_list.setUniformItemSizes(True)
        self.frame_list.setSelectionMode(QListWidget.SingleSelection)
        self.frame_list.currentRowChanged.connect(self._on_frame_selected)

        self.add_button = QPushButton("Add", self)
        self.add_button.setToolTip("Create a new blank frame")
        self.add_button.clicked.connect(self.add_frame_requested.emit)

        self.delete_button = QPushButton("Delete", self)
        self.delete_button.setToolTip("Remove the selected frame")
        self.delete_button.clicked.connect(self._emit_delete_request)

        self.duplicate_button = QPushButton("Duplicate", self)
        self.duplicate_button.setToolTip("Duplicate the selected frame")
        self.duplicate_button.clicked.connect(self._emit_duplicate_request)

        button_bar = QHBoxLayout()
        button_bar.setContentsMargins(0, 0, 0, 0)
        button_bar.setSpacing(6)
        button_bar.addWidget(self.add_button)
        button_bar.addWidget(self.delete_button)
        button_bar.addWidget(self.duplicate_button)
        button_bar.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addLayout(button_bar)
        layout.addWidget(self.frame_list)

        self._update_button_state()

    def set_document(self, document: Optional["Document"]) -> None:
        """Bind the widget to ``document`` and refresh the list."""

        if document is self._document:
            self.refresh()
            return

        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

        self._document = document
        self.refresh()

        if document is not None:
            self._unsubscribe = document.add_layer_manager_listener(
                self._on_layer_manager_changed, invoke_immediately=False
            )

    def refresh(self) -> None:
        """Refresh the frame list based on the current document state."""

        if self._document is None:
            self.frame_list.clear()
            self._update_button_state()
            return

        frame_manager = self._document.frame_manager
        frame_count = len(frame_manager.frames)

        if self.frame_list.count() != frame_count:
            self.frame_list.clear()
            for index in range(frame_count):
                self.frame_list.addItem(f"Frame {index + 1}")
        else:
            for index in range(frame_count):
                item = self.frame_list.item(index)
                if item is not None:
                    item.setText(f"Frame {index + 1}")

        active_index = frame_manager.active_frame_index
        with QSignalBlocker(self.frame_list):
            if 0 <= active_index < self.frame_list.count():
                self.frame_list.setCurrentRow(active_index)
            else:
                self.frame_list.clearSelection()

        self._update_button_state()

    def _on_layer_manager_changed(self, _layer_manager) -> None:
        self.refresh()

    def _on_frame_selected(self, row: int) -> None:
        if row < 0:
            self._update_button_state()
            return
        self._update_button_state()
        self.frame_selected.emit(row)

    def _emit_delete_request(self) -> None:
        row = self.frame_list.currentRow()
        if row >= 0:
            self.delete_frame_requested.emit(row)

    def _emit_duplicate_request(self) -> None:
        row = self.frame_list.currentRow()
        if row >= 0:
            self.duplicate_frame_requested.emit(row)

    def _update_button_state(self) -> None:
        document = self._document
        has_document = document is not None
        frame_count = len(document.frame_manager.frames) if document else 0
        current_row = self.frame_list.currentRow()
        has_selection = current_row >= 0

        self.add_button.setEnabled(has_document)
        self.delete_button.setEnabled(has_document and frame_count > 1 and has_selection)
        self.duplicate_button.setEnabled(has_document and has_selection)

    def closeEvent(self, event) -> None:  # pragma: no cover - Qt lifecycle
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        super().closeEvent(event)
