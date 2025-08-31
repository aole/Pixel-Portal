from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QRadioButton, QPushButton, QProgressBar, QMessageBox, QButtonGroup, QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt
from .ai.image_generator import image_to_image, prompt_to_image, get_pipeline
import torch

class GenerationThread(QThread):
    generation_complete = Signal(object)
    generation_failed = Signal(str)

    def __init__(self, pipe, mode, image, prompt, original_size):
        super().__init__()
        self.pipe = pipe
        self.mode = mode
        self.image = image
        self.prompt = prompt
        self.original_size = original_size

    def run(self):
        try:
            if self.mode == "Image to Image":
                generated_image = image_to_image(self.pipe, self.image, self.prompt)
            else:
                generated_image = prompt_to_image(self.pipe, self.prompt, original_size=self.original_size)
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AIPanel(QWidget):
    image_generated = Signal(object)
    last_prompt = "Chibi warrior, fighting stance, plain background"
    pipe = None # Class variable to hold the loaded pipeline

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(512)
        self.generated_image = None

        self.layout = QVBoxLayout(self)

        self.prompt_input = QLineEdit()
        self.prompt_input.setText(AIPanel.last_prompt)
        self.layout.addWidget(self.prompt_input)

        self.image_viewer = QLabel()
        self.image_viewer.setAlignment(Qt.AlignCenter)
        self.image_viewer.setMinimumSize(512, 512)
        self.alphabg_pixmap = QPixmap('alphabg.png')
        self.image_viewer.setPixmap(self.alphabg_pixmap)
        self.layout.addWidget(self.image_viewer)

        self.radio_button_group = QButtonGroup()
        self.prompt_to_image_radio = QRadioButton("Prompt to Image")
        self.prompt_to_image_radio.setChecked(True)
        self.layout.addWidget(self.prompt_to_image_radio)
        self.radio_button_group.addButton(self.prompt_to_image_radio)
        self.image_to_image_radio = QRadioButton("Image to Image")
        self.layout.addWidget(self.image_to_image_radio)
        self.radio_button_group.addButton(self.image_to_image_radio)

        # --- Buttons ---
        self.generate_buttons_widget = QWidget()
        generate_buttons_layout = QHBoxLayout(self.generate_buttons_widget)
        generate_buttons_layout.setContentsMargins(0,0,0,0)
        self.generate_button = QPushButton("Generate")
        generate_buttons_layout.addWidget(self.generate_button)
        self.layout.addWidget(self.generate_buttons_widget)

        self.viewer_buttons_widget = QWidget()
        viewer_buttons_layout = QHBoxLayout(self.viewer_buttons_widget)
        viewer_buttons_layout.setContentsMargins(0,0,0,0)
        self.accept_button = QPushButton("Accept")
        self.cancel_viewer_button = QPushButton("Cancel")
        self.regenerate_button = QPushButton("Regenerate")
        viewer_buttons_layout.addWidget(self.accept_button)
        viewer_buttons_layout.addWidget(self.cancel_viewer_button)
        viewer_buttons_layout.addWidget(self.regenerate_button)
        self.layout.addWidget(self.viewer_buttons_widget)
        self.viewer_buttons_widget.setVisible(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        # --- Connections ---
        self.generate_button.clicked.connect(self.start_generation)
        self.accept_button.clicked.connect(self.accept_image)
        self.cancel_viewer_button.clicked.connect(self.cancel_viewer)
        self.regenerate_button.clicked.connect(self.regenerate_image)
        self.image_to_image_radio.toggled.connect(self.on_mode_changed)

    def on_mode_changed(self, checked):
        if checked:
            image = self.app.get_current_image()
            if image:
                pixmap = self.pil_to_pixmap(image)
                self.image_viewer.setPixmap(pixmap.scaled(self.image_viewer.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
        else:
            self.image_viewer.setPixmap(self.alphabg_pixmap)

    def start_generation(self):
        prompt = self.prompt_input.text()
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt.")
            return

        AIPanel.last_prompt = prompt
        mode = "Image to Image" if self.image_to_image_radio.isChecked() else "Prompt to Image"
        input_image = None
        original_size = (self.app.document.width, self.app.document.height)
        if mode == "Image to Image":
            input_image = self.app.get_current_image()

        self.progress_bar.setVisible(True)
        self.generate_buttons_widget.setEnabled(False)
        self.viewer_buttons_widget.setVisible(False)

        # Load the pipeline if it's not already loaded
        if AIPanel.pipe is None:
            is_img2img = (mode == "Image to Image")
            try:
                AIPanel.pipe = get_pipeline(is_img2img)
            except Exception as e:
                self.on_generation_failed(f"Failed to load AI model: {e}")
                return

        self.thread = GenerationThread(AIPanel.pipe, mode, input_image, prompt, original_size)
        self.thread.generation_complete.connect(self.on_generation_complete)
        self.thread.generation_failed.connect(self.on_generation_failed)
        self.thread.start()

    def on_generation_complete(self, result):
        if isinstance(result, Image.Image):
            self.generated_image = result
            pixmap = self.pil_to_pixmap(result)
            self.image_viewer.setPixmap(pixmap.scaled(self.image_viewer.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
        
        self.progress_bar.setVisible(False)
        self.generate_buttons_widget.setVisible(False)
        self.generate_buttons_widget.setEnabled(True)
        self.viewer_buttons_widget.setVisible(True)

    def on_generation_failed(self, error_message):
        self.progress_bar.setVisible(False)
        self.generate_buttons_widget.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Image generation failed:\n{error_message}")

    def accept_image(self):
        if self.generated_image:
            self.image_generated.emit(self.generated_image)
        self.cancel_viewer()

    def cancel_viewer(self):
        self.viewer_buttons_widget.setVisible(False)
        self.generate_buttons_widget.setVisible(True)
        self.generated_image = None
        self.image_viewer.setPixmap(self.alphabg_pixmap)

    def regenerate_image(self):
        self.viewer_buttons_widget.setVisible(False)
        self.generate_buttons_widget.setVisible(True)
        self.start_generation()

    def _cleanup_gpu_memory(self):
        """Deletes the model and clears the GPU cache."""
        if AIPanel.pipe is not None:
            del AIPanel.pipe
            AIPanel.pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("AI pipeline and GPU cache cleared.")

    def closeEvent(self, event):
        """Clean up GPU memory when the panel is closed."""
        self._cleanup_gpu_memory()
        super().closeEvent(event)

    @staticmethod
    def pil_to_pixmap(pil_image):
        image_qt = ImageQt(pil_image)
        return QPixmap.fromImage(image_qt)

    def get_settings(self):
        return {
            "prompt": self.prompt_input.text(),
            "mode": "Image to Image" if self.image_to_image_radio.isChecked() else "Prompt to Image"
        }
