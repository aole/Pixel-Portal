from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QRadioButton,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QButtonGroup,
    QLabel,
    QWidget,
    QHBoxLayout,
    QComboBox,
    QSlider,
    QSizePolicy,
    QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PIL import Image, ImageChops
from PIL.ImageQt import ImageQt
from portal.ai.enums import GenerationMode
from portal.ai.image_generator import (
    ImageGenerator,
    is_cuda_available,
    is_diffusers_available,
    is_torch_available,
)

class GenerationThread(QThread):
    generation_complete = Signal(object)
    generation_failed = Signal(str)
    generation_step = Signal(object)

    def __init__(
        self,
        generator: ImageGenerator,
        mode: GenerationMode,
        image,
        prompt,
        original_size,
        generation_size,
        num_inference_steps,
        guidance_scale,
        strength,
        remove_background=False,
        mask_image=None,
    ):
        super().__init__()
        self.generator = generator
        self.mode = mode
        self.image = image
        self.mask_image = mask_image
        self.prompt = prompt
        self.original_size = original_size
        self.generation_size = generation_size
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.strength = strength
        self.remove_background = remove_background
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            step_callback = lambda image: self.generation_step.emit(image)

            cancellation_token = lambda: self.is_cancelled
            if self.mode == GenerationMode.IMAGE_TO_IMAGE:
                if self.mask_image:
                    generated_image = self.generator.inpaint_image(
                        self.image,
                        self.mask_image,
                        self.prompt,
                        strength=self.strength,
                        num_inference_steps=self.num_inference_steps,
                        guidance_scale=self.guidance_scale,
                        step_callback=step_callback,
                        cancellation_token=cancellation_token,
                        remove_background=self.remove_background,
                        generation_size=self.generation_size,
                    )
                else:
                    generated_image = self.generator.image_to_image(
                        self.image,
                        self.prompt,
                        strength=self.strength,
                        num_inference_steps=self.num_inference_steps,
                        guidance_scale=self.guidance_scale,
                        step_callback=step_callback,
                        cancellation_token=cancellation_token,
                        remove_background=self.remove_background,
                        generation_size=self.generation_size,
                    )
            else:
                generated_image = self.generator.prompt_to_image(
                    self.prompt,
                    original_size=self.original_size,
                    generation_size=self.generation_size,
                    num_inference_steps=self.num_inference_steps,
                    guidance_scale=self.guidance_scale,
                    step_callback=step_callback,
                    cancellation_token=cancellation_token,
                    remove_background=self.remove_background,
                )
            self.generation_complete.emit(generated_image)
        except Exception as e:
            self.generation_failed.emit(str(e))

