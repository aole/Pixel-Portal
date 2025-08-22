import os
import requests
import wx
from settings import GetSetting
import threading
import time

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
    model_path = GetSetting('AI', 'Model')
    lora_path = GetSetting('AI', 'Lora')

    model_url = "https://civitai.com/api/download/models/1759168?type=Model&format=SafeTensor"
    lora_url = "https://civitai.com/api/download/models/135931?type=Model&format=SafeTensor"

    if model_path and not os.path.exists(model_path):
        if not DownloadAIModel(parent, model_url, model_path):
            return False

    if lora_path and not os.path.exists(lora_path):
        if not DownloadAIModel(parent, lora_url, lora_path):
            return False

    return True
