import os
import requests
import wx
from settings import GetSetting

def DownloadAIModel(parent, url, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))

            progress_dialog = wx.ProgressDialog(
                "Downloading",
                f"Downloading {os.path.basename(filename)}",
                maximum=total_size,
                parent=parent,
                style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE
            )

            chunk_size = 8192
            bytes_downloaded = 0
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    progress_dialog.Update(bytes_downloaded)

            progress_dialog.Destroy()
            return True
    except Exception as e:
        wx.MessageBox(f"Failed to download {filename}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return False

def CheckAIModels(parent):
    model = GetSetting('AI', 'Model')
    lora = GetSetting('AI', 'Lora')

    model_url = "https://civitai.com/api/download/models/1759168?type=Model&format=SafeTensor&size=full&fp=fp16"
    lora_url = "https://civitai.com/api/download/models/135931?type=Model&format=SafeTensor"

    if not os.path.exists(model):
        if not DownloadAIModel(parent, model_url, model):
            return False

    if not os.path.exists(lora):
        if not DownloadAIModel(parent, lora_url, lora):
            return False

    return True
