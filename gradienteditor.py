"""
gradienteditor.py
Bhupendra Aole
1/23/2020
"""

import wx
from wx.lib.agw.cubecolourdialog import CubeColourDialog

class GradientControl(wx.Window):
    PADDING = 10
    PADDING2 = PADDING*2
    
    def __init__(self, parent=None, stops=None):
        super().__init__(parent)
        
        self.width = 300
        self.height = 100
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize(wx.Size(self.width, self.height))
        
        self.prevx, self.prevy = 0, 0
        self.left_down = False
        self.dragging = None
        
        self.stops = stops if stops else wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        self.markers = [wx.GraphicsGradientStop(wx.BLACK, 0), wx.GraphicsGradientStop(wx.WHITE, 1)]
        
    def MarkerUnderLocation(self, mx, my):
        for marker in self.markers:
            x = (self.width-GradientControl.PADDING2) * marker.Position + GradientControl.PADDING
            y = 75
            r = wx.Rect(x-3, y+8, 6, 8)
            if r.Contains(mx, my):
                return marker
                
        return None
        
    def SetMarkerLocation(self, marker, x, y):
        px = max(GradientControl.PADDING, min(x, self.width-GradientControl.PADDING)) - GradientControl.PADDING
        px /= self.width-GradientControl.PADDING2
        marker.SetPosition(px)
        
    def DrawMarker(self, gc, color, x, y, highlight=False):
        if highlight:
            gc.SetPen(wx.Pen(wx.Colour(250,250,250), 3))
        else:
            gc.SetPen(wx.Pen(wx.Colour(50,50,50), 2))
        gc.StrokeLine(x, y-4, x, y+4)
        
        gc.SetPen(wx.Pen(color, 2))
        gc.DrawRoundedRectangle(x-3, y+8, 6, 8, 3)
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)

        gc.SetPen(wx.Pen(wx.BLACK, 5))
        gc.StrokeLine(GradientControl.PADDING, 75, self.width-GradientControl.PADDING, 75)
        
        stops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        for marker in self.markers:
            stops.Add(marker)
            x = (self.width-GradientControl.PADDING2)*marker.Position + GradientControl.PADDING
            self.DrawMarker(gc, marker.Colour, x, 75, marker==self.dragging)
        
        brush = gc.CreateLinearGradientBrush(GradientControl.PADDING, 0, self.width-GradientControl.PADDING, 0, stops)
        gc.SetBrush(brush)
        gc.SetPen(wx.NullPen)
        gc.DrawRoundedRectangle(GradientControl.PADDING, GradientControl.PADDING, self.width-GradientControl.PADDING2, 45, 5)
        
    def GetStops(self):
        stops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        for marker in self.markers:
            stops.Add(marker)
        
        return stops
        
    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        if self.left_down and self.dragging:
            self.SetMarkerLocation(self.dragging, x, y)
            self.Refresh()
        self.prevx, self.prevy = x, y
        
    def OnLeftDown(self, e):
        x, y = e.GetPosition()
        self.prevx, self.prevy = x, y
        
        self.dragging = self.MarkerUnderLocation(x, y)
        self.left_down = True
        
        if not self.HasCapture():
            self.CaptureMouse()
            
        self.Refresh()

    def OnLeftUp(self, e):
        self.dragging = None
        self.left_down = False
        
        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()
            
        self.Refresh()

    def OnLeftDClick(self, e):
        x, y = e.GetPosition()
        if self.prevx==x and self.prevy==y:
            marker = self.MarkerUnderLocation(x, y)
            data = wx.ColourData()
            data.SetColour(marker.Colour)
            dlg = CubeColourDialog(self, data)
            if dlg.ShowModal() == wx.ID_OK:
                color = dlg.GetColourData().GetColour()
                marker.SetColour(color)
        
        self.Refresh()
        
class GradientEditor(wx.Dialog):
    def __init__(self, parent=None, stops=None):
        super().__init__(parent, title="Gradient Editor")
        
        sizer = wx.GridBagSizer(5,5)
        
        self.gc = GradientControl(self, stops)
        sizer.Add(self.gc, pos=(0,0), span=(1,3))
        
        b = wx.Button(self, wx.ID_OK)
        sizer.Add(b, pos=(1,1))
        
        b = wx.Button(self, wx.ID_CANCEL)
        sizer.Add(b, pos=(1,2))
        
        self.SetSizerAndFit(sizer)

    def GetStops(self):
        return self.gc.GetStops()
        
if __name__ == '__main__':
    app = wx.App()
    print(GradientEditor().ShowModal())
    