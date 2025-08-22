import os
import requests
import wx
from src.settings import GetSetting
import threading
import time

def _get_model_paths():
    print("--- Getting model paths ---")

    model_path_from_settings = GetSetting('AI', 'Model')
    lora_path_from_settings = GetSetting('AI', 'Lora')

    print(f"Path from settings (Model): '{model_path_from_settings}'")
    print(f"Path from settings (Lora): '{lora_path_from_settings}'")

    def _normalize_path(path):
        if not path:
            return None
        # This handles both \ and / as separators, making it cross-platform.
        normalized = os.path.join(*path.replace('\\', '/').split('/'))
        print(f"Normalized path '{path}' -> '{normalized}'")
        return normalized

    model_path = _normalize_path(model_path_from_settings)
    lora_path = _normalize_path(lora_path_from_settings)

    if not model_path:
        model_path = os.path.join("models", "sdxl", "juggernautXL_ragnarokBy.safetensors")
        print(f"Model path is empty, using default: '{model_path}'")
    if not lora_path:
        lora_path = os.path.join("models", "lora_sdxl", "pixel-art-xl-v1.1.safetensors")
        print(f"Lora path is empty, using default: '{lora_path}'")

    print(f"Final model path: '{model_path}'")
    print(f"Final lora path: '{lora_path}'")
    print("--------------------------")

    return model_path, lora_path

class DownloadThread(threading.Thread):
    def __init__(self, parent, url, filename, progress_dialog):
        super().__init__()
        self.parent = parent
        self.url = url
        self.filename = filename
        self.progress_dialog = progress_dialog
        self.success = False
        self.cancelled = False

    def run(self):
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)

            headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/octet-stream"}

            with requests.get(self.url, stream=True, headers=headers) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))

                if total_size > 0:
                    wx.CallAfter(self.progress_dialog.SetRange, total_size)

                bytes_downloaded = 0
                chunk_size = 8192
                with open(self.filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if self.cancelled:
                            return
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if total_size > 0:
                                wx.CallAfter(self.progress_dialog.Update, bytes_downloaded)
                            else:
                                wx.CallAfter(self.progress_dialog.Pulse)

            self.success = True
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"Failed to download {self.filename}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        finally:
            if self.progress_dialog.IsShown():
                wx.CallAfter(self.progress_dialog.Destroy)

def DownloadAIModel(parent, url, filename):
    if not url:
        return False

    progress_dialog = wx.ProgressDialog(
        "Downloading",
        f"Downloading {os.path.basename(filename)}",
        parent=parent,
        style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME
    )

    thread = DownloadThread(parent, url, filename, progress_dialog)
    progress_dialog.Show()
    thread.start()

    keep_running = True
    while thread.is_alive() and keep_running:
        wx.Yield()
        if progress_dialog.WasCancelled():
            thread.cancelled = True
            keep_running = False
        time.sleep(0.1)

    return thread.success

def CheckAIModels(parent):
    model_path, lora_path = _get_model_paths()

    model_url = "https://civitai.com/api/download/models/1759168?type=Model&format=SafeTensor"
    lora_url = "https://civitai.com/api/download/models/135931?type=Model&format=SafeTensor"

    if not os.path.exists(model_path):
        if not DownloadAIModel(parent, model_url, model_path):
            return False

    if not os.path.exists(lora_path):
        if not DownloadAIModel(parent, lora_url, lora_path):
            return False

    return True

def GenerateImage(prompt, width, height, num_inference_steps=20):
    model_path, lora_path = _get_model_paths()

    if not os.path.exists(model_path):
        wx.MessageBox("Model file not found. Please set the path in the settings.", "Error", wx.OK | wx.ICON_ERROR)
        return None

    if not os.path.exists(lora_path):
        wx.MessageBox("LoRA file not found. Please set the path in the settings.", "Error", wx.OK | wx.ICON_ERROR)
        return None

    import torch
    from diffusers import StableDiffusionXLPipeline

    try:
        pipe = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=torch.float16, variant="fp16")
        pipe.load_lora_weights(lora_path)
        pipe.to("cuda")

        image = pipe(prompt, width=width*8, height=height*8, num_inference_steps=num_inference_steps).images[0]

        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # create a valid filename from the prompt
        filename = "".join([c for c in prompt if c.isalpha() or c.isdigit() or c.isspace()]).rstrip()
        if len(filename) > 50:
            filename = filename[:50]
        filename = os.path.join(output_dir, f"{filename}.png")

        image.save(filename)

        return filename
    except Exception as e:
        wx.MessageBox(f"Failed to generate image: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return None