class AIPanel(QWidget):
    image_generated = Signal(object)

    def __init__(self, app, preview_panel, parent=None):
        super().__init__(parent)
        self.app = app
        self.preview_panel = preview_panel
        self.image_generator = ImageGenerator()
        self.setWindowTitle("AI Image Generation")
        self.setMinimumWidth(128)
        self.generated_image = None
        self.thread: Optional[GenerationThread] = None

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

        # --- Document Dimensions ---
        self.native_render_label = QLabel()
        self.native_render_label.setObjectName("ai-dimensions-label")
        self.layout.addWidget(self.native_render_label)

        self.output_size_label = QLabel()
        self.output_size_label.setObjectName("ai-output-dimensions-label")
        self.layout.addWidget(self.output_size_label)

        self.edit_output_button = QPushButton("Edit Output Area")
        self.edit_output_button.setCheckable(True)
        self.edit_output_button.toggled.connect(self.toggle_output_editing)
        self.layout.addWidget(self.edit_output_button)

        self.model_combo.currentTextChanged.connect(self.update_dimension_labels)
        self.app.document_changed.connect(self.update_dimension_labels)
        self.app.ai_output_rect_changed.connect(self.update_dimension_labels)
        self.update_dimension_labels()

        # --- Background Removal ---
        self.remove_bg_checkbox = QCheckBox("Remove BG")
        if not self.image_generator.is_background_removal_available():
            self.remove_bg_checkbox.setEnabled(False)
            self.remove_bg_checkbox.setToolTip(
                "Install rembg and onnxruntime to enable background removal"
            )
        self.layout.addWidget(self.remove_bg_checkbox)

        # --- Sliders ---
        sliders_layout = QVBoxLayout()

        # Steps Slider
        steps_layout = QHBoxLayout()
        self.steps_label = QLabel()
        steps_layout.addWidget(self.steps_label)
        self.steps_slider = QSlider(Qt.Horizontal)
        self.steps_slider.setRange(1, 100)
        steps_layout.addWidget(self.steps_slider)
        sliders_layout.addLayout(steps_layout)

        # Guidance Scale Slider
        guidance_layout = QHBoxLayout()
        self.guidance_label = QLabel()
        guidance_layout.addWidget(self.guidance_label)
        self.guidance_slider = QSlider(Qt.Horizontal)
        self.guidance_slider.setRange(0, 200)
        guidance_layout.addWidget(self.guidance_slider)
        sliders_layout.addLayout(guidance_layout)

        # Strength Slider
        strength_layout = QHBoxLayout()
        self.strength_label = QLabel()
        strength_layout.addWidget(self.strength_label)
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(0, 100)
        strength_layout.addWidget(self.strength_slider)
        sliders_layout.addLayout(strength_layout)

        self.layout.addLayout(sliders_layout)

        # Initialize sliders with defaults
        defaults = self.image_generator.defaults
        steps_default = defaults.get("num_inference_steps", 20)
        self.steps_slider.setValue(steps_default)
        self.steps_label.setText(f"Steps: {steps_default}")
        self.steps_slider.valueChanged.connect(lambda value: self.steps_label.setText(f"Steps: {value}"))

        guidance_default = defaults.get("guidance_scale", 7.0)
        self.guidance_slider.setValue(int(guidance_default * 10))
        self.guidance_label.setText(f"Guidance: {guidance_default}")
        self.guidance_slider.valueChanged.connect(lambda value: self.guidance_label.setText(f"Guidance: {value / 10.0}"))

        strength_default = defaults.get("strength", 0.8)
        self.strength_slider.setValue(int(strength_default * 100))
        self.strength_label.setText(f"Strength: {strength_default}")
        self.strength_slider.valueChanged.connect(lambda value: self.strength_label.setText(f"Strength: {value / 100.0}"))

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

        self._dependencies_ready(show_dialog=True, disable=True)


    @staticmethod
    def _normalize_dimensions(size) -> tuple[int, int] | None:
        if size is None:
            return None

        width = height = None
        if hasattr(size, "width") and hasattr(size, "height"):
            width_attr = getattr(size, "width")
            height_attr = getattr(size, "height")
            width = width_attr() if callable(width_attr) else width_attr
            height = height_attr() if callable(height_attr) else height_attr
        elif isinstance(size, (tuple, list)) and len(size) == 2:
            width, height = size
        else:
            return None

        try:
            width = int(width)
            height = int(height)
        except (TypeError, ValueError):
            return None

        if width <= 0 or height <= 0:
            return None
        return width, height

    def _dependencies_ready(self, *, show_dialog: bool = False, disable: bool = False) -> bool:
        message = None
        title = "AI Dependencies Missing"

        if not is_torch_available():
            message = "PyTorch is not installed. Install torch to enable AI features."
        elif not is_diffusers_available():
            message = (
                "diffusers is not installed or missing required pipelines. Install diffusers to enable AI features."
            )
        elif not is_cuda_available():
            title = "CUDA Not Available"
            message = "CUDA is not available. AI features will be disabled."

        if message:
            if show_dialog:
                QMessageBox.warning(self, title, message)
            if disable:
                self.set_buttons_enabled(False)
            return False
        return True

    def _resolve_generation_dimensions(
        self, model_name: str | None = None
    ) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        if model_name is None and self.model_combo is not None:
            model_name = self.model_combo.currentText()

        output_size = None
        if hasattr(self.app, "get_ai_output_rect"):
            rect = self.app.get_ai_output_rect()
        else:
            rect = None
        if rect is not None:
            output_size = self._normalize_dimensions((rect.width(), rect.height()))

        if output_size is None:
            document = getattr(self.app, "document", None)
            if document is not None:
                output_size = self._normalize_dimensions(
                    (getattr(document, "width", None), getattr(document, "height", None))
                )

        native_size = None
        if model_name:
            generation_size = self.image_generator.calculate_generation_size(
                model_name,
                output_size,
            )
            native_size = self._normalize_dimensions(generation_size)

        return native_size, output_size

    @staticmethod
    def _format_dimension_label(prefix: str, size: tuple[int, int] | None) -> str:
        if size:
            return f"{prefix}: {size[0]} × {size[1]}px"
        return f"{prefix}: —"

    def update_dimension_labels(self, *_):
        model_name = self.model_combo.currentText() if self.model_combo else None
        native_size, output_size = self._resolve_generation_dimensions(model_name)

        self.native_render_label.setText(
            self._format_dimension_label("Native Render Size", native_size)
        )
        self.output_size_label.setText(
            self._format_dimension_label("Output Size", output_size)
        )


    def start_generation(self, mode: GenerationMode):
        if not self._dependencies_ready(show_dialog=True, disable=True):
            return

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

        model_name = self.model_combo.currentText() if self.model_combo else None
        native_size, output_size = self._resolve_generation_dimensions(model_name)

        generation_size = native_size
        if generation_size is None and model_name:
            generation_size = self._normalize_dimensions(
                self.image_generator.get_generation_size(model_name)
            )
        if generation_size is None:
            generation_size = (512, 512)

        original_size = output_size or native_size or generation_size

        if not model_name:
            QMessageBox.warning(self, "Warning", "No AI model selected.")
            return

        canvas = getattr(self.app.main_window, "canvas", None)
        selection_shape = getattr(canvas, "selection_shape", None) if canvas else None
        has_selection = bool(selection_shape and not selection_shape.isEmpty())

        ai_rect = self.app.get_ai_output_rect() if hasattr(self.app, "get_ai_output_rect") else None
        crop_box = None
        if ai_rect is not None and ai_rect.width() > 0 and ai_rect.height() > 0:
            left = int(ai_rect.left())
            top = int(ai_rect.top())
            crop_box = (
                left,
                top,
                left + int(ai_rect.width()),
                top + int(ai_rect.height()),
            )

        input_image = None
        mask_image = None
        transparency_mask = None
        transparency_mask_applied = False

        if mode == GenerationMode.IMAGE_TO_IMAGE:
            input_image = self.app.get_current_image()
            if input_image is None:
                QMessageBox.warning(self, "Warning", "No image available for Image to Image generation.")
                return

            if crop_box:
                input_image = input_image.crop(crop_box)

            if input_image is not None and "A" in input_image.getbands():
                alpha_channel = input_image.getchannel("A")
                transparency_mask = alpha_channel.point(
                    lambda value: 255 if value < 255 else 0
                )
                if transparency_mask.getbbox() is None:
                    transparency_mask = None

            if has_selection and callable(getattr(canvas, "get_selection_mask_pil", None)):
                mask_image = canvas.get_selection_mask_pil()
                if mask_image:
                    if crop_box:
                        mask_image = mask_image.crop(crop_box)
                    mask_image = mask_image.convert("L")

            if mask_image and transparency_mask:
                mask_image = ImageChops.lighter(mask_image, transparency_mask)
                transparency_mask_applied = True
            elif transparency_mask and not mask_image:
                mask_image = transparency_mask
                transparency_mask_applied = True

            if mask_image and mask_image.getbbox() is None:
                mask_image = None

        is_inpaint = mask_image is not None


        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        self.set_buttons_enabled(False)

        is_img2img = (mode == GenerationMode.IMAGE_TO_IMAGE)

        try:
            self.image_generator.load_pipeline(model_name, is_img2img=is_img2img, is_inpaint=is_inpaint)
        except Exception as e:
            self.on_generation_failed(f"Failed to load AI model: {e}")
            return

        num_inference_steps = self.steps_slider.value()
        guidance_scale = self.guidance_slider.value() / 10.0
        strength = self.strength_slider.value() / 100.0
        if transparency_mask_applied:
            strength = 1.0

        remove_background = self.remove_bg_checkbox.isChecked()

        self.thread = GenerationThread(
            self.image_generator,
            mode,
            input_image,
            prompt,
            original_size,
            generation_size,
            num_inference_steps,
            guidance_scale,
            strength,
            remove_background=remove_background,
            mask_image=mask_image,
        )
        self.thread.generation_complete.connect(self.on_generation_complete)
        self.thread.generation_failed.connect(self.on_generation_failed)
        self.thread.generation_step.connect(self.on_generation_step)
        self.thread.start()

    def toggle_output_editing(self, enabled: bool):
        main_window = getattr(self.app, "main_window", None)
        canvas = getattr(main_window, "canvas", None)
        enable_method = getattr(canvas, "enable_ai_output_editing", None)

        if not callable(enable_method):
            if enabled:
                self.edit_output_button.blockSignals(True)
                self.edit_output_button.setChecked(False)
                self.edit_output_button.blockSignals(False)
            return

        enable_method(bool(enabled))

    def on_generation_step(self, image):
        if isinstance(image, Image.Image):
            pixmap = self.pil_to_pixmap(image)
            if pixmap.width() > 128 or pixmap.height() > 128:
                pixmap = pixmap.scaled(
                    128,
                    128,
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation,
                )

            self.preview_panel.preview_label.setPixmap(pixmap)
            self.preview_panel.preview_label.setFixedSize(pixmap.size())

    def on_generation_complete(self, result):
        if isinstance(result, Image.Image):
            self.generated_image = result
            self.image_generated.emit(self.generated_image)

        self.thread = None
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
        thread = self.thread
        should_alert = thread is None or not getattr(thread, "is_cancelled", False)
        self.thread = None
        if should_alert and error_message:
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
        self.image_generator.cleanup()

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
