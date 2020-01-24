"""
layercontrol.py
Bhupendra Aole
1/23/2020
"""

import wx
from layermanager import *

class LayerControl(wx.ScrolledCanvas):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetVirtualSize (150, 150)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.layers = None
        
        self.alphabg = wx.Bitmap("alphabg.png")

    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        
        #gc.DrawBitmap(self.alphabg, GradientControl.PADDING, GradientControl.PADDING, self.width-GradientControl.PADDING2, 45)
        if self.layers:
            y = 0
            for layer in self.layers:
                gc.DrawBitmap(layer, 0, y, 50, 50)
                gc.SetPen(wx.Pen(wx.BLACK))
                gc.DrawRectangle(0, y, w, 50)
                if layer==self.layers.Current():
                    gc.SetPen(wx.Pen(wx.BLUE))
                gc.DrawRectangle(0, y, 50, 50)
                y += 50

    def UpdateLayers(self):
        self.SetVirtualSize(150, self.layers.Count()*50)
        self.SetScrollRate(1, 1)
        self.Refresh()
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Layer Conrol")
    l = LayerControl(f)
    l.layers = LayerManager.CreateDummy(50, 50, 3)
    f.Show()
    app.MainLoop()
    