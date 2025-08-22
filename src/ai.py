import os
import requests
import wx
from settings import GetSetting
import threading
import time

def get_civitai_download_url(model_id):
    try:
        api_url = f"https://civitai.com/api/v1/models/{model_id}"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        latest_version = data['modelVersions'][0]
        file_info = latest_version['files'][0]

        return file_info['downloadUrl']
    except Exception as e:
        wx.CallAfter(wx.MessageBox, f"Failed to get download URL for model {model_id}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return None

class DownloadThread(threading.Thread):
    def __init__(self, parent, url, filename, progress_dialog):
        threading.Thread.__init__(self)
        self.parent = parent
        self.url = url
        self.filename = filename
        self.progress_dialog = progress_dialog
        self.success = False

    def run(self):
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with requests.get(self.url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))

                if total_size > 0:
                    wx.CallAfter(self.progress_dialog.SetRange, total_size)

                chunk_size = 8192
                bytes_downloaded = 0
                with open(self.filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if not self.progress_dialog.IsShown():
                            return
                        f.write(chunk)

                        if total_size > 0:
                            bytes_downloaded += len(chunk)
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
    thread.start()

    while thread.is_alive():
        wx.Yield()
        time.sleep(0.1)

    return thread.success

def CheckAIModels(parent):
    model_path = GetSetting('AI', 'Model')
    lora_path = GetSetting('AI', 'Lora')

    # Model IDs from original issue description
    model_id = "1759168"
    lora_id = "135931"

    if not os.path.exists(model_path):
        model_url = get_civitai_download_url(model_id)
        if not DownloadAIModel(parent, model_url, model_path):
            return False

    if not os.path.exists(lora_path):
        lora_url = get_civitai_download_url(lora_id)
        if not DownloadAIModel(parent, lora_url, lora_path):
            return False

    return True
