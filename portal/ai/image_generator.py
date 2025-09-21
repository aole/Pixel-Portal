import importlib
import importlib.util
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import Any, TYPE_CHECKING

from PIL import Image


if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    import torch as torch_module  # noqa: F401


def _import_optional_module(name: str) -> Any | None:
    """Return the imported module when available, otherwise ``None``."""

    spec = importlib.util.find_spec(name)
    if spec is None:
        return None
    return importlib.import_module(name)


torch = _import_optional_module("torch")
_diffusers_module = _import_optional_module("diffusers")
_rembg_module = _import_optional_module("rembg")


PIPELINE_CLASS_NAMES = (
    "StableDiffusionPipeline",
    "StableDiffusionImg2ImgPipeline",
    "StableDiffusionInpaintPipeline",
    "StableDiffusionXLPipeline",
    "StableDiffusionXLImg2ImgPipeline",
    "StableDiffusionXLInpaintPipeline",
)

_PIPELINES: dict[str, Any] = {}
if _diffusers_module is not None:
    for class_name in PIPELINE_CLASS_NAMES:
        _PIPELINES[class_name] = getattr(_diffusers_module, class_name, None)

StableDiffusionPipeline = _PIPELINES.get("StableDiffusionPipeline")
StableDiffusionImg2ImgPipeline = _PIPELINES.get("StableDiffusionImg2ImgPipeline")
StableDiffusionInpaintPipeline = _PIPELINES.get("StableDiffusionInpaintPipeline")
StableDiffusionXLPipeline = _PIPELINES.get("StableDiffusionXLPipeline")
StableDiffusionXLImg2ImgPipeline = _PIPELINES.get("StableDiffusionXLImg2ImgPipeline")
StableDiffusionXLInpaintPipeline = _PIPELINES.get("StableDiffusionXLInpaintPipeline")


rembg_remove = getattr(_rembg_module, "remove", None)
REMBG_AVAILABLE = callable(rembg_remove)


@dataclass(frozen=True)
class DimensionConstraints:
    min_dim: int
    max_dim: int


MODEL_DIMENSION_CONSTRAINTS: dict[str, DimensionConstraints] = {
    "SD1.5": DimensionConstraints(512, 1024),
    "SD15": DimensionConstraints(512, 1024),
    "SDXL": DimensionConstraints(768, 1526),
}


ASPECT_RATIO_DENOMINATOR_LIMIT = 64


def is_torch_available() -> bool:
    return torch is not None


def is_cuda_available() -> bool:
    return bool(
        torch is not None
        and hasattr(torch, "cuda")
        and callable(getattr(torch.cuda, "is_available", None))
        and torch.cuda.is_available()
    )


def is_diffusers_available() -> bool:
    return _diffusers_module is not None and all(
        _PIPELINES.get(name) is not None for name in PIPELINE_CLASS_NAMES
    )


