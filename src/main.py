"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""
import wx

from .settings import (
    InitSettings,
    LoadSettings
)
from .ui.mainframe import Frame

app = None

def CreateWindows():
    global app

    app = wx.App()

    InitSettings()
    LoadSettings('settings.ini')

    Frame().Show()


def RunProgram():
    app.MainLoop()


CreateWindows()
RunProgram()
