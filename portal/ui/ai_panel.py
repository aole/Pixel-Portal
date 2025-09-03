from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QRadioButton, QPushButton, QProgressBar,
                               QMessageBox, QButtonGroup, QLabel, QWidget, QHBoxLayout, QComboBox, QSlider,
                                 QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt
from portal.ai.image_generator import image_to_image, prompt_to_image, get_pipeline
import torch

class GenerationThread(QThread):
    generation_complete = Signal(object)
    generation_failed = Signal(str)

    def __init__(self, pipe, mode, image, prompt, original_size, num_inference_steps, guidance_scale, strength):
        super().__init__()
        self.pipe = pipe
        self.mode = mode
        self.image = image
        self.prompt = prompt
        self.original_size = original_size
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.strength = strength

    def run(self):
        try:
            if self.mode == "Image to Image":
                generated_image = image_to_image(self.pipe, self.image, self.prompt,
                                                 strength=self.strength,
                                                 num_inference_steps=self.num_inference_steps,
                                                 guidance_scale=self.guidance_scale)
            else:
                generated_image = prompt_to_image(self.pipe, self.prompt,
                                                  original_size=self.original_size,
                                                  num_inference_steps=self.num_inference_steps,
                                                  guidance_scale=self.guidance_scale)
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AIPanel(QWidget):
    image_generated = Signal(object)
    pipe = None # Class variable to hold the loaded pipeline
    current_model = None

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(512)
        self.generated_image = None

        self.layout = QVBoxLayout(self)

        self.prompt_input = QTextEdit()
        last_prompt = self.app.config.get('AI', 'last_prompt', fallback="Chibi warrior, fighting stance, plain background")
        self.prompt_input.setText(last_prompt)
        self.prompt_input.setFixedHeight(self.fontMetrics().lineSpacing() * 4)
        self.layout.addWidget(self.prompt_input)

        # --- Model Selection ---
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["SD1.5", "SDXL"])
        self.model_combo.setCurrentText("SD1.5")
        model_layout.addWidget(self.model_combo)
        self.layout.addLayout(model_layout)

        # --- Sliders ---
        sliders_layout = QVBoxLayout()

        # Steps Slider
        steps_layout = QHBoxLayout()
        self.steps_label = QLabel("Steps: 20")
        steps_layout.addWidget(self.steps_label)
        self.steps_slider = QSlider(Qt.Horizontal)
        self.steps_slider.setRange(1, 100)
        self.steps_slider.setValue(20)
        self.steps_slider.valueChanged.connect(lambda value: self.steps_label.setText(f"Steps: {value}"))
        steps_layout.addWidget(self.steps_slider)
        sliders_layout.addLayout(steps_layout)

        # Guidance Scale Slider
        guidance_layout = QHBoxLayout()
        self.guidance_label = QLabel("Guidance: 7.0")
        guidance_layout.addWidget(self.guidance_label)
        self.guidance_slider = QSlider(Qt.Horizontal)
        self.guidance_slider.setRange(0, 200)
        self.guidance_slider.setValue(70)
        self.guidance_slider.valueChanged.connect(lambda value: self.guidance_label.setText(f"Guidance: {value / 10.0}"))
        guidance_layout.addWidget(self.guidance_slider)
        sliders_layout.addLayout(guidance_layout)

        # Strength Slider
        strength_layout = QHBoxLayout()
        self.strength_label = QLabel("Strength: 0.8")
        strength_layout.addWidget(self.strength_label)
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(0, 100)
        self.strength_slider.setValue(80)
        self.strength_slider.valueChanged.connect(lambda value: self.strength_label.setText(f"Strength: {value / 100.0}"))
        strength_layout.addWidget(self.strength_slider)
        sliders_layout.addLayout(strength_layout)

        self.layout.addLayout(sliders_layout)

        # --- Buttons ---
        buttons_layout = QHBoxLayout()
        self.prompt_to_image_button = QPushButton("Prompt to Image")
        self.image_to_image_button = QPushButton("Image to Image")
        self.variations_button = QPushButton("Variations")

        buttons_layout.addWidget(self.prompt_to_image_button)
        buttons_layout.addWidget(self.image_to_image_button)
        buttons_layout.addWidget(self.variations_button)

        self.layout.addLayout(buttons_layout)

        self.variations_button.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        # --- Connections ---
        self.prompt_to_image_button.clicked.connect(lambda: self.start_generation("Prompt to Image"))
        self.image_to_image_button.clicked.connect(lambda: self.start_generation("Image to Image"))
        self.variations_button.clicked.connect(self.generate_variations)


    def start_generation(self, mode):
        prompt = self.prompt_input.toPlainText()
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt.")
            return

        additions = "pixel art, pixel world"
        if additions not in prompt:
            prompt = f"{prompt}, {additions}"

        if not self.app.config.has_section('AI'):
            self.app.config.add_section('AI')
        self.app.config.set('AI', 'last_prompt', prompt)
        self.app.save_settings()

        input_image = None
        original_size = (self.app.document.width, self.app.document.height)

        model_name = self.model_combo.currentText()

        if mode == "Image to Image":
            input_image = self.app.get_current_image()
            if input_image is None:
                QMessageBox.warning(self, "Warning", "No image available for Image to Image generation.")
                return

        self.progress_bar.setVisible(True)
        self.set_buttons_enabled(False)

        # if the model has changed, unload the old one
        if AIPanel.current_model != model_name:
            self._cleanup_gpu_memory()
            AIPanel.current_model = None

        # Load the pipeline if it's not already loaded
        if AIPanel.pipe is None:
            is_img2img = (mode == "Image to Image")
            try:
                AIPanel.pipe = get_pipeline(model_name, is_img2img)
                AIPanel.current_model = model_name
            except Exception as e:
                self.on_generation_failed(f"Failed to load AI model: {e}")
                return

        num_inference_steps = self.steps_slider.value()
        guidance_scale = self.guidance_slider.value() / 10.0
        strength = self.strength_slider.value() / 100.0

        self.thread = GenerationThread(AIPanel.pipe, mode, input_image, prompt, original_size,
                                       num_inference_steps, guidance_scale, strength)
        self.thread.generation_complete.connect(self.on_generation_complete)
        self.thread.generation_failed.connect(self.on_generation_failed)
        self.thread.start()

    def on_generation_complete(self, result):
        if isinstance(result, Image.Image):
            self.generated_image = result
            self.image_generated.emit(self.generated_image)

        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        self.variations_button.setEnabled(True)


    def on_generation_failed(self, error_message):
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        QMessageBox.critical(self, "Error", f"Image generation failed:\n{error_message}")

    def generate_variations(self):
        if self.generated_image:
            self.start_generation("Image to Image")
        else:
            QMessageBox.warning(self, "Warning", "No image to generate variations from.")

    def set_buttons_enabled(self, enabled):
        self.prompt_to_image_button.setEnabled(enabled)
        self.image_to_image_button.setEnabled(enabled)
        self.variations_button.setEnabled(enabled and self.generated_image is not None)


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
            "prompt": self.prompt_input.toPlainText(),
            "model": self.model_combo.currentText(),
            "steps": self.steps_slider.value(),
            "guidance": self.guidance_slider.value(),
            "strength": self.strength_slider.value(),
        }
