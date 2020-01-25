"""
layercontrol.py
Bhupendra Aole
1/23/2020
"""

import wx
from layermanager import *

class LayerPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.layers = None
        
        self.alphabg = wx.Bitmap("alphabg.png")

    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        
        if self.layers:
            y = 0
            for layer in self.layers:
                gc.DrawBitmap(self.alphabg, 0, y, 50, 50)
                gc.DrawBitmap(layer, 0, y, 50, 50)
                gc.SetPen(wx.Pen(wx.BLACK))
                gc.DrawRectangle(0, y, w, 50)
                if layer==self.layers.Current():
                    gc.SetPen(wx.Pen(wx.BLUE))
                gc.DrawRectangle(0, y, 50, 50)
                y += 50

    def UpdateLayers(self, layers):
        print('minsize:', layers.Count())
        self.SetMinSize(wx.Size(150, layers.Count()*50))
        self.layers = layers
        self.Refresh()
        
class LayerControl(wx.ScrolledWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = LayerPanel(self)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 3)
        
        self.SetSizer(sizer)
        
        self.FitInside()
        self.SetScrollRate(5,5)
        
    def UpdateLayers(self, layers=None):
        if layers:
            self.panel.UpdateLayers(layers)
        self.Refresh()
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Layer Control")
    l = LayerControl(f)
    l.UpdateLayers(LayerManager.CreateDummy(50, 50, 3))
    f.Show()
    app.MainLoop()
    