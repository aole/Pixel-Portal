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

FrameChangedEvent,           EVT_FRAME_CHANGED_EVENT          = wx.lib.newevent.NewEvent()
VisibilityChangedEvent,      EVT_VISIBILITY_CHANGED_EVENT     = wx.lib.newevent.NewEvent()
KeyInsertEvent,              EVT_KEY_INSERT_EVENT             = wx.lib.newevent.NewEvent()
KeyDeleteEvent,              EVT_KEY_DELETE_EVENT             = wx.lib.newevent.NewEvent()
KeySetEvent,                 EVT_KEY_SET_EVENT                = wx.lib.newevent.NewEvent()

class PlayTimer(wx.Timer):
    def __init__(self, parent=None):
        super().__init__()
        
        self.parent = parent

    def Notify(self):
        self.parent.NextFrame()
        
class AnimationPanel(wx.Panel):
    def __init__(self, parent=None, document=None):
        super().__init__(parent)

        self.CURRENT_FRAME_COLOR = wx.Colour(*wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT).Get(False), 50)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.SINGLE_KEY_PER_FRAME = True
        
        self.document = document
        self.startAnimationBlock = 25
        self.horizontalScale = 12
        self.highlightedSlot = [0, 0, 0] # frame | slot | of num slots
        self.playTimer = PlayTimer(self)
        
        self.SetMinSize(wx.Size(100, 100))
        
        self.grabbedKey = None
        self.grabbedFrame = -1
        
    def DeleteKey(self, frame=None):
        if not frame:
            frame = self.document.currentFrame
        key = self.document.keys[frame]
        del self.document.keys[frame]
        self.Refresh()
        return key[0]
        
    def GetCurrentFrame(self):
        return self.document.currentFrame
        
    def GetFrameFromPosition(self, x, y):
        return int((x - self.startAnimationBlock)/self.horizontalScale) + 1
        
    def GetGrabbedKey(self):
        return self.grabbedKey
        
    def GetDisplayKey(self):
        return self.GetKey(self.document.currentFrame)
        
    # get key on this frame or any previous one
    def GetKey(self, frame):
        f = frame
        while not f in self.document.keys and f>0:
            f -= 1
        if f in self.document.keys:
            key = self.document.keys[f]
            if self.SINGLE_KEY_PER_FRAME:
                key = key[0]
            return key
            
        return None
        
    # get key from this frame only
    def GetAbsoluteKey(self, frame):
        if frame in self.document.keys:
            return self.document.keys[frame]
        else:
            return None
            
    def GrabKey(self, key, frame):
        self.grabbedKey = key
        self.grabbedFrame = frame
        del self.document.keys[frame]
        
    def HighlightSlotFromPosition(self, x, y):
        w, h = self.GetClientSize()
        self.UnSetHighlightedSlot()
        
        if y < INFO_BAR_HEIGHT or y > h-INFO_BAR_HEIGHT:
            return
        f = self.GetFrameFromPosition(x, y)
        if f<=0: # or f>self.document.totalFrames:
            return
            
        self.highlightedSlot[0] = f
        if not f in self.document.keys or self.SINGLE_KEY_PER_FRAME:
            self.highlightedSlot[2] = 1
        else:
            h -= INFO_BAR_HEIGHT*2
            y -= INFO_BAR_HEIGHT
            key = self.document.keys[f]
            self.highlightedSlot[2] = len(key)+1
            self.highlightedSlot[1] = int(y/(h/self.highlightedSlot[2]))
            
    def InsertKey(self, frame, key):
        self.document.keys[frame] = [key]
        self.Refresh()
            
    def IsEndFrameHandle(self, x, y, margin=10):
        pos = self.startAnimationBlock + self.document.totalFrames * self.horizontalScale
        return x>=pos and x<pos+margin
    
    def MoveKey(self, frame, key):
        self.document.keys[self.document.currentFrame] = key
        if not frame == self.document.currentFrame:
            self.Refresh()
    
    def NextFrame(self):
        nf = 1 if self.document.currentFrame>=self.document.totalFrames else self.document.currentFrame+1
        self.SetCurrentFrame(nf)
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        
        w, h = self.GetClientSize()
        cf = self.document.currentFrame
        hs = self.horizontalScale
        tf = self.document.totalFrames
        sab = self.startAnimationBlock
        
        # block for total animation length
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)))
        gc.SetPen(wx.NullPen)
        gc.DrawRectangle(sab, 0, tf*hs, h)
        
        # keys
        c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)
        c.Set(c.red, c.green+20, c.blue)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(c))
        gc.SetPen(wx.NullPen)
        for f, key in self.document.keys.items():
            fi = f - 1
            numslots = len(key)
            sh = (h-INFO_BAR_HEIGHT*2)/numslots
            y = INFO_BAR_HEIGHT
            for i in range(numslots):
                gc.DrawRoundedRectangle(sab+fi*hs+2, y, hs-4, sh, 5)
                y += sh
        
        # grabbed key
        if self.grabbedKey:
            fi = self.document.currentFrame - 1
            numslots = len(self.grabbedKey)
            sh = (h-INFO_BAR_HEIGHT*2)/numslots
            y = INFO_BAR_HEIGHT
            for i in range(numslots):
                gc.DrawRoundedRectangle(sab+fi*hs+2, y, hs-4, sh, 5)
                y += sh
                
        # highlighted slot
        c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        c.Set(c.red, c.green, c.blue, 128)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(c))
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
        pos = sab + tf * hs - hs/2
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
        pos = sab + cf * hs - hs/2
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
        if not self.grabbedKey: # a bit distracting
            gc.SetPen(wx.NullPen)
            gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(self.CURRENT_FRAME_COLOR))
            x = sab+cf*hs
            gc.DrawRectangle(x-hs, INFO_BAR_HEIGHT, hs, (h-INFO_BAR_HEIGHT*2))
        
    def Pan(self, dx):
        self.startAnimationBlock += dx
        w, h = self.GetClientSize()
        if self.startAnimationBlock > w-10:
            self.startAnimationBlock = w-10
    
    def Play(self):
        self.playTimer.Start(milliseconds=1000.0/self.document.fps)
        
    def ReleaseKey(self):
        if self.grabbedKey:
            self.MoveKey(self.grabbedFrame, self.grabbedKey)
            self.grabbedKey = None
            self.grabbedFrame = -1
        
    def SetCurrentFrame(self, frame):
        if self.document.currentFrame != frame:
            key = self.GetKey(frame)
            evt = FrameChangedEvent(key = key, frame = frame, lastFrame = self.document.currentFrame)
            wx.PostEvent(self, evt)
            
            self.document.currentFrame = frame
            self.Refresh()
            
    def SetCurrentFrameFromPosition(self, x, y):
        w, h = self.GetClientSize()
        frame = max(1, self.GetFrameFromPosition(x, y))
        self.SetCurrentFrame(frame)
        
    def SetDocument(self, document):
        self.document = document
        
        key = self.GetKey(self.document.currentFrame)
        evt = FrameChangedEvent(key = key, frame = self.document.currentFrame, lastFrame = self.document.currentFrame)
        wx.PostEvent(self, evt)
        self.Refresh()
        
    def SetEndFrameToPosition(self, x, y):
        newf = int((x - self.startAnimationBlock)/self.horizontalScale)
        if newf<2:
            return
        self.SetTotalFrames(newf)
        
    def SetKeyToCurrentFrame(self, key):
        self.document.keys[self.document.currentFrame] = key
        self.Refresh()
        
    def SetTotalFrames(self, frames):
        self.document.totalFrames = frames
        self.Refresh()
        
    def Stop(self):
        self.playTimer.Stop()
        
    def UnSetHighlightedSlot(self):
        self.highlightedSlot[0] = 0
        self.highlightedSlot[1] = 0
        self.highlightedSlot[2] = 0
        
    def ZoomOnPosition(self, x, y, amt):
        ps = self.horizontalScale*self.document.totalFrames
        if amt>0:
            self.horizontalScale += 1
        else:
            self.horizontalScale = max(3, self.horizontalScale-1)
            
        self.startAnimationBlock -= int((self.horizontalScale*self.document.totalFrames-ps)*((x - self.startAnimationBlock)/(ps)))
        self.Refresh()
        
