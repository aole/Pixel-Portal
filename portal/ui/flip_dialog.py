from PySide6.QtWidgets import (
    QDialog,
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QRadioButton,
)

from portal.core.command import FlipScope

class FlipDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Flip")

        # Flip Type Checkboxes
        self.flip_type_group = QGroupBox("Flip")
        self.horizontal_checkbox = QCheckBox("Horizontal")
        self.vertical_checkbox = QCheckBox("Vertical")
        self.horizontal_checkbox.setChecked(True)
        flip_type_layout = QVBoxLayout()
        flip_type_layout.addWidget(self.horizontal_checkbox)
        flip_type_layout.addWidget(self.vertical_checkbox)
        self.flip_type_group.setLayout(flip_type_layout)

        # Scope Radio Buttons
        self.scope_group = QGroupBox("Scope")
        self.current_frame_radio = QRadioButton("Current Frame")
        self.current_layer_radio = QRadioButton("Current Layer")
        self.whole_document_radio = QRadioButton("Whole Document")
        self.current_frame_radio.setChecked(True)
        scope_layout = QVBoxLayout()
        scope_layout.addWidget(self.current_frame_radio)
        scope_layout.addWidget(self.current_layer_radio)
        scope_layout.addWidget(self.whole_document_radio)
        self.scope_group.setLayout(scope_layout)

        # OK and Cancel Buttons
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.flip_type_group)
        main_layout.addWidget(self.scope_group)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_values(self):
        if self.whole_document_radio.isChecked():
            scope = FlipScope.DOCUMENT
        elif self.current_frame_radio.isChecked():
            scope = FlipScope.FRAME
        else:
            scope = FlipScope.LAYER

        return {
            "horizontal": self.horizontal_checkbox.isChecked(),
            "vertical": self.vertical_checkbox.isChecked(),
            "scope": scope,
        }
