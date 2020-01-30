"""
animationcontrol.py
Bhupendra Aole
1/23/2020
"""

from random import randrange

import wx
import wx.lib.newevent

from layermanager import *

END_FRAME_HANDLE = 0
INFO_BAR_HEIGHT = 20
NUN_LABEL_WIDTH = 30
LABEL_FONT_SIZE = 8
MIN_MARKER_SIZE = 20

FrameChangedEvent,      EVT_FRAME_CHANGED_EVENT     = wx.lib.newevent.NewEvent()

class PlayTimer(wx.Timer):
    def __init__(self, parent=None):
        super().__init__()
        
        self.parent = parent

    def Notify(self):
        self.parent.NextFrame()
        
class AnimationPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.startAnimationBlock = 25
        self.horizontalScale = 12
        self.currentFrame = 10
        self.fps = 8
        self.highlightedSlot = [0, 0, 0] # frame | slot | of num slots
        self.selectedSlot = [1, 0, 1]
        
        self.keys = {}
        self.SetTotalFrames(24)
        self.playTimer = PlayTimer(self)
        
    def GetFrameFromPosition(self, x, y):
        return int((x - self.startAnimationBlock)/self.horizontalScale) + 1
        
    def GetKey(self, frame):
        f = frame
        while not f in self.keys and f>0:
            f -= 1
        if f in self.keys:
            return self.keys[f]
        return None
        
    def HighlightSlotFromPosition(self, x, y):
        w, h = self.GetClientSize()
        self.UnSetHighlightedSlot()
        
        if y < INFO_BAR_HEIGHT or y > h-INFO_BAR_HEIGHT:
            return
        f = self.GetFrameFromPosition(x, y)
        if f<=0 or f>=self.totalFrames:
            return
            
        self.highlightedSlot[0] = f
        if not f in self.keys:
            self.highlightedSlot[2] = 1
        else:
            h -= INFO_BAR_HEIGHT*2
            y -= INFO_BAR_HEIGHT
            key = self.keys[f]
            self.highlightedSlot[2] = len(key)+1
            self.highlightedSlot[1] = int(y/(h/self.highlightedSlot[2]))
            
    def InsertKey(self, key):
        if self.selectedSlot[2]:
            if self.selectedSlot[2]<2:
                self.keys[self.selectedSlot[0]] = [key]
            else:
                self.keys[self.selectedSlot[0]].insert(self.selectedSlot[1], key)
            self.selectedSlot[2] += 1
            
            self.Refresh()
        else:
            print('Error: No selected slot!')
            
    def IsEndFrameHandle(self, x, y, margin=10):
        pos = self.startAnimationBlock + self.totalFrames * self.horizontalScale
        return x>=pos and x<pos+margin
        
    def NextFrame(self):
        nf = 1 if self.currentFrame>=self.totalFrames else self.currentFrame+1
        self.SetCurrentFrame(nf)
        
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
        
        # keys
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        gc.SetPen(wx.NullPen)
        for f, key in self.keys.items():
            fi = f - 1
            numslots = len(key)
            sh = (h-INFO_BAR_HEIGHT*2)/numslots
            y = INFO_BAR_HEIGHT
            for i in range(numslots):
                gc.DrawRoundedRectangle(sab+fi*hs+2, y, hs-4, sh, 5)
                y += sh
            
        # selected slot
        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT), 1))
        if self.selectedSlot[2]>0:
            x = sab + (self.selectedSlot[0]-1) * hs
            sh = (h - INFO_BAR_HEIGHT*2) / self.selectedSlot[2]
            gc.DrawRoundedRectangle(x+2, INFO_BAR_HEIGHT + sh * self.selectedSlot[1] + 2, hs - 4, sh - 4, 5)
            
        # highlighted slot
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)))
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_ACTIVEBORDER), 2, wx.PENSTYLE_LONG_DASH))
        if self.highlightedSlot[2]>0:
            x = sab + (self.highlightedSlot[0]-1) * hs
            sh = (h - INFO_BAR_HEIGHT*2) / self.highlightedSlot[2]
            gc.DrawRoundedRectangle(x+2, INFO_BAR_HEIGHT + sh * self.highlightedSlot[1] + 2, hs - 4, sh - 4, 5)
            
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
    
    def Play(self):
        self.playTimer.Start(milliseconds=1000.0/self.fps)
        
    def SelectHighlighted(self, x, y):
        if self.highlightedSlot[2]:
            self.selectedSlot[0] = self.highlightedSlot[0]
            self.selectedSlot[1] = self.highlightedSlot[1]
            self.selectedSlot[2] = self.highlightedSlot[2]
            self.Refresh()
        
    def SetCurrentFrame(self, frame):
        if self.currentFrame != frame:
            key = self.GetKey(frame)
            evt = FrameChangedEvent(key = key, frame = frame, lastFrame = self.currentFrame)
            wx.PostEvent(self, evt)
            
            self.currentFrame = frame
            self.Refresh()
            
    def SetCurrentFrameFromPosition(self, x, y):
        w, h = self.GetClientSize()
        if y>20 and y<h-20:
            return
        self.SetCurrentFrame(max(1, self.GetFrameFromPosition(x, y)))
        
    def SetEndFrameToPosition(self, x, y):
        newf = int((x - self.startAnimationBlock)/self.horizontalScale)
        if newf<2:
            return
        self.SetTotalFrames(newf)
        
    def SetTotalFrames(self, frames):
        self.totalFrames = frames
        self.Refresh()
        
    def Stop(self):
        self.playTimer.Stop()
        
    def UnSetHighlightedSlot(self):
        self.highlightedSlot[0] = 0
        self.highlightedSlot[1] = 0
        self.highlightedSlot[2] = 0
        
    def UnSetSelectedSlot(self):
        self.selectedSlot[0] = 0
        self.selectedSlot[1] = 0
        self.selectedSlot[2] = 0
        
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
        
        # ANIMATION PANEL
        self.panel = AnimationPanel(self)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.panel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.panel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.panel.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.panel.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
        #self.panel.InsertImage(3, self)
        #self.panel.InsertImage(4, self)
        #self.panel.InsertImage(14, self)
        
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 1)
        
        # ANIMATION CONTROLS
        conpanel = wx.Panel(self)
        consizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn = wx.Button(conpanel, label="Play")
        self.Bind(wx.EVT_BUTTON, self.OnPlay, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        btn = wx.Button(conpanel, label="Stop")
        self.Bind(wx.EVT_BUTTON, self.OnStop, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        btn = wx.Button(conpanel, label="Key In")
        self.Bind(wx.EVT_BUTTON, self.OnInsertKey, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        conpanel.SetSizer(consizer)
        sizer.Add(conpanel, 0, wx.ALIGN_CENTER, 1)
        
        self.SetSizer(sizer)
        
        self.prevx, self.prevy = 0, 0
        self.grab = None
        
    def OnInsertKey(self, e):
        key = (randrange(12), randrange(12))
        self.panel.InsertKey(key)
        
    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.Position
        self.grab = None
        
        if self.panel.IsEndFrameHandle(self.prevx, self.prevy):
            self.grab = END_FRAME_HANDLE
        else:
            self.panel.SetCurrentFrameFromPosition(self.prevx, self.prevy)
            self.panel.SelectHighlighted(self.prevx, self.prevy)
    def OnLeftUp(self, e):
        self.grab = None
        
    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.Position

    def OnMouseMove(self, e):
        x, y = e.Position
        self.panel.UnSetHighlightedSlot()
        
        if e.middleIsDown:
            self.panel.Pan(x-self.prevx)
            self.panel.Refresh()
        elif e.leftIsDown:
            if self.grab == END_FRAME_HANDLE:
                self.panel.SetEndFrameToPosition(x, y)
            else:
                self.panel.SetCurrentFrameFromPosition(self.prevx, self.prevy)
        elif e.rightIsDown:
            pass
        else:
            if self.panel.IsEndFrameHandle(x, y):
                self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
                self.panel.HighlightSlotFromPosition(x, y)
            self.panel.Refresh()
            
        self.prevx, self.prevy = x, y
        
    def OnMouseWheel(self, e):
        amt = e.GetWheelRotation()
        self.panel.ZoomOnPosition(*e.Position, amt)
        self.panel.Refresh()
        
    def OnPlay(self, e):
        self.panel.Play()
        
    def OnResize(self, e):
        self.panel.Refresh()
        e.Skip()
        
    def OnStop(self, e):
        self.panel.Stop()
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Animation Control")
    l = AnimationControl(f)
    f.Show()
    app.MainLoop()
    