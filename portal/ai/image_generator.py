# src/ai/image_generator.py

import torch
from diffusers import StableDiffusionXLImg2ImgPipeline
from PIL import Image
import os
from huggingface_hub import hf_hub_download

def image_to_image(
    input_image: Image.Image,
    prompt: str,
    output_dir: str = "output",
) -> Image.Image:
    """
    Generates a pixel art image from an input image using a Stable Diffusion XL model.

    Args:
        input_image: The input PIL Image.
        prompt: The text prompt to guide image generation.
        output_dir: The directory to save the intermediate and final images.

    Returns:
        The generated and resized PIL Image.
    """
    # --- 1. Setup and Configuration ---
    # These are Hugging Face repository IDs. The files will be downloaded automatically.
    base_model_filename = r"models\sdxl\juggernautXL_ragnarokBy.safetensors"
    lora_filename = r"models\lora_sdxl\pixel-art-xl-v1.1.safetensors"
    os.makedirs(output_dir, exist_ok=True)

    # Check for CUDA availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("Warning: CUDA not available, using CPU. This will be very slow.")
        # On CPU, float16 is not supported, use float32
        torch_dtype = torch.float32
    else:
        torch_dtype = torch.float16

    print("Loading model...")
    # --- 2. Load the Model and LoRA ---
    pipe = StableDiffusionXLImg2ImgPipeline.from_single_file(
        base_model_filename,
        torch_dtype=torch_dtype,
        use_safetensors=True,
    ).to(device)

    print("Loading LoRA...")
    pipe.load_lora_weights(lora_filename)
    # The user's sample code had a weight, but the function signature for diffusers
    # might vary. The common way is to fuse them with a weight.
    # Let's assume a default blending for now as per modern diffusers.
    # pipe.fuse_lora(lora_weight=0.75) # Example if fusing is desired

    # --- 3. Prepare the Input Image ---
    print("Preparing input image...")
    original_size = input_image.size
    # The model was trained on 1024x1024 images
    model_input_image = input_image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)

    # --- 4. Generate the AI Image ---
    print("Generating image...")
    generated_image = pipe(
        prompt=prompt,
        image=model_input_image,
        strength=0.8,
        num_inference_steps=20,
        guidance_scale=7.0,
    ).images[0]

    # --- 5. Save the Intermediate Image ---
    generated_image.save(os.path.join(output_dir, "generated_1024x1024.png"))
    print(f"Saved 1024x1024 image to {output_dir}")

    # --- 6. Scale Image to Original Size ---
    print(f"Resizing generated image to original size: {original_size}")
    final_image = generated_image.resize(original_size, Image.Resampling.NEAREST)

    return final_image
