from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout

class ResizeDialog(QDialog):
    def __init__(self, parent=None, width=0, height=0):
        super().__init__(parent)
        self.setWindowTitle("Resize Document")

        self.width_label = QLabel("Width:")
        self.width_input = QLineEdit(str(width))
        self.height_label = QLabel("Height:")
        self.height_input = QLineEdit(str(height))
        self.interpolation_label = QLabel("Interpolation:")
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(["Nearest Neighbor", "Smooth"])

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(self.width_label)
        h_layout1.addWidget(self.width_input)
        layout.addLayout(h_layout1)

        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(self.height_label)
        h_layout2.addWidget(self.height_input)
        layout.addLayout(h_layout2)

        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(self.interpolation_label)
        h_layout3.addWidget(self.interpolation_combo)
        layout.addLayout(h_layout3)

        h_layout4 = QHBoxLayout()
        h_layout4.addWidget(self.ok_button)
        h_layout4.addWidget(self.cancel_button)
        layout.addLayout(h_layout4)

        self.setLayout(layout)

    def get_values(self):
        return {
            "width": int(self.width_input.text()),
            "height": int(self.height_input.text()),
            "interpolation": self.interpolation_combo.currentText()
        }
