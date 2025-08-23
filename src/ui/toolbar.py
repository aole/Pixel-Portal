"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

import wx
from wx.adv import BitmapComboBox
from src.ui.canvas import TOOLS

class Toolbar(wx.ToolBar):
    def __init__(self, parent):
        super().__init__(parent)

        self.SetToolBitmapSize((32, 32))

        self.AddToolButton('Clear', parent.OnClear,
                           icon=wx.Bitmap("icons/clear.png"))
        self.AddToolButton('Resize', parent.OnDocResize,
                           icon=wx.Bitmap("icons/resize.png"))

        self.AddToolButton('New', parent.OnNew,
                           icon=wx.Bitmap("icons/new.png"))
        self.AddToolButton('Load', parent.OnOpen,
                           icon=wx.Bitmap("icons/load.png"))
        self.AddToolButton('Save', parent.OnSave,
                           icon=wx.Bitmap("icons/save.png"))
        self.AddToolButton('Gif', parent.OnSaveGif,
                           icon=wx.Bitmap("icons/gif.png"))
        self.AddSeparator()

        self.colorbtn = self.AddToolButton(
            'Foreground Color', parent.OnColorBtn, icon=wx.Bitmap("icons/forecolor.png"))

        # Tool combo box
        bcb = BitmapComboBox(self, style=wx.CB_READONLY)
        for k, v in TOOLS.items():
            bcb.Append(k, wx.Bitmap("icons/"+v[1]))
        self.Bind(wx.EVT_COMBOBOX, parent.OnTool, id=bcb.GetId())
        bcb.SetSelection(0)
        self.AddControl(bcb)

        # Gradient editor
        gbtn = wx.BitmapButton(self, bitmap=wx.Bitmap("icons/gradient.png"))
        self.Bind(wx.EVT_BUTTON, parent.OnGradientBtn, id=gbtn.GetId())
        self.AddControl(gbtn)

        self.AddToggleButton('Grid', parent.OnToggleGrid,
                             icon=wx.Bitmap("icons/grid.png"), default=True)
        self.AddToggleButton('Mirror X', parent.OnMirrorX,
                             icon=wx.Bitmap("icons/mirrorx.png"))
        self.AddToggleButton('Mirror Y', parent.OnMirrorY,
                             icon=wx.Bitmap("icons/mirrory.png"))
        self.AddToggleButton('Smooth Line', parent.OnSmoothLine,
                             icon=wx.Bitmap("icons/smooth.png"))
        self.AddToolButton('Center', parent.OnCenter,
                           icon=wx.Bitmap("icons/center.png"))

        self.Realize()

    def AddToggleButton(self, label, function, icon, default=False):
        btn = self.AddCheckTool(wx.ID_ANY, label, icon, shortHelp=label)
        self.ToggleTool(btn.GetId(), default)
        self.GetParent().Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn

    def AddToolButton(self, label, function, icon):
        btn = self.AddTool(wx.ID_ANY, label, icon, shortHelp=label)
        self.GetParent().Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn

    def SetColor(self, color):
        bitmap = self.colorbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        gc = wx.GraphicsContext.Create(mdc)

        clip = wx.Region(0, 0, 32, 32)
        clip.Subtract(wx.Rect(9, 9, 14, 14))

        gc.Clip(clip)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        gc.SetPen(wx.NullPen)
        gc.DrawRectangle(0, 0, 32, 32)

        mdc.SelectObject(wx.NullBitmap)
        del mdc

        self.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)
