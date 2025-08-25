from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QProgressBar, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from PIL import Image
from .ai.image_generator import image_to_image

class GenerationThread(QThread):
    generation_complete = Signal(Image.Image)
    generation_failed = Signal(str)

    def __init__(self, image, prompt):
        super().__init__()
        self.image = image
        self.prompt = prompt

    def run(self):
        try:
            generated_image = image_to_image(self.image, self.prompt)
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AiDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout(self)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter a prompt...")
        self.layout.addWidget(self.prompt_input)

        self.generation_mode = QComboBox()
        self.generation_mode.addItems(["Image to Image", "Prompt to Image"])
        self.layout.addWidget(self.generation_mode)

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

        mode = self.generation_mode.currentText()
        if mode == "Image to Image":
            input_image = self.app.get_current_image()
        else:
            # Create a blank image for prompt-to-image
            input_image = Image.new("RGBA", (512, 512), (255, 255, 255, 255))

        self.progress_bar.setVisible(True)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        self.thread = GenerationThread(input_image, prompt)
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
            "mode": self.generation_mode.currentText()
        }
