from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QRadioButton, QPushButton, QProgressBar,
                               QMessageBox, QButtonGroup, QLabel, QWidget, QHBoxLayout, QComboBox, QSlider,
                                 QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt
from portal.ai.enums import GenerationMode
from portal.ai.image_generator import image_to_image, prompt_to_image, get_pipeline, inpaint_image
import torch

class GenerationThread(QThread):
    generation_complete = Signal(object)
    generation_failed = Signal(str)
    generation_step = Signal(object)

    def __init__(self, pipe, mode: GenerationMode, image, prompt, original_size, num_inference_steps, guidance_scale, strength, mask_image=None):
        super().__init__()
        self.pipe = pipe
        self.mode = mode
        self.image = image
        self.mask_image = mask_image
        self.prompt = prompt
        self.original_size = original_size
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.strength = strength
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            step_callback = lambda image: self.generation_step.emit(image)

            cancellation_token = lambda: self.is_cancelled
            if self.mode == GenerationMode.IMAGE_TO_IMAGE:
                if self.mask_image:
                    generated_image = inpaint_image(self.pipe, self.image, self.mask_image, self.prompt,
                                                     strength=self.strength,
                                                     num_inference_steps=self.num_inference_steps,
                                                     guidance_scale=self.guidance_scale,
                                                     step_callback=step_callback,
                                                     cancellation_token=cancellation_token)
                else:
                    generated_image = image_to_image(self.pipe, self.image, self.prompt,
                                                    strength=self.strength,
                                                    num_inference_steps=self.num_inference_steps,
                                                    guidance_scale=self.guidance_scale,
                                                    step_callback=step_callback,
                                                    cancellation_token=cancellation_token)
            else:
                generated_image = prompt_to_image(self.pipe, self.prompt,
                                                  original_size=self.original_size,
                                                  num_inference_steps=self.num_inference_steps,
                                                  guidance_scale=self.guidance_scale,
                                                  step_callback=step_callback,
                                                  cancellation_token=cancellation_token)
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AIPanel(QWidget):
    image_generated = Signal(object)
    pipe = None # Class variable to hold the loaded pipeline
    current_model = None
    is_img2img = None
    is_inpaint = None

    def __init__(self, app, preview_panel, parent=None):
        super().__init__(parent)
        self.app = app
        self.preview_panel = preview_panel
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(128)
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
        self.prompt_to_image_button = QPushButton("T to I")
        self.image_to_image_button = QPushButton("I to I")
        self.variations_button = QPushButton("Vr")

        buttons_layout.addWidget(self.prompt_to_image_button)
        buttons_layout.addWidget(self.image_to_image_button)
        buttons_layout.addWidget(self.variations_button)

        self.layout.addLayout(buttons_layout)

        self.variations_button.setEnabled(False)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("X")
        self.cancel_button.setFixedSize(20, 20)
        progress_layout.addWidget(self.cancel_button)
        self.layout.addLayout(progress_layout)

        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)

        # --- Connections ---
        self.prompt_to_image_button.clicked.connect(lambda: self.start_generation(GenerationMode.PROMPT_TO_IMAGE))
        self.image_to_image_button.clicked.connect(lambda: self.start_generation(GenerationMode.IMAGE_TO_IMAGE))
        self.variations_button.clicked.connect(self.generate_variations)
        self.cancel_button.clicked.connect(self.cancel_generation)

        if not torch.cuda.is_available():
            QMessageBox.warning(self, "CUDA Not Available", "CUDA is not available. AI features will be disabled.")
            self.set_buttons_enabled(False)


    def start_generation(self, mode: GenerationMode):
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
        mask_image = None
        original_size = (self.app.document.width, self.app.document.height)

        model_name = self.model_combo.currentText()

        is_inpaint = False
        if mode == GenerationMode.IMAGE_TO_IMAGE:
            input_image = self.app.get_current_image()
            if input_image is None:
                QMessageBox.warning(self, "Warning", "No image available for Image to Image generation.")
                return

            if self.app.canvas.selection_shape is not None:
                is_inpaint = True
                mask_image = self.app.canvas.get_selection_mask_pil()


        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        self.set_buttons_enabled(False)

        is_img2img = (mode == GenerationMode.IMAGE_TO_IMAGE)

        # if the model or pipeline type has changed, unload the old one
        if AIPanel.current_model != model_name or AIPanel.is_img2img != is_img2img or AIPanel.is_inpaint != is_inpaint:
            self._cleanup_gpu_memory()
            AIPanel.current_model = None
            AIPanel.is_img2img = None
            AIPanel.is_inpaint = None

        # Load the pipeline if it's not already loaded
        if AIPanel.pipe is None:
            try:
                AIPanel.pipe = get_pipeline(model_name, is_img2img, is_inpaint)
                AIPanel.current_model = model_name
                AIPanel.is_img2img = is_img2img
                AIPanel.is_inpaint = is_inpaint
            except Exception as e:
                self.on_generation_failed(f"Failed to load AI model: {e}")
                return

        num_inference_steps = self.steps_slider.value()
        guidance_scale = self.guidance_slider.value() / 10.0
        strength = self.strength_slider.value() / 100.0

        self.thread = GenerationThread(AIPanel.pipe, mode, input_image, prompt, original_size,
                                       num_inference_steps, guidance_scale, strength, mask_image=mask_image)
        self.thread.generation_complete.connect(self.on_generation_complete)
        self.thread.generation_failed.connect(self.on_generation_failed)
        self.thread.generation_step.connect(self.on_generation_step)
        self.thread.start()

    def on_generation_step(self, image):
        if isinstance(image, Image.Image):
            # If the image is larger than 128px in width or height, scale it down.
            if image.width > 128 or image.height > 128:
                image = image.resize((128, 128), Image.Resampling.NEAREST)

            pixmap = self.pil_to_pixmap(image)
            self.preview_panel.preview_label.setPixmap(pixmap)
            self.preview_panel.preview_label.setFixedSize(pixmap.size())

    def on_generation_complete(self, result):
        if isinstance(result, Image.Image):
            self.generated_image = result
            self.image_generated.emit(self.generated_image)

        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.set_buttons_enabled(True)
        self.variations_button.setEnabled(True)
        self.preview_panel.update_preview()


    def cancel_generation(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancel()

    def on_generation_failed(self, error_message):
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.set_buttons_enabled(True)
        if not self.thread.is_cancelled:
            QMessageBox.critical(self, "Error", f"Image generation failed:\n{error_message}")

    def generate_variations(self):
        if self.generated_image:
            self.start_generation(GenerationMode.IMAGE_TO_IMAGE)
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
