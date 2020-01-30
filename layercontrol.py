"""
layercontrol.py
Bhupendra Aole
1/23/2020
"""

import wx
import wx.lib.newevent

from layermanager import *

LayerClickedEvent,      EVT_LAYER_CLICKED_EVENT     = wx.lib.newevent.NewEvent()
LayerVisibilityEvent,   EVT_LAYER_VISIBILITY_EVENT  = wx.lib.newevent.NewEvent()
LayerAlphaEvent,        EVT_LAYER_ALPHA_EVENT       = wx.lib.newevent.NewEvent()
LayerDropEvent,         EVT_LAYER_DROP_EVENT        = wx.lib.newevent.NewEvent()

class LayerPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.layers = None
        self.txtBoxLayer = None
        self.highlightSection = -1
        
        self.alphabg = wx.Bitmap("alphabg.png").GetSubBitmap(wx.Rect(0,0,300,300)).ConvertToImage().AdjustChannels(1,1,1, .3).ConvertToBitmap()
        self.bmVisible = wx.Bitmap("icons/visible.png")
        self.bmNotVisible = wx.Bitmap("icons/NA.png")

        self.textctrl = wx.TextCtrl(self, value="layer", pos=(60, 15), size=(100, wx.DefaultCoord), style=wx.TE_PROCESS_ENTER)
        self.textctrl.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
        self.textctrl.Bind(wx.EVT_KILL_FOCUS, self.OnTextEnter)
        self.textctrl.Hide()
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.Clear()
        
        gc = wx.GraphicsContext.Create(dc)
        #gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        #gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        w, h = self.GetClientSize()
        
        border = 2
        if self.layers:
            y = 0
            for layer in self.layers:
                if layer==self.layers.Current():
                    gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)))
                    gc.SetPen(wx.NullPen)
                    gc.DrawRectangle(0, y, w, 50)
                    gc.SetBrush(wx.NullBrush)
                gc.SetPen(wx.Pen(wx.BLACK, 1))
                # draw checkered background
                gc.DrawBitmap(self.alphabg, border, y+border, 50-border*2, 50-border*2)
                # draw the layer
                gc.DrawBitmap(layer, border, y+border, 50-border*2, 50-border*2)
                # print layer name
                if layer==self.layers.Current():
                    gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXHIGHLIGHTTEXT))
                else:
                    gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT), wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT))
                gc.DrawText(layer.name, 60, y+18)
                # draw visibility icon
                if layer.visible:
                    gc.DrawBitmap(self.bmVisible, w-24, y+2, 23, 23)
                else:
                    gc.DrawBitmap(self.bmNotVisible, w-24, y+2, 23, 23)
                
                # draw outline around row
                #gc.DrawRectangle(0, y, w, 50)
                gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW), border))
                gc.StrokeLine(border/2, y+border/2, w-border/2, y+border/2)
                gc.StrokeLine(border/2, y+border/2, border/2, y+50-border/2)
                gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_ACTIVEBORDER), border))
                gc.StrokeLine(border/2, y+50-border/2, w-border/2, y+50-border/2)
                gc.StrokeLine(w-border/2, y+border/2, w-border/2, y+50-border/2)
                # draw outline around layer
                #gc.DrawRectangle(0, y, 50, 50)
                # draw outline around visibility icon
                #gc.DrawRectangle(w-25, y, 25, 25)
                
                y += 50
            
            # draw section between layers when draging
            if self.highlightSection>=0:
                y = self.highlightSection*50
                sh = 12
                if y<0:
                    y=0
                    sh /= 2
                gc.SetPen(wx.NullPen)
                gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)))
                gc.DrawRectangle(0, y-5, w, sh)
                
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
        
    def SetTextBox(self, idx=-1, layer=None, x=0, y=0):
        if not layer:
            if self.textctrl and self.textctrl.Shown:
                self.txtBoxLayer.name = self.textctrl.GetValue()
            self.textctrl.Hide()
                
        self.txtBoxLayer = layer
        w, h = self.GetClientSize()
        if layer and x>60 and x<w-25:
            self.textctrl.SetValue(layer.name)
            self.textctrl.SelectAll()
            self.textctrl.SetPosition(wx.Point(60, idx*50+15))
            self.textctrl.Show()
            self.textctrl.SetFocus()
        
    def OnTextEnter(self, e):
        self.txtBoxLayer.name = self.textctrl.GetValue()
        self.txtBoxLayer = None
        self.textctrl.Hide()
        
class LayerControl(wx.ScrolledWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        
        self.panel = LayerPanel(self)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.panel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.panel.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.panel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        
        self.slider = wx.Slider(self, value=255, maxValue=255)
        self.slider.Bind(wx.EVT_SLIDER, self.OnSlider)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.slider, 0, wx.EXPAND | wx.ALL, 3)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(sizer)
        
        self.FitInside()
        self.SetScrollRate(5,5)
        
        self.grabbedLayer = None
        
    def UpdateLayers(self, layers=None):
        if layers:
            self.panel.UpdateLayers(layers)
            self.slider.SetValue(layers.Current().alpha*255)
            
        self.Refresh()
        
    def OnMouseMove(self, e):
        self.panel.highlightSection = -1
        if e.Dragging() and self.grabbedLayer:
            wx.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            x, y = e.Position
            ry = y/50
            dry = round(y/50)
            if abs(ry-dry)<.15:
                self.panel.highlightSection = dry
            
            self.panel.Refresh()
        else:
            wx.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            
    def OnLeftDown(self, e):
        x, y = e.Position
        self.panel.SetTextBox()
        idx, layer = self.panel.GetLayerAtPosition(x, y)
        self.grabbedLayer = layer
        if layer:
            if self.panel.IsVisibleIcon(idx, x, y):
                evt = LayerVisibilityEvent(layer = layer, index = idx, position = e.Position)
                wx.PostEvent(self, evt)
            else:
                evt = LayerClickedEvent(layer = layer, index = idx, position = e.Position)
                wx.PostEvent(self, evt)
                
        if not self.panel.HasCapture():
            self.panel.CaptureMouse()

    def OnLeftUp(self, e):
        if self.panel.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.panel.ReleaseMouse()

        if self.grabbedLayer and self.panel.highlightSection >=0:
            evt = LayerDropEvent(layer = self.grabbedLayer, position = self.panel.highlightSection)
            wx.PostEvent(self, evt)
        self.grabbedLayer = None
        self.panel.highlightSection = -1
        self.panel.Refresh()
        
    def OnLeftDClick(self, e):
        x, y = e.Position
        idx, layer = self.panel.GetLayerAtPosition(x, y)
        self.panel.SetTextBox(idx, layer, x, y)
        
    def OnSlider(self, e):
        evt = LayerAlphaEvent(alpha = self.slider.Value/255.0)
        wx.PostEvent(self, evt)
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Layer Control")
    l = LayerControl(f)
    l.UpdateLayers(LayerManager.CreateDummy(50, 50, 3))
    f.Show()
    app.MainLoop()
    