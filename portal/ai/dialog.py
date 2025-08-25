from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QRadioButton, QPushButton, QProgressBar, QMessageBox, QButtonGroup
from PySide6.QtCore import Qt, QThread, Signal
from PIL import Image
from .image_generator import image_to_image, prompt_to_image

class GenerationThread(QThread):
    generation_complete = Signal(Image.Image)
    generation_failed = Signal(str)

    def __init__(self, mode, image, prompt, original_size):
        super().__init__()
        self.mode = mode
        self.image = image
        self.prompt = prompt
        self.original_size = original_size

    def run(self):
        try:
            if self.mode == "Image to Image":
                generated_image = image_to_image(self.image, self.prompt)
            else:
                generated_image = prompt_to_image(self.prompt, original_size=self.original_size)
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AiDialog(QDialog):
    last_prompt = "Chibi warrior, fighting stance, plain background"

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout(self)

        self.prompt_input = QLineEdit()
        self.prompt_input.setText(AiDialog.last_prompt)
        self.layout.addWidget(self.prompt_input)

        self.radio_button_group = QButtonGroup()

        self.image_to_image_radio = QRadioButton("Image to Image")
        self.image_to_image_radio.setChecked(True)
        self.layout.addWidget(self.image_to_image_radio)
        self.radio_button_group.addButton(self.image_to_image_radio)

        self.prompt_to_image_radio = QRadioButton("Prompt to Image")
        self.layout.addWidget(self.prompt_to_image_radio)
        self.radio_button_group.addButton(self.prompt_to_image_radio)

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.start_generation)
        self.layout.addWidget(self.generate_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.layout.addWidget(self.cancel_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

    def start_generation(self):
        prompt = self.prompt_input.text()
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt.")
            return

        AiDialog.last_prompt = prompt

        mode = "Image to Image" if self.image_to_image_radio.isChecked() else "Prompt to Image"

        input_image = None
        original_size = (self.app.document.width, self.app.document.height)
        if mode == "Image to Image":
            input_image = self.app.get_current_image()

        self.progress_bar.setVisible(True)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        self.thread = GenerationThread(mode, input_image, prompt, original_size)
        self.thread.generation_complete.connect(self.on_generation_complete)
        self.thread.generation_failed.connect(self.on_generation_failed)
        self.thread.start()

    def on_generation_complete(self, image):
        self.app.add_new_layer_with_image(image)
        self.accept()

    def on_generation_failed(self, error_message):
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Image generation failed:\n{error_message}")

    def get_settings(self):
        return {
            "prompt": self.prompt_input.text(),
            "mode": "Image to Image" if self.image_to_image_radio.isChecked() else "Prompt to Image"
        }