def generation_dependencies_ready() -> bool:
    return is_torch_available() and is_diffusers_available()


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
    def _snap_generation_size(
        desired: tuple[int, int],
        constraints: DimensionConstraints | None,
        multiple: int = 8,
    ) -> tuple[int, int] | None:
        min_dim = constraints.min_dim if constraints else None
        max_dim = constraints.max_dim if constraints else None

        width = max(1, int(desired[0]))
        height = max(1, int(desired[1]))
        width_f = float(width)
        height_f = float(height)

        scale = 1.0
        allow_exceed_max = False
        if min_dim:
            smallest = min(width_f, height_f)
            if smallest < min_dim:
                scale = max(scale, min_dim / smallest)

        scaled_width = width_f * scale
        scaled_height = height_f * scale

        if max_dim:
            largest = max(scaled_width, scaled_height)
            if largest > max_dim:
                reduction = max_dim / largest
                reduced_width = scaled_width * reduction
                reduced_height = scaled_height * reduction
                if min_dim and min(reduced_width, reduced_height) < min_dim - 1e-6:
                    allow_exceed_max = True
                else:
                    scaled_width = reduced_width
                    scaled_height = reduced_height

        if scaled_width <= 0 or scaled_height <= 0:
            return None

        ratio = Fraction(width, height).limit_denominator(
            ASPECT_RATIO_DENOMINATOR_LIMIT
        )
        base_width = ratio.numerator * multiple
        base_height = ratio.denominator * multiple
        if base_width <= 0 or base_height <= 0:
            return None

        base_min = min(base_width, base_height)
        min_multiplier = 1
        if min_dim:
            min_multiplier = max(min_multiplier, math.ceil(min_dim / base_min))

        enforce_max = bool(max_dim) and not allow_exceed_max
        max_multiplier = None
        if enforce_max:
            max_unit = max(base_width, base_height)
            max_multiplier = math.floor(max_dim / max_unit)
            if max_multiplier < min_multiplier:
                enforce_max = False
            else:
                max_multiplier = max(1, max_multiplier)

        width_based = scaled_width / base_width
        height_based = scaled_height / base_height
        candidates = {min_multiplier}
        for value in (width_based, height_based):
            if math.isfinite(value):
                candidates.update(
                    {
                        math.floor(value),
                        math.ceil(value),
                        int(round(value)),
                    }
                )

        if enforce_max and max_multiplier is not None:
            candidates.add(max_multiplier)

        valid: list[tuple[int, int, int]] = []
        for candidate in candidates:
            current = candidate
            if current <= 0:
                continue
            if current < min_multiplier:
                current = min_multiplier
            if enforce_max and max_multiplier is not None and current > max_multiplier:
                continue

            width_candidate = base_width * current
            height_candidate = base_height * current

            if min_dim and min(width_candidate, height_candidate) < min_dim:
                continue
            if enforce_max and max_dim and max(width_candidate, height_candidate) > max_dim:
                continue

            valid.append((width_candidate, height_candidate, current))

        if not valid:
            if allow_exceed_max:
                current = min_multiplier
                return (
                    int(base_width * current),
                    int(base_height * current),
                )
            return None

        def score(option: tuple[int, int, int]) -> float:
            width_candidate, height_candidate, _ = option
            return abs(width_candidate - scaled_width) + abs(height_candidate - scaled_height)

        best_width, best_height, _ = min(valid, key=score)
        return int(best_width), int(best_height)

    def _get_model_constraints(self, model_name: str | None) -> DimensionConstraints | None:
        if not model_name:
            return None
        key = str(model_name).strip().upper()
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
            return fallback or (512, 512)

        normalized = (int(normalized[0]), int(normalized[1]))
        constraints = self._get_model_constraints(model_name)
        snapped = self._snap_generation_size(normalized, constraints)
        if snapped is None:
            return fallback or normalized
        return snapped

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

        if not is_torch_available():
            raise RuntimeError(
                "PyTorch is not installed. Install torch to enable AI image generation."
            )
        if not is_diffusers_available():
            raise RuntimeError(
                "diffusers is not installed or missing required pipelines. Install diffusers to enable AI image generation."
            )

        device = "cuda" if is_cuda_available() else "cpu"
        torch_dtype = torch.float16 if device == "cuda" else torch.float32

        pipeline_params = {
            "torch_dtype": torch_dtype,
            "use_safetensors": True,
        }
        if "clip_skip" in model_cfg:
            pipeline_params["clip_skip"] = model_cfg["clip_skip"]

        pipeline_class = None
        model_key = str(model_name).strip().upper()
        if model_key == "SDXL":
            if is_inpaint:
                pipeline_class = StableDiffusionXLInpaintPipeline
            elif is_img2img:
                pipeline_class = StableDiffusionXLImg2ImgPipeline
            else:
                pipeline_class = StableDiffusionXLPipeline
        elif model_key in {"SD1.5", "SD15"}:
            if is_inpaint:
                pipeline_class = StableDiffusionInpaintPipeline
            elif is_img2img:
                pipeline_class = StableDiffusionImg2ImgPipeline
            else:
                pipeline_class = StableDiffusionPipeline
        else:
            raise ValueError("Invalid model name")

        if pipeline_class is None:
            raise RuntimeError(
                "The requested diffusion pipeline is unavailable. Update diffusers to a version that provides the required pipelines."
            )

        print(f"Loading {model_name} AI pipeline...")
        self.pipe = pipeline_class.from_single_file(
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
            if is_cuda_available() and hasattr(torch.cuda, "empty_cache"):
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
