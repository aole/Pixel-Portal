from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QColorDialog,
    QCheckBox,
)
from PySide6.QtGui import QColor

class ColorButton(QPushButton):
    """A button that displays a color and opens a color dialog when clicked."""
    def __init__(self, color=QColor("black")):
        super().__init__()
        self._color = color
        self.setStyleSheet(f"background-color: {self._color.name()}")
        self.clicked.connect(self.on_click)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self.setStyleSheet(f"background-color: {self._color.name()}")

    def on_click(self):
        color = QColorDialog.getColor(self._color, self)
        if color.isValid():
            self.color = color

class ScriptDialog(QDialog):
    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Script Parameters")

        self.widgets = {}
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        for param in params:
            name = param['name']
            label = param['label']
            param_type = param.get('type', 'text')
            default = param.get('default')

            if param_type == 'text':
                widget = QLineEdit(default)
            elif param_type == 'number':
                widget = QSpinBox()
                if 'min' in param:
                    widget.setMinimum(param['min'])
                if 'max' in param:
                    widget.setMaximum(param['max'])
                if default is not None:
                    widget.setValue(default)
            elif param_type == 'color':
                widget = ColorButton(QColor(default))
            elif param_type == 'choice':
                widget = QComboBox()
                if 'choices' in param:
                    widget.addItems(param['choices'])
                if default is not None:
                    widget.setCurrentText(default)
            elif param_type == 'checkbox':
                widget = QCheckBox()
                if default is not None:
                    widget.setChecked(bool(default))
                else:
                    widget.setChecked(False)

            self.form_layout.addRow(label, widget)
            self.widgets[name] = (param_type, widget)

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_values(self):
        values = {}
        for name, (param_type, widget) in self.widgets.items():
            if param_type == 'text':
                values[name] = widget.text()
            elif param_type == 'number':
                values[name] = widget.value()
            elif param_type == 'color':
                values[name] = widget.color
            elif param_type == 'choice':
                values[name] = widget.currentText()
            elif param_type == 'checkbox':
                values[name] = widget.isChecked()
        return values
