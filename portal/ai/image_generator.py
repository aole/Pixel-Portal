import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, StableDiffusionPipeline, StableDiffusionImg2ImgPipeline
from PIL import Image
import os
from datetime import datetime


def get_pipeline(model_name="SD1.5", is_img2img=False):
    """
    Loads and returns the appropriate Stable Diffusion pipeline.
    This function should only be called once per session.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if device == "cuda" else torch.float32

    print(f"Loading {model_name} AI pipeline...")

    pipeline_params = {
        "torch_dtype": torch_dtype,
        "use_safetensors": True,
    }

    if model_name == "SDXL":
        base_model_filename = r"models/sdxl/juggernautXL_ragnarokBy.safetensors"
        PipelineClass = StableDiffusionXLImg2ImgPipeline if is_img2img else StableDiffusionXLPipeline

    elif model_name == "SD1.5":
        base_model_filename = r"models/sd1.5/aziibpixelmix_v10.safetensors"
        PipelineClass = StableDiffusionImg2ImgPipeline if is_img2img else StableDiffusionPipeline
        pipeline_params["clip_skip"] = 2

    else:
        raise ValueError("Invalid model name")
    
    pipe = PipelineClass.from_single_file(
        base_model_filename,
        **pipeline_params
    ).to(device)

    print("AI pipeline loaded successfully.")
    
    return pipe

def prompt_to_image(
    pipe: object,
    prompt: str,
    original_size: tuple[int, int],
    num_inference_steps: int = 20,
    guidance_scale: float = 7.0,
    output_dir: str = "output",
    step_callback=None,
) -> Image.Image:
    """Generates an image from a prompt using a pre-loaded pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    def callback(pipe, step_index, timestep, callback_kwargs):
        if step_callback:
            # convert latents to image
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
    generated_image = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        callback_on_step_end=callback if step_callback else None,
    ).images[0]

    # Save and resize
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{timestamp}.png"
    generated_image.save(os.path.join(output_dir, filename))
    final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
    return final_image

def image_to_image(
    pipe: object,
    input_image: Image.Image,
    prompt: str,
    strength: float = 0.8,
    num_inference_steps: int = 20,
    guidance_scale: float = 7.0,
    output_dir: str = "output",
    step_callback=None,
) -> Image.Image:
    """Generates an image from another image using a pre-loaded pipeline."""
    os.makedirs(output_dir, exist_ok=True)
    original_size = input_image.size

    def callback(pipe, step_index, timestep, callback_kwargs):
        if step_callback:
            # convert latents to image
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
    if isinstance(pipe, StableDiffusionXLImg2ImgPipeline):
        model_input_image = input_image.convert("RGB").resize((1024, 1024), Image.Resampling.NEAREST)
    else:
        model_input_image = input_image.convert("RGB").resize((512, 512), Image.Resampling.NEAREST)

    print("Generating image from image...")
    generated_image = pipe(
        prompt=prompt,
        image=model_input_image,
        strength=strength,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        callback_on_step_end=callback if step_callback else None,
    ).images[0]

    # Save and resize
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{timestamp}.png"
    generated_image.save(os.path.join(output_dir, filename))
    final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
    return final_image
    