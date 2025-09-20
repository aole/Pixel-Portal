import json
import math
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


MODEL_DIMENSION_CONSTRAINTS: dict[str, tuple[int, int]] = {
    "SD1.5": (512, 1024),
    "SDXL": (768, 1526),
}


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

    @staticmethod
    def _calculate_step_for_ratio(ratio_width: int, ratio_height: int, multiple: int = 8) -> int:
        """Return the multiplier that keeps the ratio while snapping to `multiple`."""

        ratio_width = max(1, int(ratio_width))
        ratio_height = max(1, int(ratio_height))
        gcd_width = math.gcd(ratio_width, multiple)
        gcd_height = math.gcd(ratio_height, multiple)
        width_factor = multiple // gcd_width
        height_factor = multiple // gcd_height
        return math.lcm(width_factor, height_factor)

    def _get_model_constraints(self, model_name: str | None) -> tuple[int, int] | None:
        if not model_name:
            return None
        key = str(model_name).upper()
        return MODEL_DIMENSION_CONSTRAINTS.get(key)

    def calculate_generation_size(
        self,
        model_name: str,
        desired_size: tuple[int, int] | None,
    ) -> tuple[int, int]:
        """Derive a native generation size that respects model limits."""

        fallback = self.get_generation_size(model_name)
        normalized = self._coerce_size(desired_size)
        if normalized is None:
            return fallback

        width, height = normalized
        width = max(1, int(width))
        height = max(1, int(height))

        constraints = self._get_model_constraints(model_name)
        if constraints:
            min_dim, max_dim = constraints
        else:
            min_dim = max_dim = None

        width_f = float(width)
        height_f = float(height)
        scale = 1.0

        if min_dim:
            smallest = min(width_f, height_f)
            if smallest < min_dim:
                scale = min_dim / smallest

        scaled_width = width_f * scale
        scaled_height = height_f * scale

        allow_exceed_max = False
        if max_dim:
            largest = max(scaled_width, scaled_height)
            if largest > max_dim:
                reduction = max_dim / largest
                candidate_width = scaled_width * reduction
                candidate_height = scaled_height * reduction
                if min_dim and min(candidate_width, candidate_height) < min_dim - 1e-6:
                    allow_exceed_max = True
                else:
                    scale *= reduction
                    scaled_width = candidate_width
                    scaled_height = candidate_height

        target_width = scaled_width
        target_height = scaled_height

        ratio_gcd = math.gcd(width, height)
        ratio_width = width // ratio_gcd
        ratio_height = height // ratio_gcd

        step = self._calculate_step_for_ratio(ratio_width, ratio_height)
        width_unit = ratio_width * step
        height_unit = ratio_height * step
        if width_unit <= 0 or height_unit <= 0:
            return fallback

        min_unit = min(width_unit, height_unit)
        max_unit = max(width_unit, height_unit)

        required_multiplier = 1
        if min_dim:
            required_multiplier = max(required_multiplier, math.ceil(min_dim / min_unit))

        approx_multiplier = target_width / width_unit if width_unit else target_height / height_unit
        if approx_multiplier <= 0:
            approx_multiplier = float(required_multiplier)

        multiplier = max(required_multiplier, int(round(approx_multiplier)))
        if multiplier < 1:
            multiplier = required_multiplier

        enforce_max = bool(max_dim) and not allow_exceed_max
        if enforce_max:
            max_multiplier = max(1, math.floor(max_dim / max_unit))
            if max_multiplier < required_multiplier:
                multiplier = required_multiplier
                enforce_max = False
            elif multiplier > max_multiplier:
                multiplier = max_multiplier

        final_width = width_unit * multiplier
        final_height = height_unit * multiplier

        if min_dim and min(final_width, final_height) < min_dim:
            multiplier = max(multiplier, math.ceil(min_dim / min_unit))
            final_width = width_unit * multiplier
            final_height = height_unit * multiplier

        if enforce_max and max_dim and max(final_width, final_height) > max_dim:
            max_multiplier = max(1, math.floor(max_dim / max_unit))
            multiplier = max_multiplier
            final_width = width_unit * multiplier
            final_height = height_unit * multiplier

        if final_width <= 0 or final_height <= 0:
            return fallback

        return int(final_width), int(final_height)

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
        generation_size: tuple[int, int] | None = None,
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

        coerced_generation_size = self._coerce_size(generation_size)
        if coerced_generation_size is None:
            coerced_generation_size = self.get_generation_size(self.current_model) or (512, 512)

        pipe_kwargs = {
            "prompt": prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "callback_on_step_end": callback,
        }
        if coerced_generation_size:
            pipe_kwargs["width"], pipe_kwargs["height"] = coerced_generation_size

        print("Generating image from prompt...")
        generated_image = self.pipe(**pipe_kwargs).images[0]

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
        generation_size: tuple[int, int] | None = None,
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

        target_generation_size = self._coerce_size(generation_size)
        if target_generation_size is None:
            target_generation_size = self.get_generation_size(self.current_model) or (512, 512)

        print("Preparing input image for img2img...")
        model_input_image = input_image.convert("RGB").resize(
            target_generation_size,
            Image.Resampling.NEAREST,
        )

        print("Generating image from image...")
        pipe_kwargs = {
            "prompt": prompt,
            "image": model_input_image,
            "strength": strength,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "callback_on_step_end": callback,
        }
        if target_generation_size:
            pipe_kwargs["width"], pipe_kwargs["height"] = target_generation_size

        generated_image = self.pipe(**pipe_kwargs).images[0]

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
        generation_size: tuple[int, int] | None = None,
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

        target_generation_size = self._coerce_size(generation_size)
        if target_generation_size is None:
            target_generation_size = self.get_generation_size(self.current_model) or (512, 512)

        print("Preparing input image for inpainting...")
        model_input_image = input_image.convert("RGB").resize(
            target_generation_size,
            Image.Resampling.NEAREST,
        )
        mask_image = mask_image.convert("RGB").resize(
            target_generation_size,
            Image.Resampling.NEAREST,
        )

        print("Generating image from image...")
        pipe_kwargs = {
            "prompt": prompt,
            "image": model_input_image,
            "mask_image": mask_image,
            "strength": strength,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "callback_on_step_end": callback,
        }
        if target_generation_size:
            pipe_kwargs["width"], pipe_kwargs["height"] = target_generation_size

        generated_image = self.pipe(**pipe_kwargs).images[0]

        if remove_background:
            generated_image = self._remove_background(generated_image)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"
        generated_image.save(os.path.join(output_dir, filename))
        final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
        return final_image
