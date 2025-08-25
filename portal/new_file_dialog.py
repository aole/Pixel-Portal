from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PySide6.QtGui import QIntValidator


class NewFileDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("New File")

        self.layout = QVBoxLayout(self)

        # Width and Height
        size_layout = QHBoxLayout()
        self.width_input = QLineEdit("64")
        self.width_input.setValidator(QIntValidator(1, 4096))
        self.height_input = QLineEdit("64")
        self.height_input.setValidator(QIntValidator(1, 4096))
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_input)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_input)
        self.layout.addLayout(size_layout)

        # Standard sizes
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets:"))
        sizes = [16, 32, 64, 128]
        for size in sizes:
            button = QPushButton(f"{size}x{size}")
            button.clicked.connect(lambda checked, s=size: self.set_size(s, s))
            presets_layout.addWidget(button)
        self.layout.addLayout(presets_layout)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(button_layout)

    def set_size(self, width, height):
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))

    def accept(self):
        width = int(self.width_input.text())
        height = int(self.height_input.text())
        self.app.new_document(width, height)
        super().accept()
