"""
gradienteditor.py
Bhupendra Aole
1/23/2020
"""

import wx
from wx.lib.agw.cubecolourdialog import CubeColourDialog

class GradientStop(wx.GraphicsGradientStop):
    def __init__(self, color, pos):
        super().__init__(color, pos)
        self.active = True
        
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
        
        if not stops:
            stops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
            stops.Add(GradientStop(wx.BLACK, 0))
            stops.Add(GradientStop(wx.WHITE, 1))
        self.stops = stops
        
        self.markers = [GradientStop(stops.StartColour, 0), GradientStop(stops.EndColour, 1)]
        for stop in range(1, stops.Count-1):
            self.markers.append(stops[stop])
            
        self.alphabg = wx.Bitmap("alphabg.png")

    def UpdateStops(self):
        minm = (2, None)
        maxm = (-1, None)
        for marker in self.markers[2:]:
            if isinstance(marker, GradientStop) and not marker.active:
                continue
            if marker.Position < minm[0]:
                minm = (marker.Position, marker.Colour)
            if marker.Position > maxm[0]:
                maxm = (marker.Position, marker.Colour)
            
        self.stops = wx.GraphicsGradientStops(minm[1], maxm[1])
        for marker in self.markers[2:]:
            if isinstance(marker, GradientStop) and not marker.active:
                continue
            self.stops.Add(marker)
            
    def MarkerUnderLocation(self, mx, my):
        for marker in self.markers[2:]:
            x = int((self.width-GradientControl.PADDING2) * marker.Position + GradientControl.PADDING)
            y = 75
            r = wx.Rect(x-4, y-6, 8, 25)
            if r.Contains(mx, my):
                return marker
                
        return None
        
    def SetMarkerLocation(self, marker, x, y):
        if x<0 or x>self.width or y<0 or y>self.height and len(self.markers)>4:
            marker.active = False
        else:
            marker.active = True
            px = max(GradientControl.PADDING, min(x, self.width-GradientControl.PADDING)) - GradientControl.PADDING
            px /= self.width-GradientControl.PADDING2
            marker.SetPosition(px)
        
    def DrawMarker(self, gc, x, y, highlight=False):
        if highlight:
            gc.SetPen(wx.Pen(wx.Colour(250,250,250), 3))
        else:
            gc.SetPen(wx.Pen(wx.Colour(50,50,50), 2))
        gc.StrokeLine(x, y-4, x, y+4)
        
        gc.DrawRoundedRectangle(x-3, y+8, 6, 8, 3)
        
    def RemoveUnactiveMarkers(self):
        self.markers = [x for x in self.markers if not isinstance(x, GradientStop) or x.active]
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)

        gc.DrawBitmap(self.alphabg, GradientControl.PADDING, GradientControl.PADDING, self.width-GradientControl.PADDING2, 45)
        
        gc.SetPen(wx.Pen(wx.BLACK, 5))
        gc.StrokeLine(GradientControl.PADDING, 75, self.width-GradientControl.PADDING, 75)
        
        for marker in self.markers[2:]:
            if isinstance(marker, GradientStop) and not marker.active:
                continue
            x = (self.width-GradientControl.PADDING2)*marker.Position + GradientControl.PADDING
            self.DrawMarker(gc, x, 75, marker==self.dragging)
        
        brush = gc.CreateLinearGradientBrush(GradientControl.PADDING, 0, self.width-GradientControl.PADDING, 0, self.stops)
        gc.SetBrush(brush)
        gc.SetPen(wx.NullPen)
        gc.DrawRectangle(GradientControl.PADDING, GradientControl.PADDING, self.width-GradientControl.PADDING2, 45)
        
    def GetStops(self):
        return self.stops
        
    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        if self.left_down and self.dragging:
            self.SetMarkerLocation(self.dragging, x, y)
            self.UpdateStops()
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
        self.RemoveUnactiveMarkers()
        
    def OnLeftDClick(self, e):
        x, y = e.GetPosition()
        if self.prevx==x and self.prevy==y:
            marker = self.MarkerUnderLocation(x, y)
            if marker:
                data = wx.ColourData()
                data.SetColour(marker.Colour)
                dlg = CubeColourDialog(self, data)
                if dlg.ShowModal() == wx.ID_OK:
                    color = dlg.GetColourData().GetColour()
                    marker.SetColour(color)
            else: # add new marker
                if x <= self.width-GradientControl.PADDING and x>=GradientControl.PADDING:
                    pos = (x-GradientControl.PADDING) / (self.width-GradientControl.PADDING2)
                    # find markers before and after pos to interpolate
                    bef = None
                    aft = None
                    for marker in self.markers:
                        if marker.Position<=pos and (not bef or marker.Position>bef.Position):
                            bef = marker
                        if marker.Position>=pos and (not aft or marker.Position<aft.Position):
                            aft = marker
                            
                    # interpolate before and after color
                    w = aft.Position - bef.Position
                    ip = (pos-bef.Position)/w
                    icr = int(bef.Colour.red+(aft.Colour.red - bef.Colour.red)*ip)
                    icg = int(bef.Colour.green+(aft.Colour.green - bef.Colour.green)*ip)
                    icb = int(bef.Colour.blue+(aft.Colour.blue - bef.Colour.blue)*ip)
                    ica = int(bef.Colour.alpha+(aft.Colour.alpha - bef.Colour.alpha)*ip)
                    stop = GradientStop(wx.Colour(icr, icg, icb, ica), pos)
                    
                    self.markers.append(stop)
                    
        self.UpdateStops()
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
    ge = GradientEditor()
    ge.ShowModal()
    stops = ge.GetStops()
    for i in range(stops.GetCount()):
        stop = stops[i]
        print(str(i+1), round(stop.Position,1), stop.Colour)
        