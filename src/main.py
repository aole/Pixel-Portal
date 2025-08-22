"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""
import sys
import os
import wx

# Add the project root to the Python path
# This allows for absolute imports from the 'src' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.settings import (
    InitSettings,
    LoadSettings
)
from src.ui.mainframe import Frame

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
