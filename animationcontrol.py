"""
animationcontrol.py
Bhupendra Aole
1/23/2020
"""

import wx
import wx.lib.newevent

from layermanager import *

END_FRAME_HANDLE = 0
INFO_BAR_HEIGHT = 20
NUN_LABEL_WIDTH = 30
LABEL_FONT_SIZE = 8

class AnimationPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.startAnimationBlock = 25
        self.horizontalScale = 12
        self.currentFrame = 10
        
        self.SetTotalFrames(24)
        
    def IsEndFrameHandle(self, x, y, margin=10):
        pos = self.startAnimationBlock + self.totalFrames * self.horizontalScale
        return x>=pos and x<pos+margin
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        
        w, h = self.GetClientSize()
        cf = self.currentFrame
        hs = self.horizontalScale
        tf = self.totalFrames
        sab = self.startAnimationBlock
        
        # block for total animation length
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)))
        gc.SetPen(wx.NullPen)
        gc.DrawRectangle(sab, 0, tf*hs, h)
        
        # vertical lines for each frame
        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_ACTIVEBORDER), 1))
        for x in range(sab % hs, w, hs):
            gc.StrokeLine(x, 0, x, h)
        
        # top info text
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)))
        gc.DrawRectangle(0, 0, w, INFO_BAR_HEIGHT)
            # last frame number
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)))
        pos = sab + tf * hs
        mx = NUN_LABEL_WIDTH+NUN_LABEL_WIDTH/2 if cf>tf else NUN_LABEL_WIDTH/2
        if pos+mx>w:
            pos = w-mx
        mx = NUN_LABEL_WIDTH+NUN_LABEL_WIDTH/2 if cf<=tf else NUN_LABEL_WIDTH/2
        if pos-mx<0:
            pos = mx
        gc.DrawRoundedRectangle(pos - NUN_LABEL_WIDTH/2, 0, NUN_LABEL_WIDTH, INFO_BAR_HEIGHT, 5)
        gc.SetFont(wx.Font(LABEL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT), wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT))
        tw, th, td, tel = gc.GetFullTextExtent(str(tf))
        gc.DrawText(str(tf), pos - tw/2, 5)
            # current frame number
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)))
        pos = sab + cf * hs
        mx = NUN_LABEL_WIDTH+NUN_LABEL_WIDTH/2 if cf<=tf else NUN_LABEL_WIDTH/2
        if pos+mx>w:
            pos = w-mx
        mx = NUN_LABEL_WIDTH+NUN_LABEL_WIDTH/2 if cf>tf else NUN_LABEL_WIDTH/2
        if pos-mx<0:
            pos = mx
        gc.DrawRoundedRectangle(pos - NUN_LABEL_WIDTH/2, 0, NUN_LABEL_WIDTH, INFO_BAR_HEIGHT, 5)
        gc.SetFont(wx.Font(LABEL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT), wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        tw, th, td, tel = gc.GetFullTextExtent(str(cf))
        gc.DrawText(str(cf), pos - tw/2, 5)
        
        # all frame numbers bottom bar
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)))
        gc.DrawRectangle(0, h-INFO_BAR_HEIGHT, w, INFO_BAR_HEIGHT)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)))
        gc.DrawRoundedRectangle(sab-10, h-INFO_BAR_HEIGHT, tf*hs+20, INFO_BAR_HEIGHT, 5)
        gc.SetFont(wx.Font(LABEL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT), wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT))
        tw, th, td, tel = gc.GetFullTextExtent('333')
        gap = int(tw / hs)+1
        lstfrm = int((w - sab)/hs)+1
        for f in range(0, lstfrm, gap):
            if f > tf:
                gc.SetFont(wx.Font(LABEL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT), wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            tw, th, td, tel = gc.GetFullTextExtent(str(f))
            gc.DrawText(str(f), sab+f*hs-tw/2, h-15)
        
        # vertical line for current frame
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT), 3))
        x = sab+cf*hs
        gc.StrokeLine(x, INFO_BAR_HEIGHT, x, h-INFO_BAR_HEIGHT)
        
    def Pan(self, dx):
        self.startAnimationBlock += dx
        w, h = self.GetClientSize()
        if self.startAnimationBlock > w-10:
            self.startAnimationBlock = w-10
    
    def SetCurrentFrameAtPosition(self, x, y):
        w, h = self.GetClientSize()
        if y>20 and y<h-20:
            return
        self.currentFrame = max(1, int((x - self.startAnimationBlock)/self.horizontalScale))
        
        self.Refresh()
        
    def SetEndFrameToPosition(self, x, y):
        newf = int((x - self.startAnimationBlock)/self.horizontalScale)
        if newf<2:
            return
        self.SetTotalFrames(newf)
        
    def SetTotalFrames(self, frames):
        self.totalFrames = frames
        self.Refresh()
        
    def ZoomOnPosition(self, x, y, amt):
        ps = self.horizontalScale*self.totalFrames
        if amt>0:
            self.horizontalScale += 1
        else:
            self.horizontalScale = max(3, self.horizontalScale-1)
            
        self.startAnimationBlock -= int((self.horizontalScale*self.totalFrames-ps)*((x - self.startAnimationBlock)/(ps)))
        
class AnimationControl(wx.Window):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.panel = AnimationPanel(self)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.panel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.panel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.panel.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.panel.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(sizer)
        
        self.prevx, self.prevy = 0, 0
        self.grab = None
        
    def OnMouseMove(self, e):
        x, y = e.Position
        if e.middleIsDown:
            self.panel.Pan(x-self.prevx)
            self.panel.Refresh()
        elif e.leftIsDown:
            if self.grab == END_FRAME_HANDLE:
                self.panel.SetEndFrameToPosition(x, y)
            else:
                self.panel.SetCurrentFrameAtPosition(self.prevx, self.prevy)
        elif e.rightIsDown:
            pass
        else:
            if self.panel.IsEndFrameHandle(x, y):
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            
        self.prevx, self.prevy = x, y
        
    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.Position
        self.grab = None
        if self.panel.IsEndFrameHandle(self.prevx, self.prevy):
            self.grab = END_FRAME_HANDLE
        else:
            self.panel.SetCurrentFrameAtPosition(self.prevx, self.prevy)

    def OnLeftUp(self, e):
        self.grab = None
        
    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.Position

    def OnMouseWheel(self, e):
        amt = e.GetWheelRotation()
        self.panel.ZoomOnPosition(*e.Position, amt)
        self.panel.Refresh()
        
    def OnResize(self, e):
        self.panel.Refresh()
        e.Skip()
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Animation Control")
    l = AnimationControl(f)
    f.Show()
    app.MainLoop()
    