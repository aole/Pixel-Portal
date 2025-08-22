import os
import requests
import wx
from settings import GetSetting
import threading

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

                wx.CallAfter(self.progress_dialog.SetRange, total_size)

                chunk_size = 8192
                bytes_downloaded = 0
                with open(self.filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if not self.progress_dialog.IsShown():
                            # Dialog was cancelled
                            return

                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        wx.CallAfter(self.progress_dialog.Update, bytes_downloaded)

            self.success = True
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"Failed to download {self.filename}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        finally:
            if self.progress_dialog.IsShown():
                wx.CallAfter(self.progress_dialog.Destroy)

def DownloadAIModel(parent, url, filename):
    progress_dialog = wx.ProgressDialog(
        "Downloading",
        f"Downloading {os.path.basename(filename)}",
        parent=parent,
        style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT
    )

    thread = DownloadThread(parent, url, filename, progress_dialog)
    thread.start()

    progress_dialog.ShowModal()

    thread.join()

    return thread.success

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