class AnimationView(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent)
    
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.SetMinSize(wx.Size(100, 100))
        
        self.freeze = False
        self.bitmap = None
        
    def Display(self, key):
        if self.freeze:
            return
            
        if key:
            w, h = self.GetClientSize()
            ar = w/h
            
            kw, kh = key[0].width, key[0].height
            kar = kw/kh
            
            if kar>ar:
                sr = w/kw
            else:
                sr = h/kh
            
            w = kw*sr
            h = kh*sr
            
            self.bitmap = Layer(w, h)
            self.bitmap.DrawAll(key)
        else:
            self.bitmap = None
            
    def Freeze(self, key):
        self.Display(key)
        self.freeze = True
        
    def OnFrameChanged(self, e):
        self.Display(e.key)
        self.Refresh()
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        
        w, h = self.GetClientSize()
        if self.bitmap:
            gc.DrawBitmap(self.bitmap, max(0, (w-self.bitmap.width)/2), max(0, (h-self.bitmap.height)/2), self.bitmap.width, self.bitmap.height)
    
    def UnFreeze(self):
        self.freeze = False
        
class AnimationControl(wx.Window):
    def __init__(self, parent=None, document=None):
        super().__init__(parent)
        
        self.document = document
        
        # ANIMATION PANEL
        self.panel = AnimationPanel(self, document)
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.panel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.panel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.panel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.panel.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.panel.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        # VIEW PANEL
        self.view = AnimationView(self)
        self.panel.Bind(EVT_FRAME_CHANGED_EVENT, self.view.OnFrameChanged)
        
        panelsizer = wx.BoxSizer(wx.VERTICAL)
        animsizer = wx.BoxSizer(wx.HORIZONTAL)
        animsizer.Add(self.panel, 3, wx.EXPAND | wx.ALL, 1)
        animsizer.Add(self.view, 1, wx.EXPAND | wx.ALL, 1)
        
        panelsizer.Add(animsizer, 1, wx.EXPAND | wx.ALL, 1)
        
        # ANIMATION CONTROLS
        conpanel = wx.Panel(self)
        consizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn = wx.BitmapButton(conpanel, bitmap=wx.Bitmap("icons/play.png"))
        self.Bind(wx.EVT_BUTTON, self.OnPlay, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        btn = wx.BitmapButton(conpanel, bitmap=wx.Bitmap("icons/stop.png"))
        self.Bind(wx.EVT_BUTTON, self.OnStop, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        consizer.AddSpacer(50)
        
        btn = wx.BitmapButton(conpanel, bitmap=wx.Bitmap("icons/key.png"))
        self.Bind(wx.EVT_BUTTON, self.OnInsertKey, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        btn = wx.BitmapButton(conpanel, bitmap=wx.Bitmap("icons/keydelete.png"))
        self.Bind(wx.EVT_BUTTON, self.OnDeleteKey, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        consizer.AddSpacer(50)
        
        self.txtFPS = wx.StaticText(conpanel, label=str(self.document.fps))
        self.txtFPS.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False))
        consizer.Add(self.txtFPS, 0, wx.ALIGN_CENTER, 1)
        
        consizer.AddSpacer(5)
        
        btn = wx.BitmapButton(conpanel, bitmap=wx.Bitmap("icons/fps.png"))
        self.Bind(wx.EVT_BUTTON, self.OnFPSChange, id=btn.GetId())
        consizer.Add(btn, 0, wx.ALIGN_CENTER, 1)
        
        conpanel.SetSizer(consizer)
        panelsizer.Add(conpanel, 0, wx.ALIGN_CENTER, 1)
        
        self.SetSizer(panelsizer)
        
        self.prevx, self.prevy = 0, 0
        self.grab = None
    
    def DeleteKey(self, frame):
        key = self.panel.DeleteKey(frame)
        self.Refresh()
        return key
        
    def GetAnimationFrames(self):
        bitmaps = []
        for f in range(1, self.panel.totalFrames+1):
            key = self.panel.GetKey(f)
            if key:
                bitmap = Layer.Create(key[0].width, key[0].height)
                bitmap.DrawAll(key)
                bitmaps.append(bitmap)
        
        return bitmaps
        
    def GetFPS(self):
        return self.panel.fps
        
    def InsertKey(self, frame, key):
        self.panel.InsertKey(frame, key)
        self.Refresh()
        
    def OnDeleteKey(self, e):
        key = self.DeleteKey(self.panel.GetCurrentFrame())
    
        evt = KeyDeleteEvent(frame = self.panel.GetCurrentFrame(), key = key)
        wx.PostEvent(self, evt)
        
    def OnFPSChange(self, e):
        num = wx.GetNumberFromUser("Enter FPS", "FPS", "Pixel Portal", self.document.fps, 1, 1000, self)
        if num>0:
            self.document.fps = num
            self.txtFPS.SetLabel(str(num))
            self.Layout()
            
    def OnInsertKey(self, e):
        if self.document:
            key = []
            for layer in self.document:
                if layer.visible:
                    key.insert(0, layer)
            self.InsertKey(self.panel.GetCurrentFrame(), key)
            
            evt = KeyInsertEvent(frame = self.panel.GetCurrentFrame(), key = key)
            wx.PostEvent(self, evt)
            
            self.panel.NextFrame()
    
    def OnLeftDClick(self, e):
        self.prevx, self.prevy = e.Position
        f = self.panel.GetFrameFromPosition(self.prevx, self.prevy)
        gk = self.panel.GetAbsoluteKey(f)
        if gk:
            evt = VisibilityChangedEvent(key = gk[0], frame = self.document.currentFrame)
            wx.PostEvent(self, evt)
            
    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.Position
        self.grab = None
        self.grabbedKey = None
        
        if self.panel.IsEndFrameHandle(self.prevx, self.prevy):
            self.grab = END_FRAME_HANDLE
        else:
            self.panel.SetCurrentFrameFromPosition(self.prevx, self.prevy)
            # below can be different from above
            f = self.panel.GetFrameFromPosition(self.prevx, self.prevy)
            gk = self.panel.GetAbsoluteKey(f)
            if gk:
                self.panel.GrabKey(gk, f)
                self.view.Freeze(gk[0])
            
    def OnLeftUp(self, e):
        self.grab = None
        if self.panel.grabbedKey and not self.panel.document.currentFrame == self.panel.grabbedFrame:
            evt = KeySetEvent(key = self.panel.grabbedKey[0], frame = self.panel.document.currentFrame, fromFrame = self.panel.grabbedFrame)
            wx.PostEvent(self, evt)
        self.panel.ReleaseKey()
        self.view.UnFreeze()
            
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
        
    def OnPlay(self, e):
        self.panel.Play()
        
    def OnResize(self, e):
        self.panel.Refresh()
        e.Skip()
        
    def OnStop(self, e):
        self.panel.Stop()
    
    def Refresh(self):
        self.panel.Refresh()
        self.view.Display(self.panel.GetDisplayKey())
        super().Refresh()
    
    def SetCurrentFrame(self, frame):
        self.panel.SetCurrentFrame(frame)
        
    def SetDocument(self, document):
        self.document = document
        self.panel.SetDocument(document)
        self.txtFPS.SetLabel(str(self.document.fps))
        
if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None, title="Animation Control")
    l = AnimationControl(f, LayerManager.CreateDummy(50, 50, 3))
    l.OnInsertKey(None)
    key = l.DeleteKey(1)
    l.InsertKey(4, key)
    l.SetCurrentFrame(4)
    l.OnDeleteKey(None)
    f.Show()
    app.MainLoop()
    