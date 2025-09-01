import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
from PIL import Image
import os
from datetime import datetime

def get_pipeline(is_img2img=False, use_lora=False):
    """
    Loads and returns the appropriate Stable Diffusion XL pipeline.
    This function should only be called once per session.
    """
    base_model_filename = r"models\sdxl\juggernautXL_ragnarokBy.safetensors"
    lora_filename = r"models\lora_sdxl\pixel-art-xl-v1.1.safetensors"
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if device == "cuda" else torch.float32

    print("Loading AI pipeline...")
    PipelineClass = StableDiffusionXLImg2ImgPipeline if is_img2img else StableDiffusionXLPipeline
    
    pipe = PipelineClass.from_single_file(
        base_model_filename,
        torch_dtype=torch_dtype,
        use_safetensors=True,
    ).to(device)

    if use_lora:
        print("Loading LoRA...")
        pipe.load_lora_weights(lora_filename)
        print("AI pipeline loaded successfully.")
    
    return pipe

def prompt_to_image(
    pipe: StableDiffusionXLPipeline,
    prompt: str,
    original_size: tuple[int, int],
    num_inference_steps: int = 20,
    guidance_scale: float = 7.0,
    output_dir: str = "output",
) -> Image.Image:
    """Generates an image from a prompt using a pre-loaded pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    print("Generating image from prompt...")
    generated_image = pipe(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
    ).images[0]

    # Save and resize
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{timestamp}.png"
    generated_image.save(os.path.join(output_dir, filename))
    final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
    return final_image

def image_to_image(
    pipe: StableDiffusionXLImg2ImgPipeline,
    input_image: Image.Image,
    prompt: str,
    strength: float = 0.8,
    num_inference_steps: int = 20,
    guidance_scale: float = 7.0,
    output_dir: str = "output",
) -> Image.Image:
    """Generates an image from another image using a pre-loaded pipeline."""
    os.makedirs(output_dir, exist_ok=True)
    original_size = input_image.size

    print("Preparing input image for img2img...")
    model_input_image = input_image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)

    print("Generating image from image...")
    generated_image = pipe(
        prompt=prompt,
        image=model_input_image,
        strength=strength,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
    ).images[0]

    # Save and resize
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{timestamp}.png"
    generated_image.save(os.path.join(output_dir, filename))
    final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)
    return final_image
    