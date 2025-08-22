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

def main():
    app = wx.App()
    InitSettings()
    LoadSettings('settings.ini')
    frame = Frame()
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
