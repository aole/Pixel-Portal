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
        print("[Debug] DownloadThread.run: Starting thread.")
        try:
            print(f"[Debug] Creating directory for {self.filename}")
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)

            headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/octet-stream"}
            print(f"[Debug] Making request to URL: {self.url}")

            with requests.get(self.url, stream=True, headers=headers) as r:
                print(f"[Debug] Request response status: {r.status_code}")
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))
                print(f"[Debug] Content-Length: {total_size}")

                if total_size > 0:
                    wx.CallAfter(self.progress_dialog.SetRange, total_size)

                bytes_downloaded = 0
                chunk_size = 8192
                print("[Debug] Starting download loop...")
                with open(self.filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if self.cancelled or not self.progress_dialog.IsShown():
                            print("[Debug] Download cancelled or dialog closed.")
                            return
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if total_size > 0:
                                wx.CallAfter(self.progress_dialog.Update, bytes_downloaded)
                            else:
                                wx.CallAfter(self.progress_dialog.Pulse)
                print("[Debug] Download loop finished.")

            self.success = True
            print("[Debug] Download successful.")
        except Exception as e:
            print(f"[Debug] An exception occurred: {e}")
            wx.CallAfter(wx.MessageBox, f"Failed to download {self.filename}: {e}", "Error", wx.OK | wx.ICON_ERROR)
        finally:
            print("[Debug] DownloadThread.run: Reached finally block.")
            if self.progress_dialog.IsShown():
                print("[Debug] Destroying progress dialog.")
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

    if not os.path.exists(model_path):
        if not DownloadAIModel(parent, model_url, model_path):
            return False

    if not os.path.exists(lora_path):
        if not DownloadAIModel(parent, lora_url, lora_path):
            return False

    return True
