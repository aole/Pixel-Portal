import json
import os
from datetime import datetime

import torch
from diffusers import (
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLInpaintPipeline,
    StableDiffusionXLPipeline,
)
from PIL import Image
try:
    from rembg import remove as rembg_remove
except Exception:  # ImportError or runtime errors such as missing onnxruntime
    rembg_remove = None

REMBG_AVAILABLE = rembg_remove is not None


class ImageGenerator:
    """Wrapper around Stable Diffusion pipelines with configurable defaults."""

    def __init__(self, config_path: str | None = None) -> None:
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as f:
            cfg = json.load(f)
        self.model_configs = cfg.get("models", {})
        self.defaults = cfg.get("defaults", {})

        self.pipe = None
        self.current_model = None
        self.is_img2img = None
        self.is_inpaint = None

    @staticmethod
    def _coerce_dimension(value) -> int | None:
        """Convert raw config values into a positive integer dimension."""

        try:
            dimension = int(value)
        except (TypeError, ValueError):
            return None
        if dimension <= 0:
            return None
        return dimension

    def _coerce_size(self, candidate) -> tuple[int, int] | None:
        """Normalise a variety of config size formats to (width, height)."""

        if candidate is None:
            return None

        if isinstance(candidate, dict):
            width = self._coerce_dimension(candidate.get("width"))
            height = self._coerce_dimension(candidate.get("height"))
            if width and height:
                return width, height
            return None

        if isinstance(candidate, (list, tuple)) and len(candidate) == 2:
            width = self._coerce_dimension(candidate[0])
            height = self._coerce_dimension(candidate[1])
            if width and height:
                return width, height
            return None

        if isinstance(candidate, str):
            normalized = (
                candidate.lower()
                .strip()
                .replace("×", "x")
                .replace(",", "x")
            )
            if "x" in normalized:
                parts = [part for part in normalized.split("x") if part]
                if len(parts) == 2:
                    width = self._coerce_dimension(parts[0])
                    height = self._coerce_dimension(parts[1])
                    if width and height:
                        return width, height
            return None

        return None

    def get_generation_size(self, model_name: str) -> tuple[int, int] | None:
        """Return the size (width, height) the model generates before resizing."""

        if not model_name:
            return None

        model_cfg = self.model_configs.get(model_name)
        if not model_cfg:
            return None

        for key in ("generation_size", "image_size"):
            size = self._coerce_size(model_cfg.get(key))
            if size:
                return size

        width = self._coerce_dimension(model_cfg.get("generation_width"))
        height = self._coerce_dimension(model_cfg.get("generation_height"))
        if width and height:
            return width, height

        width = self._coerce_dimension(model_cfg.get("width"))
        height = self._coerce_dimension(model_cfg.get("height"))
        if width and height:
            return width, height

        model_name_upper = str(model_name).upper()
        if "XL" in model_name_upper:
            return 1024, 1024

        return 512, 512

    def load_pipeline(self, model_name: str, is_img2img: bool = False, is_inpaint: bool = False):
        """Load and cache the requested pipeline."""
        if (
            self.pipe
            and self.current_model == model_name
            and self.is_img2img == is_img2img
            and self.is_inpaint == is_inpaint
        ):
            return self.pipe

        self.cleanup()

        model_cfg = self.model_configs.get(model_name)
        if not model_cfg:
            raise ValueError("Invalid model name")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if device == "cuda" else torch.float32

        pipeline_params = {
            "torch_dtype": torch_dtype,
            "use_safetensors": True,
        }
        if "clip_skip" in model_cfg:
            pipeline_params["clip_skip"] = model_cfg["clip_skip"]

        if model_name == "SDXL":
            if is_inpaint:
                PipelineClass = StableDiffusionXLInpaintPipeline
            elif is_img2img:
                PipelineClass = StableDiffusionXLImg2ImgPipeline
            else:
                PipelineClass = StableDiffusionXLPipeline
        elif model_name == "SD1.5":
            if is_inpaint:
                PipelineClass = StableDiffusionInpaintPipeline
            elif is_img2img:
                PipelineClass = StableDiffusionImg2ImgPipeline
            else:
                PipelineClass = StableDiffusionPipeline
        else:
            raise ValueError("Invalid model name")

        print(f"Loading {model_name} AI pipeline...")
        self.pipe = PipelineClass.from_single_file(
            model_cfg["path"],
            **pipeline_params,
        ).to(device)
        print("AI pipeline loaded successfully.")

        self.current_model = model_name
        self.is_img2img = is_img2img
        self.is_inpaint = is_inpaint
        return self.pipe

    def cleanup(self):
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("AI pipeline and GPU cache cleared.")

    def _remove_background(self, image: Image.Image) -> Image.Image:
        if not REMBG_AVAILABLE:
            print(
                "Background removal unavailable: rembg or its dependencies are not installed."
            )
            return image
        try:
            return rembg_remove(image)
        except Exception as e:
            print(f"Background removal failed: {e}")
            return image

    @staticmethod
    def is_background_removal_available() -> bool:
        return REMBG_AVAILABLE

    def prompt_to_image(
        self,
        prompt: str,
        original_size: tuple[int, int],
        num_inference_steps: int | None = None,
        guidance_scale: float | None = None,
        output_dir: str | None = None,
        step_callback=None,
        cancellation_token=None,
        remove_background: bool = False,
    ) -> Image.Image:
        output_dir = output_dir or self.defaults.get("output_dir", "output")
        num_inference_steps = num_inference_steps or self.defaults.get("num_inference_steps", 20)
        guidance_scale = guidance_scale or self.defaults.get("guidance_scale", 7.0)
        os.makedirs(output_dir, exist_ok=True)

        def callback(pipe, step_index, timestep, callback_kwargs):
            if cancellation_token and cancellation_token():
                pipe._interrupt = True
            if step_callback:
                latents = callback_kwargs["latents"]
                latents = 1 / 0.18215 * latents
                image = pipe.vae.decode(latents).sample
                image = (image / 2 + 0.5).clamp(0, 1)
                image = image.cpu().permute(0, 2, 3, 1).numpy()
                image = (image[0] * 255).round().astype("uint8")
                image = Image.fromarray(image)
                step_callback(image)
            return callback_kwargs

        print("Generating image from prompt...")
        generated_image = self.pipe(
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            callback_on_step_end=callback,
        ).images[0]

        if remove_background:
            generated_image = self._remove_background(generated_image)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"
        generated_image.save(os.path.join(output_dir, filename))
        final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
        return final_image

    def image_to_image(
        self,
        input_image: Image.Image,
        prompt: str,
        strength: float | None = None,
        num_inference_steps: int | None = None,
        guidance_scale: float | None = None,
        output_dir: str | None = None,
        step_callback=None,
        cancellation_token=None,
        remove_background: bool = False,
    ) -> Image.Image:
        output_dir = output_dir or self.defaults.get("output_dir", "output")
        num_inference_steps = num_inference_steps or self.defaults.get("num_inference_steps", 20)
        guidance_scale = guidance_scale or self.defaults.get("guidance_scale", 7.0)
        strength = strength if strength is not None else self.defaults.get("strength", 0.8)
        os.makedirs(output_dir, exist_ok=True)
        original_size = input_image.size

        def callback(pipe, step_index, timestep, callback_kwargs):
            if cancellation_token and cancellation_token():
                pipe._interrupt = True
            if step_callback:
                latents = callback_kwargs["latents"]
                latents = 1 / 0.18215 * latents
                image = pipe.vae.decode(latents).sample
                image = (image / 2 + 0.5).clamp(0, 1)
                image = image.cpu().permute(0, 2, 3, 1).numpy()
                image = (image[0] * 255).round().astype("uint8")
                image = Image.fromarray(image)
                step_callback(image)
            return callback_kwargs

        print("Preparing input image for img2img...")
        if isinstance(self.pipe, StableDiffusionXLImg2ImgPipeline):
            model_input_image = input_image.convert("RGB").resize((1024, 1024), Image.Resampling.NEAREST)
        else:
            model_input_image = input_image.convert("RGB").resize((512, 512), Image.Resampling.NEAREST)

        print("Generating image from image...")
        generated_image = self.pipe(
            prompt=prompt,
            image=model_input_image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            callback_on_step_end=callback,
        ).images[0]

        if remove_background:
            generated_image = self._remove_background(generated_image)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"
        generated_image.save(os.path.join(output_dir, filename))
        final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
        return final_image

    def inpaint_image(
        self,
        input_image: Image.Image,
        mask_image: Image.Image,
        prompt: str,
        strength: float | None = None,
        num_inference_steps: int | None = None,
        guidance_scale: float | None = None,
        output_dir: str | None = None,
        step_callback=None,
        cancellation_token=None,
        remove_background: bool = False,
    ) -> Image.Image:
        output_dir = output_dir or self.defaults.get("output_dir", "output")
        num_inference_steps = num_inference_steps or self.defaults.get("num_inference_steps", 20)
        guidance_scale = guidance_scale or self.defaults.get("guidance_scale", 7.0)
        strength = strength if strength is not None else self.defaults.get("strength", 0.8)
        os.makedirs(output_dir, exist_ok=True)
        original_size = input_image.size

        def callback(pipe, step_index, timestep, callback_kwargs):
            if cancellation_token and cancellation_token():
                pipe._interrupt = True
            if step_callback:
                latents = callback_kwargs["latents"]
                latents = 1 / 0.18215 * latents
                image = pipe.vae.decode(latents).sample
                image = (image / 2 + 0.5).clamp(0, 1)
                image = image.cpu().permute(0, 2, 3, 1).numpy()
                image = (image[0] * 255).round().astype("uint8")
                image = Image.fromarray(image)
                step_callback(image)
            return callback_kwargs

        print("Preparing input image for inpainting...")
        if isinstance(self.pipe, StableDiffusionXLInpaintPipeline):
            model_input_image = input_image.convert("RGB").resize((1024, 1024), Image.Resampling.NEAREST)
            mask_image = mask_image.convert("RGB").resize((1024, 1024), Image.Resampling.NEAREST)
        else:
            model_input_image = input_image.convert("RGB").resize((512, 512), Image.Resampling.NEAREST)
            mask_image = mask_image.convert("RGB").resize((512, 512), Image.Resampling.NEAREST)

        print("Generating image from image...")
        generated_image = self.pipe(
            prompt=prompt,
            image=model_input_image,
            mask_image=mask_image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            callback_on_step_end=callback,
        ).images[0]

        if remove_background:
            generated_image = self._remove_background(generated_image)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"
        generated_image.save(os.path.join(output_dir, filename))
        final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
        return final_image
