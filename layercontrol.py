"""
layercontrol.py
Bhupendra Aole
1/23/2020
"""

import wx
import wx.lib.newevent

from layermanager import *

LayerClickedEvent, EVT_LAYER_CLICKED_EVENT = wx.lib.newevent.NewEvent()
LayerVisibilityEvent, EVT_LAYER_VISIBILITY_EVENT = wx.lib.newevent.NewEvent()

class LayerPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.layers = None
        
        self.alphabg = wx.Bitmap("alphabg.png").GetSubBitmap(wx.Rect(0,0,300,300))
        self.bmVisible = wx.Bitmap("icons/visible.png")

    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        w, h = self.GetClientSize()
        
        if self.layers:
            y = 0
            for layer in self.layers:
                # draw checkered background
                gc.DrawBitmap(self.alphabg, 0, y, 50, 50)
                # draw the layer
                gc.DrawBitmap(layer, 0, y, 50, 50)
                # draw visibility icon
                if layer.visible:
                    gc.DrawBitmap(self.bmVisible, w-25, y, 25, 25)
                
                # if the layer is selected use thick pen
                gc.SetPen(wx.Pen(wx.BLACK, 1))
                if layer==self.layers.Current():
                    gc.SetPen(wx.Pen(wx.BLACK, 3))
                # draw outline around layer
                gc.DrawRectangle(0, y, w, 50)
                gc.SetPen(wx.Pen(wx.BLACK, 1))
                gc.DrawRectangle(0, y, 50, 50)
                gc.DrawRectangle(w-25, y, 25, 25)
                
                y += 50

    def UpdateLayers(self, layers):
        self.SetMinSize(wx.Size(150, layers.Count()*50))
        self.layers = layers
        self.Refresh()
       
    def GetLayerAtPosition(self, x, y):
        idx = int(y / 50)
        if idx<self.layers.Count():
            return idx, self.layers[idx]
        return -1, None
        
    def IsVisibleIcon(self, index, x, y):
        w, h = self.GetClientSize()
        y -= index*50
        return x>w-25 and y<25
        
class LayerControl(wx.ScrolledWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        
        self.panel = LayerPanel(self)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(sizer)
        
        self.FitInside()
        self.SetScrollRate(5,5)
        
    def UpdateLayers(self, layers=None):
        if layers:
            self.panel.UpdateLayers(layers)
        self.Refresh()
        
    def OnLeftDown(self, e):
        x, y = e.Position
        idx, layer = self.panel.GetLayerAtPosition(x, y)
        if layer:
            if self.panel.IsVisibleIcon(idx, x, y):
                evt = LayerVisibilityEvent(layer = layer, index = idx, position = e.Position)
                wx.PostEvent(self, evt)
            else:
                evt = LayerClickedEvent(layer = layer, index = idx, position = e.Position)
                wx.PostEvent(self, evt)
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Layer Control")
    l = LayerControl(f)
    l.UpdateLayers(LayerManager.CreateDummy(50, 50, 3))
    f.Show()
    app.MainLoop()
    