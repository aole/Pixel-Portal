from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)

from portal.core.document_controller import BackgroundRemovalScope


class RemoveBackgroundDialog(QDialog):
    """Configure how background removal should be applied to the active layer."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

        self.setWindowTitle("Remove Background")
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        layout = QVBoxLayout(self)
        description = QLabel(
            "Choose whether to remove the background from the current key or all keys.",
            self,
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.button_group = QButtonGroup(self)
        self.all_keys_radio = QRadioButton("All keys", self)
        self.this_key_radio = QRadioButton("This key", self)
        self.button_group.addButton(self.all_keys_radio)
        self.button_group.addButton(self.this_key_radio)
        self.all_keys_radio.setChecked(True)

        layout.addWidget(self.all_keys_radio)
        layout.addWidget(self.this_key_radio)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply,
            parent=self,
        )
        self.button_box.accepted.connect(self._apply_and_close)
        self.button_box.rejected.connect(self.reject)
        apply_button = self.button_box.button(QDialogButtonBox.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self.apply)
        layout.addWidget(self.button_box)

    def current_scope(self) -> BackgroundRemovalScope:
        if self.this_key_radio.isChecked():
            return BackgroundRemovalScope.THIS_KEY
        return BackgroundRemovalScope.ALL_KEYS

    def apply(self):
        scope = self.current_scope()
        if self.app is not None:
            self.app.remove_background_from_layer(scope)

    def _apply_and_close(self):
        self.apply()
        self.accept()
