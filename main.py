"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

from math import ceil

from shapely.geometry   import Polygon, MultiPolygon, LineString
from shapely.ops        import unary_union

import wx
from wx.adv import BitmapComboBox
from wx.lib.agw.cubecolourdialog import CubeColourDialog

from PIL import Image, ImageDraw, ImageSequence

import numpy as np

from undomanager import *
from layermanager import *
from gradienteditor import *
from layercontrol import *

PROGRAM_NAME = "Pixel Portal"
WINDOW_SIZE = (800, 550)

DEFAULT_DOC_SIZE = (80, 80)
DEFAULT_PIXEL_SIZE = 5

TOOLS = {"Pen":             (wx.CURSOR_PENCIL,      "toolpen.png"),
         "Select":          (wx.CURSOR_CROSS,       "toolselectrect.png"),
         "Line":            (wx.CURSOR_CROSS,       "toolline.png"),
         "Rectangle":       (wx.CURSOR_CROSS,       "toolrect.png"),
         "Ellipse":         (wx.CURSOR_CROSS,       "toolellipse.png"),
         "Move":            (wx.CURSOR_SIZING,      "toolmove.png"),
         "Bucket":          (wx.CURSOR_PAINT_BRUSH, "toolbucket.png"),
         "Picker":          (wx.CURSOR_RIGHT_ARROW, "toolpicker.png"),
         "Gradient":        (wx.CURSOR_CROSS,       "toolgradient.png"),
         "Radial Gradient": (wx.CURSOR_CROSS,       "toolrgradient.png")}

#Debug
RENDER_CURRENT_LAYER = True
RENDER_PREVIEW = True
RENDER_PIXEL_UNDER_MOUSE = False
PRINT_UNDO_REDO = True

app = None

def minmax(a, b):
    if b < a:
        return b, a
    else:
        return a, b

class Canvas(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)

        self.panx = 20
        self.pany = 20

        self.prevx, self.prevy = 0, 0
        self.origx, self.origy = 0, 0
        self.prevgx, self.prevgy = -1, -1
        self.linePoints = []
        self.smoothLine = False
        
        self.movex, self.movey = 0, 0
        self.selection = wx.Region()
        self.lastSelection = None
        
        self.mouseState = 0
        self.doubleClick = False
        
        self.current_tool = "Pen"
        self.original_tool = self.current_tool
        self.mirrorx = False
        self.mirrory = False
        self.gridVisible = True

        self.pixel_size = DEFAULT_PIXEL_SIZE

        self.penSize = 1
        self.penColor = wx.BLACK
        self.palette = None
        
        self.gradientStops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        self.gradientStops.Add(wx.GraphicsGradientStop(wx.BLACK, 0))
        self.gradientStops.Add(wx.GraphicsGradientStop(wx.WHITE, 1))
        
        self.refAlpha = 0.3
        self.refScale = 1
        self.reference = None
        
        self.layers = LayerManager()
        
        self.alphabg = wx.Bitmap("alphabg.png")

        # UNDO / REDO
        self.history = UndoManager()
        self.beforeLayer = None
        self.noUndo = False

        self.SetCursor(wx.Cursor(TOOLS[self.current_tool][0]))

        self.listeners = []

    def ClearCurrentLayer(self):
        self.beforeLayer = self.layers.Current().Copy()

        self.layers.Current().Clear(clip=self.selection)

        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, self.beforeLayer, self.layers.Current().Copy()))
        self.beforeLayer = None
        self.Refresh()

    def DrawGrid(self, gc):
        w, h = self.GetClientSize()

        # minor lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#55555555'))
        path = gc.CreatePath()
        for x in range(self.panx, min(self.panx + self.layers.width * self.pixel_size + 1, w), self.pixel_size):
            path.MoveToPoint(x, self.pany)
            path.AddLineToPoint(x, min(self.pany + self.layers.height * self.pixel_size, h))
        for y in range(self.pany, min(self.pany + self.layers.height * self.pixel_size + 1, h), self.pixel_size):
            path.MoveToPoint(self.panx, y)
            path.AddLineToPoint(min(self.panx + self.layers.width * self.pixel_size, w), y)
        gc.StrokePath(path)

        midpx = self.pixel_size * int(self.layers.width / 2)
        midpy = self.pixel_size * int(self.layers.height / 2)

        # major lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#22222255'))
        path = gc.CreatePath()
        if midpx:
            path.MoveToPoint(midpx+self.panx, self.pany)
            path.AddLineToPoint(midpx+self.panx, min(self.pany + self.layers.height * self.pixel_size, h))
            if self.mirrorx:
                path.MoveToPoint(midpx+self.panx-self.pixel_size, self.pany)
                path.AddLineToPoint(midpx+self.panx-self.pixel_size, min(self.pany + self.layers.height * self.pixel_size, h))
        if midpy:
            path.MoveToPoint(self.panx, midpy+self.pany)
            path.AddLineToPoint(min(self.panx + self.layers.width * self.pixel_size, w), midpy+self.pany)
            if self.mirrory:
                path.MoveToPoint(self.panx, midpy+self.pany-self.pixel_size)
                path.AddLineToPoint(min(self.panx + self.layers.width * self.pixel_size, w), midpy+self.pany-self.pixel_size)
        gc.StrokePath(path)

    def GetXMirror(self, x):
        w = int(self.layers.width / 2)
        return ((x + 1 - w) * -1) + w - 1

    def GetYMirror(self, y):
        h = int(self.layers.height / 2)
        return ((y + 1 - h) * -1) + h - 1

    def DrawPixel(self, x, y, color, canmirrorx=True, canmirrory=True):
        self.layers.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawPixel(self.GetXMirror(x), y, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawPixel(x, self.GetYMirror(y), color, False, False)

    def ErasePixel(self, x, y, canmirrorx=True, canmirrory=True):
        self.layers.ErasePixel(x, y, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.ErasePixel(self.GetXMirror(x), y, False, True)
        if canmirrory and self.mirrory:
            self.ErasePixel(x, self.GetYMirror(y), False, False)

    def OnFloodFill(self):
        x,y = wx.GetMousePosition()
        x,y = self.ScreenToClient(x,y)
        gx, gy = self.PixelAtPosition(x,y)
        
        beforeLayer = self.layers.Current().Copy()
        self.layers.BlitToSurface()
        self.layers.Current().Clear()
        self.FloodFill(gx, gy, self.penColor)
        self.layers.BlitFromSurface()
        self.layers.surface.Clear()
        
        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, beforeLayer, self.layers.Current().Copy()))
        self.Refresh()
        
    def FloodFill(self, x, y, color):
        #self.layers.surface.FloodFill(x, y, color, self.selection)
        #return
        
        
        w, h = self.layers.width, self.layers.height
        
        def bpos(xp, yp):
            return yp*w*4+xp*4
            
        def car(a, b):
            return a[0]==b[0] and a[1]==b[1] and a[2]==b[2] and a[3]==b[3]
            
        if x < 0 or y < 0 or x > w - 1 or y > h - 1:
            return
        if not self.selection.IsEmpty() and not self.selection.Contains(x, y):
            return

        buf = bytearray(w*h*4)
        self.layers.surface.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
        i = bpos(x,y)
        replace = buf[i:i+4]
        
        rgba = color.Get()
        
        queue = {(x, y)}
        while queue:
            # replace current pixel
            x, y = queue.pop()
            i = bpos(x,y)
            
            if not self.selection or self.selection.IsEmpty() or self.selection.Contains(x, y):
                buf[i] = rgba[0]
                buf[i+1] = rgba[1]
                buf[i+2] = rgba[2]
                buf[i+3] = rgba[3]
                # north
                d = bpos(x,y-1)
                if y > 0 and car(buf[d:d+4], replace) and not car(buf[d:d+4], rgba):
                    queue.add((x, y - 1))
                # east
                d = bpos(x+1,y)
                if x < w - 1 and car(buf[d:d+4], replace) and not car(buf[d:d+4], rgba):
                    queue.add((x + 1, y))
                # south
                d = bpos(x,y+1)
                if y < h - 1 and car(buf[d:d+4], replace) and not car(buf[d:d+4], rgba):
                    queue.add((x, y + 1))
                # west
                d = bpos(x-1, y)
                if x > 0 and car(buf[d:d+4], replace) and not car(buf[d:d+4], rgba):
                    queue.add((x - 1, y))
                    
        self.layers.surface.CopyFromBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
    def DrawLine(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            self.layers.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            if canmirrorx and self.mirrorx:
                self.DrawLine(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
            if canmirrory and self.mirrory:
                self.DrawLine(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def EraseLine(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True):
        self.layers.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.EraseLine(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True)
        if canmirrory and self.mirrory:
            self.EraseLine(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False)

    def Spline(self, pts, color, canmirrorx=True, canmirrory=True):
        self.layers.Spline(pts, color)
        if canmirrorx and self.mirrorx:
            mpts = [(self.GetXMirror(x), y) for x,y in pts]
            self.Spline(mpts, color, False, True)
        if canmirrory and self.mirrory:
            mpts = [(x, self.GetYMirror(y)) for x,y in pts]
            self.Spline(mpts, color, False, False)

    def DrawRectangle(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            x = min(x0, x1)
            y = min(y0, y1)
            w = abs(x1 - x0)
            h = abs(y1 - y0)
            
            if center:
                xc = x0
                yc = y0
            if equal and w!=h:
                w = h = min(w,h)
                if x0>x1:
                    x = x0-w
                if y0>y1:
                    y = y0-w
                    
            if w==0 or h==0:
                if w==0 and h==0:
                    self.layers.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
                else:
                    self.layers.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            elif center:
                self.layers.Rectangle(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
            else:
                self.layers.Rectangle(x, y, w, h, color, size=self.penSize, clip=self.selection)
            
            if canmirrorx and self.mirrorx:
                self.DrawRectangle(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
            if canmirrory and self.mirrory:
                self.DrawRectangle(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def EraseRectangle(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True, equal=False, center=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        
        if center:
            xc = x0
            yc = y0
        if equal and w!=h:
            w = h = min(w,h)
            if x0>x1:
                x = x0-w
            if y0>y1:
                y = y0-w
                
        if w==0 or h==0:
            if w==0 and h==0:
                self.layers.ErasePixel(x, y, size=self.penSize, clip=self.selection)
            else:
                self.layers.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        elif center:
            self.layers.EraseRectangle(xc-w, yc-h, w*2, h*2, size=self.penSize, clip=self.selection)
        else:
            self.layers.EraseRectangle(x, y, w, h, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.EraseRectangle(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.EraseRectangle(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False, equal, center)

    def DrawEllipse(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            x = min(x0, x1)
            y = min(y0, y1)
            w = abs(x1 - x0)
            h = abs(y1 - y0)
            
            if center:
                xc = x0
                yc = y0
            if equal and w!=h:
                w = h = min(w,h)
                if x0>x1:
                    x = x0-w
                if y0>y1:
                    y = y0-w
                    
            if w==0 or h==0:
                if w==0 and h==0:
                    self.layers.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
                else:
                    self.layers.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            elif center:
                self.layers.Ellipse(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
            else:
                self.layers.Ellipse(x, y, w, h, color, size=self.penSize, clip=self.selection)
            
            if canmirrorx and self.mirrorx:
                self.DrawEllipse(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
            if canmirrory and self.mirrory:
                self.DrawEllipse(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def EraseEllipse(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True, equal=False, center=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        
        if center:
            xc = x0
            yc = y0
        if equal and w!=h:
            w = h = min(w,h)
            if x0>x1:
                x = x0-w
            if y0>y1:
                y = y0-w
                
        if w==0 or h==0:
            if w==0 and h==0:
                self.layers.ErasePixel(x, y, size=self.penSize, clip=self.selection)
            else:
                self.layers.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        elif center:
            self.layers.EraseEllipse(xc-w, yc-h, w*2, h*2, size=self.penSize, clip=self.selection)
        else:
            self.layers.EraseEllipse(x, y, w, h, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.EraseEllipse(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.EraseEllipse(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False, equal, center)

    def FillGradient(self, x0, y0, x1, y1):
        self.layers.FillGradient(x0, y0, x1, y1, self.gradientStops, clip=self.selection)
        
    def FillRGradient(self, x0, y0, x1, y1):
        self.layers.FillRGradient(x0, y0, x1, y1, self.gradientStops, clip=self.selection)
        
    def SetPenColor(self, color):
        self.penColor = color

    def GetPenColor(self):
        return self.penColor

    def SetGradientStops(self, stops):
        self.gradientStops = stops
        
    def GetGradientStops(self):
        return self.gradientStops
        
    def PixelAtPosition(self, x, y, func=int):
        return (func((x - self.panx) / self.pixel_size),
                func((y - self.pany) / self.pixel_size))

    def AdjustBrushSize(self, amount):
        self.penSize += amount
        if self.penSize<1:
            self.penSize = 1
            
        self.Refresh()
        
    def ChangePenColor(self, color):
        self.penColor = color
        for l in self.listeners:
            l.PenColorChanged(color)

    def Select(self, region=None):
        self.lastSelection = None
        if not region: # Select All
            self.selection = wx.Region(0,0,self.layers.width, self.layers.height)
        else:
            if self.selection and not self.selection.IsEmpty(): # Deselection
                self.lastSelection = self.selection
            self.selection = region
            
    def Deselect(self):
        if self.selection and not self.selection.IsEmpty(): # Deselection
            self.lastSelection = self.selection
        self.selection = wx.Region()
        
    def Reselect(self):
        if not self.selection or self.selection.IsEmpty():
            self.selection = self.lastSelection
            self.lastSelection = None
            
    def SelectInvert(self):
        s = wx.Region(0, 0, self.layers.width, self.layers.height)
        s.Subtract(self.selection)
        self.selection = s
        
    def UpdateSelection(self, x0, y0, x1, y1, sub=False):
        minx, maxx = minmax(x0, x1)
        miny, maxy = minmax(y0, y1)
        minx, miny = self.PixelAtPosition(minx, miny)
        maxx, maxy = self.PixelAtPosition(maxx, maxy, ceil)
        if sub:
            self.selection.Subtract(wx.Rect(minx, miny, maxx - minx, maxy - miny))
        else:
            self.selection.Union(minx, miny, maxx - minx, maxy - miny)
            
        self.selection.Intersect(0, 0, self.layers.width, self.layers.height)
        
    def SelectBoundary(self, x, y, add=False, sub=False):
        layer = self.layers.Current()
        w, h = layer.width, layer.height
        
        def bpos(xp, yp):
            return yp*w*4+xp*4
            
        def car(a, b):
            return a[0]==b[0] and a[1]==b[1] and a[2]==b[2] and a[3]==b[3]
            
        buf = bytearray(w*h*4)
        layer.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
        i = bpos(x,y)
        color = buf[i:i+4]
        
        queue = {(x, y)}
        col = set()
        selection = wx.Region()
        
        while queue:
            x, y = queue.pop()
            col.add((x,y))
            selection.Union(x,y, 1,1)
            # north
            d = bpos(x,y-1)
            if y > 0 and car(buf[d:d+4], color) and (x,y-1) not in col:
                queue.add((x, y - 1))
            # east
            d = bpos(x+1,y)
            if x < w - 1 and car(buf[d:d+4], color) and (x+1,y) not in col:
                queue.add((x + 1, y))
            # south
            d = bpos(x,y+1)
            if y < h - 1 and car(buf[d:d+4], color) and (x,y+1) not in col:
                queue.add((x, y + 1))
            # west
            d = bpos(x-1,y)
            if x > 0 and car(buf[d:d+4], color) and (x-1,y) not in col:
                queue.add((x - 1, y))
                    
        if add:
            self.selection.Union(selection)
        elif sub:
            self.selection.Subtract(selection)
        else:
            self.selection = selection
        
    def OnMouseWheel(self, e):
        amt = e.GetWheelRotation()
        if amt > 0:
            self.pixel_size += 1
        else:
            self.pixel_size -= 1
            if self.pixel_size < 1:
                self.pixel_size = 1

        for l in self.listeners:
            l.PixelSizeChanged(self.pixel_size)

        self.Refresh()

    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.prevgx, self.prevgy = gx, gy

        # draw with 1st color
        if self.mouseState == 1:
            if self.current_tool == "Pen":
                if self.smoothLine:
                    self.linePoints.append((gx, gy)) # for smoothing later
                self.DrawLine(*self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.penColor)
            elif self.current_tool == "Line":
                self.layers.surface.Clear()
                self.DrawLine(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Rectangle":
                self.layers.surface.Clear()
                self.DrawRectangle(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor, equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.layers.surface.Clear()
                self.DrawEllipse(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor,
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Move":
                self.movex, self.movey = int((x - self.origx)/ self.pixel_size), int((y - self.origy)/ self.pixel_size)
            elif self.current_tool == "Picker":
                color = self.layers.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
            elif self.current_tool == "Gradient":
                self.layers.surface.Clear()
                self.FillGradient(*self.PixelAtPosition(self.origx, self.origy), gx, gy)
            elif self.current_tool == "Radial Gradient":
                self.layers.surface.Clear()
                self.FillRGradient(*self.PixelAtPosition(self.origx, self.origy), gx, gy)

        # draw with 2nd color
        elif self.mouseState == 2:
            if self.current_tool == "Pen":
                self.EraseLine(*self.PixelAtPosition(self.prevx, self.prevy), gx, gy)
            elif self.current_tool == "Line":
                self.layers.BlitToSurface()
                self.EraseLine(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y))
            elif self.current_tool == "Rectangle":
                self.layers.BlitToSurface()
                self.EraseRectangle(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.layers.BlitToSurface()
                self.EraseEllipse(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Select":
                px, py = self.PixelAtPosition(self.prevx, self.prevy)
                if not self.selection.IsEmpty():
                    self.selection.Offset(gx - px, gy - py)

        elif self.mouseState == 3:
            self.panx += x - self.prevx
            self.pany += y - self.prevy

        self.prevx, self.prevy = x, y

        self.Refresh()

    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 1
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = self.layers.Current().Copy()

        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                if self.smoothLine:
                    self.linePoints.append((gx, gy))
                self.DrawPixel(gx, gy, self.penColor)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.DrawPixel(gx, gy, self.penColor)
        elif self.current_tool == "Move":
            self.layers.surface.Draw(self.layers.Current(), clip=self.selection)
            if not e.ControlDown():
                self.layers.Current().Clear(clip=self.selection)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.layers.BlitToSurface()
                self.layers.Current().Clear()
                self.FloodFill(gx, gy, self.penColor)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers.Composite().GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Select":
            if not e.ControlDown() and not e.AltDown():
                self.Select(wx.Region())

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnLeftUp(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.mouseState = 0

        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool == "Pen":
            # smooth line
            if self.smoothLine:
                self.layers.surface.Clear()
                line = LineString(self.linePoints)
                self.linePoints.clear()
                smoothline = line.simplify(1, True)
                self.Spline(smoothline.coords, self.penColor)
            self.layers.BlitFromSurface()
            
        elif self.current_tool in ("Line", "Ellipse", "Rectangle", "Gradient", "Radial Gradient"):
            self.layers.BlitFromSurface()
        elif self.current_tool == "Bucket":
            self.layers.BlitFromSurface()
        elif self.current_tool == "Move":
            self.layers.BlitFromSurface(self.movex, self.movey)
            if not self.selection.IsEmpty():
                ox, oy = self.PixelAtPosition(self.origx, self.origy)
                self.selection.Offset(self.movex, self.movey)
        elif self.current_tool == "Select" and not self.doubleClick:
            self.UpdateSelection(x, y, self.origx, self.origy, e.AltDown())
            self.doubleClick = False
            
        self.movex, self.movey = 0, 0

        self.layers.surface.Clear()

        # create an undo command
        if not self.noUndo:
            self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, self.beforeLayer, self.layers.Current().Copy()))
        self.beforeLayer = None

        self.noUndo = False
        self.current_tool = self.original_tool

        self.doubleClick = False
        self.Refresh()
        
        for l in self.listeners:
            l.RefreshLayers()

    def OnRightDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)
        self.mouseState = 2

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = self.layers.Current().Copy()

        # put a dot
        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.layers.BlitToSurface()
                self.ErasePixel(gx, gy)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.layers.BlitToSurface()
                self.ErasePixel(gx, gy)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers.Current().GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.layers.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.layers.BlitToSurface()
                self.layers.Current().Clear()
                self.FloodFill(gx, gy, wx.Colour(0,0,0,0))
        elif self.current_tool == "Select":
            self.noUndo = True
            if not self.selection.Contains(gx, gy):
                self.Select(wx.Region())

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnRightUp(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.mouseState = 0

        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool in ("Pen", "Line", "Rectangle", "Ellipse", "Bucket"):
            self.layers.SourceFromSurface()

        self.movex, self.movey = 0, 0

        self.layers.surface.Clear()

        # create an undo command
        if not self.noUndo:
            self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, self.beforeLayer, self.layers.Current().Copy()))
            self.noUndo = True
            
        self.current_tool = self.original_tool
        self.beforeLayer = None
        self.Refresh()
        
        for l in self.listeners:
            l.RefreshLayers()

    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 3
        self.noUndo = False

    def OnMiddleUp(self, e):
        self.mouseState = 0
        self.noUndo = False

    def OnLeftDClick(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        if self.current_tool=="Select":
            self.SelectBoundary(gx, gy, e.ControlDown(), e.AltDown())
        
        self.doubleClick = True
        
    def OnMouseEnter(self, e):
        self.SetFocus()
        
    def DrawBrushOnCanvas(self, gc, px, py):
        gc.SetPen(wx.NullPen)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(self.penColor))
        x, y = int(px-self.penSize/2+.5), int(py-self.penSize/2+.5)
        sz = self.penSize*self.pixel_size
        gc.DrawRectangle(self.panx+x*self.pixel_size, self.pany+y*self.pixel_size, sz, sz)
        
    def GetPolyCoords(self, x, y, w, h):
        return (x,y), (x,y+h), (x+w, y+h), (x+w,y)
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        alphadc = wx.MemoryDC(self.alphabg)
        
        skipCurrent = self.mouseState == 2 or (self.mouseState==1 and self.current_tool in ("Move"))
        composite = self.layers.Composite(self.movex, self.movey,
                                          drawCurrent=not skipCurrent,
                                          drawSurface=self.mouseState != 0)
        compositedc = wx.MemoryDC(composite)
        
        lw, lh = self.layers.width, self.layers.height
        plw, plh = self.layers.width*self.pixel_size, self.layers.height*self.pixel_size
        
        # PAINT WHOLE CANVAS BACKGROUND
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.Clear()

        # PAINT RULERS --------------
        dc.SetBrush(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
        dc.SetPen(wx.ThePenList.FindOrCreatePen("#999999FF"))
        dc.DrawRectangle(self.panx-10, 0, lw*self.pixel_size+20, 25)
        dc.DrawRectangle(0, self.pany-10, 25, lh*self.pixel_size+20)
        
        dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
        for rx in range(0, lw+1):
            if self.prevgx==rx and rx<lw:
                dc.SetBrush(wx.TheBrushList.FindOrCreateBrush("#CCCCCC"))
                dc.SetPen(wx.ThePenList.FindOrCreatePen("#999999FF"))
                dc.DrawRectangle(self.panx + rx * self.pixel_size, 0, 5, 5)
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
                dc.SetBrush(wx.NullBrush)
                
            rh = 10 if rx%5==0 else 5
            dc.DrawLine(self.panx + rx * self.pixel_size, 0, self.panx + rx * self.pixel_size, rh)
            if rx%5==0:
                rsz = int(dc.GetTextExtent(str(rx)).width/2)
                dc.DrawText(str(rx), self.panx + rx * self.pixel_size - rsz, rh)
                
        for ry in range(0, lh+1):
            if self.prevgy==ry and ry<lh:
                dc.SetBrush(wx.TheBrushList.FindOrCreateBrush("#CCCCCC"))
                dc.SetPen(wx.ThePenList.FindOrCreatePen("#999999FF"))
                dc.DrawRectangle(0, self.pany + ry * self.pixel_size, 5, 5)
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
                dc.SetBrush(wx.NullBrush)
                
            rw = 10 if ry%5==0 else 5
            dc.DrawLine(0, self.pany + ry * self.pixel_size, rw, self.pany + ry * self.pixel_size)
            if ry%5==0:
                rsz = int(dc.GetTextExtent(str(ry)).height/2)
                dc.DrawText(str(ry), rw, self.pany + ry * self.pixel_size - rsz)
            
        # CLIP TO DOCUMENT
        dc.SetClippingRegion(self.panx, self.pany, self.layers.width * self.pixel_size,
                             self.layers.height * self.pixel_size)

        # RENDER ALPHA BACKGROUND
        abgw, abgh = self.alphabg.GetWidth(), self.alphabg.GetHeight()
        dc.StretchBlit(self.panx, self.pany,
                       plw, plh,
                       alphadc,
                       0, 0,
                       abgw, abgh)
        
        # RENDER PAINT LAYERS
        if RENDER_CURRENT_LAYER:
            dc.StretchBlit(self.panx, self.pany,
                           self.layers.width * self.pixel_size, self.layers.height * self.pixel_size,
                           compositedc,
                           0, 0,
                           lw, lh)

        gc = wx.GraphicsContext.Create(dc)

        # DRAW BRUSH PREVIEW
        if RENDER_PIXEL_UNDER_MOUSE and self.mouseState == 0 and self.current_tool in ["Pen", "Line", "Rectangle", "Ellipse"]:
            self.DrawBrushOnCanvas(gc, self.prevgx, self.prevgy)
            
        # REFERENCE
        if self.reference:
            w, h = int(self.reference.width*self.refScale), int(self.reference.height*self.refScale)
            ar = w/h
            cw, ch = self.layers.width * self.pixel_size, self.layers.height * self.pixel_size
            gc.DrawBitmap(self.reference, self.panx, self.pany, min(cw, ch*ar), min(cw/ar,ch))
            
        # GRID
        if self.gridVisible and self.pixel_size > 2:
            self.DrawGrid(gc)

        # SELECTION
        display_selection_rect = True
        if self.mouseState == 1 and self.current_tool in ("Move"):
            display_selection_rect = False
        
        # XOR ADD CLEAR not supported on windows
        # print(gc.SetCompositionMode(wx.COMPOSITION_CLEAR))
        gc.SetBrush(wx.NullBrush)
        if self.mouseState == 1 and self.current_tool == "Select":
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22443388", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawRectangle(min(self.prevx, self.origx), min(self.prevy, self.origy), abs(self.prevx - self.origx),
                             abs(self.prevy - self.origy))
                             
        # TODO: Performance, precalculate shapely MultiPolygon union
        if self.selection and not self.selection.IsEmpty() and display_selection_rect:
            spoly = []
            for r in self.selection:
                poly = Polygon([*self.GetPolyCoords(r.x * self.pixel_size + self.panx,
                                 r.y * self.pixel_size + self.pany,
                                 r.width * self.pixel_size,
                                 r.height * self.pixel_size)])
                spoly.append(poly)
            spoly = unary_union(spoly)
            if not isinstance(spoly, MultiPolygon):
                spoly = MultiPolygon([spoly])
            # can have multiple disjoint polygons boundaries
            expath = gc.CreatePath()
            inpath = gc.CreatePath()
            for poly in spoly:
                moveto = True
                for x,y in poly.exterior.coords:
                    if moveto:
                        expath.MoveToPoint(x,y)
                        moveto = False
                    else:
                        expath.AddLineToPoint(x,y)
                expath.CloseSubpath()
                
                # each exterior boundary can have multiple interior holes
                for interior in poly.interiors:
                    moveto = True
                    for x,y in interior.coords:
                        if moveto:
                            inpath.MoveToPoint(x,y)
                            moveto = False
                        else:
                            inpath.AddLineToPoint(x,y)
                    inpath.CloseSubpath()
                    
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#66887788", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawPath(inpath)
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22443388", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawPath(expath)
            
        # PREVIEW
        if RENDER_PREVIEW:
            dc.DestroyClippingRegion()
            w, h = e.GetEventObject().GetSize()
            # BUG? dc.GetSize provide does not reduce in size if the window is expanded and them reduced.
            dc.StretchBlit(w-lw, 0,
                           lw, lh,
                           alphadc,
                           0, 0,
                           abgw, abgh)
            dc.StretchBlit(w-lw, 0,
                           lw, lh,
                           compositedc,
                           0, 0,
                           lw, lh)
        
        alphadc.SelectObject(wx.NullBitmap)
        del alphadc
        
    def Undo(self):
        if PRINT_UNDO_REDO:
            print('UNDO:', str(self.history.GetCurrentCommand()))
        self.history.Undo()
        self.Refresh()
        for l in self.listeners:
            l.Undid()
            
    def Redo(self):
        if PRINT_UNDO_REDO and self.history.Redo():
            print('REDO:', str(self.history.GetCurrentCommand()))
        self.Refresh()
        for l in self.listeners:
            l.Redid()
            
    def IsDirty(self):
        return self.history.IsDirty()

    def New(self, pixel, width, height):
        self.pixel_size = pixel

        # to ensure alpha
        bglayer = Layer.Create(width, height, wx.WHITE)
        bglayer.name = "background"
        
        self.layers.width = width
        self.layers.height = height
        self.layers.RemoveAll()
        self.layers.surface = Layer.Create(width, height)
        self.layers.surface.name = 'Surface'
        self.layers.AppendSelect(bglayer)
        self.layers.AppendSelect()

        self.history.ClearCommands()
        self.Deselect()
        
    def Resize(self, width, height):
        if width == self.layers.width and height == self.layers.height:
            return
        old = self.layers.Copy()
        #self.layers = LayerManager()
        self.layers.Resize(old, width, height)
        self.history.Store(ResizeCommand(self.layers, old, self.layers.Copy()))
        
        self.Refresh()

    def OnCropToSelection(self, e):
        if not self.selection or self.selection.IsEmpty():
            return
        
        rect = self.selection.GetBox()
        old = self.layers
        self.layers = LayerManager()
        self.layers.Crop(old, rect)
        
        self.history.ClearCommands()
        self.Deselect()

        for l in self.listeners:
            l.ImageSizeChanged(rect.width, rect.height)
            
        self.Refresh()
        
    def LoadRefImage(self, filename):
        image = Image.open(filename)
        image.putalpha(int(self.refAlpha*255))
        
        self.reference = Layer(wx.Bitmap.FromBufferRGBA(*image.size, image.tobytes()))

    def RemoveRefImage(self, e):
        self.reference = None
        self.Refresh()

    def Load(self, pixel, filename):
        if filename[-3:]=="png":
            image = wx.Image(filename)
            self.pixel_size = pixel
            width, height = int(image.GetWidth() / pixel), int(image.GetHeight() / pixel)

            self.New(pixel, width, height)

            self.layers.Current().Load(filename)
        elif filename[-3:]=="tif":
            im = Image.open(filename)
            width, height = int(im.width/pixel), int(im.height/pixel)
            self.layers.Init(width, height)
            for frame in ImageSequence.Iterator(im):
                bitmap = wx.Bitmap.FromBufferRGBA(im.width, im.height, frame.convert("RGBA").tobytes("raw"))
                self.layers.InsertBottom(Layer(Layer(bitmap).Scaled(1/pixel)))
            self.layers.currentLayer = 0
            
        self.history.ClearCommands()
        self.Deselect()

        for l in self.listeners:
            l.ImageSizeChanged(width, height)
            
    def Save(self, filename):
        if filename[-3:]=="png":
            self.layers.Composite().Scaled(self.pixel_size).SaveFile(filename, wx.BITMAP_TYPE_PNG)
        elif filename[-3:]=="tif":
            tifimgs = []
            w,h = self.layers.width*self.pixel_size, self.layers.height*self.pixel_size
            for layer in self.layers:
                buf = np.zeros(w*h*4)
                layer.Scaled(self.pixel_size).CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
                tifimg = Image.new('RGBA', (w,h))
                tifimg.frombytes(buf)
                tifimgs.append(tifimg)
            tifimgs[0].save(filename, compression="tiff_deflate", save_all=True,
               append_images=tifimgs[1:])
                
        self.history.MarkAsSaved()

    def SaveGif(self, filename):
        images = []
        wxImage = self.history.GetCommands()[0].before.Scaled(self.pixel_size).ConvertToImage()
        pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
        pilImage.frombytes(array(wxImage.GetDataBuffer()))
        images.append(pilImage)

        for cmd in self.history.GetCommands():
            wxImage = cmd.after.Scaled(self.pixel_size).ConvertToImage()
            pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
            pilImage.frombytes(array(wxImage.GetDataBuffer()))
            images.append(pilImage)
        images[0].save(filename, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)

    def SetTool(self, tool):
        self.current_tool = tool
        self.original_tool = tool
        self.SetCursor(wx.Cursor(TOOLS[tool][0]))

    def CenterCanvasInPanel(self, size):
        self.panx = int(size[0] / 2 - self.layers.width * self.pixel_size / 2)
        self.pany = int(size[1] / 2 - self.layers.height * self.pixel_size / 2)

        if self.panx < 30:
            self.panx = 30
        if self.pany < 30:
            self.pany = 30

    def GetMirror(self, bitmap, horizontally=True):
        return bitmap.ConvertToImage().Mirror(horizontally).ConvertToBitmap()

    def OnMirrorTR(self, e):
        before = self.layers.Current().Copy()
        after = Layer(self.GetMirror(before))
        after.name = before.name+' mirror'
        after.Draw(before, wx.Region(0, 0, int(before.width / 2), before.height))

        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, before, after.Copy()))
        self.layers.Set(after)

        self.Refresh()

    def OnMirrorTB(self, e):
        before = self.layers.Current().Copy()
        after = Layer(self.GetMirror(before, False))
        after.name = before.name+' mirror'
        after.Draw(before, wx.Region(0, 0, before.width, int(before.height / 2)))

        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, before, after.Copy()))
        self.layers.Set(after)

        self.Refresh()

    def OnFlipH(self, e):
        before = self.layers.Current().Copy()
        after = self.GetMirror(before)
        after.name = before.name+' mirror'

        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, before, after.Copy()))
        self.layers.Current().Draw(after)

        self.Refresh()

    def Rotate90(self, e, clockwise=True):
        before = self.layers.Current().Copy()
        image = before.ConvertToImage()
        image = image.Rotate90(clockwise)
        after = image.ConvertToBitmap()

        self.history.Store(PaintCommand(self.layers, self.layers.currentLayer, before, after.Copy()))
        self.layers.Current().Draw(after)

        self.Refresh()

    def AddLayer(self):
        index = self.layers.currentLayer
        layer = self.layers.AppendSelect().Copy()
        self.history.Store(AddLayerCommand(self.layers, index, layer))
        
    def RemoveLayer(self):
        index = self.layers.currentLayer
        layer = self.layers.Remove().Copy()
        self.history.Store(RemoveLayerCommand(self.layers, index, layer))
        
class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=PROGRAM_NAME, size=WINDOW_SIZE)

        self.FirstTimeResize = True

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        self.canvas = Canvas(self)
        self.canvas.listeners.append(self)

        # MENU
        self.menuid = 20001

        mbar = wx.MenuBar()

        mfile = wx.Menu()
        mbar.Append(mfile, "&File")
        
        mnew = wx.Menu()
        mfile.AppendSubMenu(mnew, "New")
        self.AddMenuItem(mnew, "32 x 32", self.OnNew32x32)
        
        medit = wx.Menu()
        mbar.Append(medit, "&Edit")
        self.AddMenuItem(medit, "Flip Horizontal", self.canvas.OnFlipH)
        self.AddMenuItem(medit, "Mirror to Right", self.canvas.OnMirrorTR)
        self.AddMenuItem(medit, "Mirror Down", self.canvas.OnMirrorTB)
        self.AddMenuItem(medit, "Reference Image ...", self.OnRefImage)
        self.AddMenuItem(medit, "Remove Reference Image", self.canvas.RemoveRefImage)
        self.AddMenuItem(medit, "Rotate 90 CW", self.canvas.Rotate90)
        self.AddMenuItem(medit, "Crop to Selection", self.canvas.OnCropToSelection)
        
        mselect = wx.Menu()
        mbar.Append(mselect, "&Selection")
        self.AddMenuItem(mselect, "Select &All\tCTRL+A", self.OnSelectAll)
        self.AddMenuItem(mselect, "&Deselect\tCTRL+SHIFT+A", self.OnDeselect)
        self.AddMenuItem(mselect, "&Reselect\tCTRL+SHIFT+D", self.OnReselect)
        self.AddMenuItem(mselect, "&Invert Selection\tCTRL+SHIFT+I", self.OnSelectInvert)

        menu = wx.Menu()
        mbar.Append(menu, "&Layer")
        self.AddMenuItem(menu, "&Add Layer", self.OnAddLayer)
        self.AddMenuItem(menu, "&Remove Layer", self.OnRemoveLayer)
        
        self.SetMenuBar(mbar)

        # TOOLBAR
        self.toolbar = tb = self.CreateToolBar()
        tb.SetToolBitmapSize((32, 32))
        
        self.AddToolButton(tb, 'Clear', self.OnClear, icon=wx.Bitmap("icons/clear.png"))
        self.AddToolButton(tb, 'Resize', self.OnDocResize, icon=wx.Bitmap("icons/resize.png"))

        self.txtPixel = wx.TextCtrl(tb, value=str(DEFAULT_PIXEL_SIZE))
        self.AddToolControl(tb, self.txtPixel)
        self.txtWidth = wx.TextCtrl(tb, value=str(DEFAULT_DOC_SIZE[0]))
        self.AddToolControl(tb, self.txtWidth)
        self.txtHeight = wx.TextCtrl(tb, value=str(DEFAULT_DOC_SIZE[1]))
        self.AddToolControl(tb, self.txtHeight)

        self.AddToolButton(tb, 'New', self.OnNew, icon=wx.Bitmap("icons/new.png"))
        self.AddToolButton(tb, 'Load', self.OnLoad, icon=wx.Bitmap("icons/load.png"))
        self.AddToolButton(tb, 'Save', self.OnSave, icon=wx.Bitmap("icons/save.png"))
        self.AddToolButton(tb, 'Gif', self.OnSaveGif, icon=wx.Bitmap("icons/gif.png"))
        tb.AddSeparator()
        
        self.colorbtn = self.AddToolButton(tb, 'Foreground Color', self.OnColor, icon=wx.Bitmap("icons/forecolor.png"))
        
        # Tool combo box
        bcb = BitmapComboBox(tb, style=wx.CB_READONLY)
        for k, v in TOOLS.items():
            bcb.Append(k, wx.Bitmap("icons/"+v[1]))
        self.Bind(wx.EVT_COMBOBOX, self.OnTool, id=bcb.GetId())
        bcb.SetSelection(0)
        tb.AddControl(bcb)
        
        # Gradient editor
        gbtn = wx.BitmapButton(tb, bitmap=wx.Bitmap("icons/gradient.png"))
        self.Bind(wx.EVT_BUTTON, self.OnGradient, id=gbtn.GetId())
        tb.AddControl(gbtn)
        
        self.AddToggleButton(tb, 'Grid', self.OnToggleGrid, icon=wx.Bitmap("icons/grid.png"), default=True)
        self.AddToggleButton(tb, 'Mirror X', self.OnMirrorX, icon=wx.Bitmap("icons/mirrorx.png"))
        self.AddToggleButton(tb, 'Mirror Y', self.OnMirrorY, icon=wx.Bitmap("icons/mirrory.png"))
        self.AddToggleButton(tb, 'Smooth Line', self.OnSmoothLine, icon=wx.Bitmap("icons/smooth.png"))
        self.AddToolButton(tb, 'Center', self.OnCenter, icon=wx.Bitmap("icons/center.png"))
        
        tb.Realize()

        # add CANVAS
        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.canvas, 2, wx.EXPAND | wx.ALL, 2)
        
        # RIGHT PANEL
        layerPanel = wx.Panel(self, size=(200,-1))
        bs.Add(layerPanel, 0, wx.EXPAND|wx.ALL, 2)
        bsp = wx.BoxSizer(wx.VERTICAL)
        
        # LAYERS LIST
        self.lyrctrl = LayerControl(layerPanel)
        self.lyrctrl.UpdateLayers(self.canvas.layers)
        self.lyrctrl.Bind(EVT_LAYER_CLICKED_EVENT, self.OnLayerClicked)
        self.lyrctrl.Bind(EVT_LAYER_VISIBILITY_EVENT, self.OnLayerVisibility)
        self.lyrctrl.Bind(EVT_LAYER_ALPHA_EVENT, self.OnLayerAlphaChange)
        bsp.Add(self.lyrctrl, 1, wx.EXPAND | wx.ALL, 3)
        
        self.OnNew(None, *DEFAULT_DOC_SIZE)
        
        layerPanel.SetSizer(bsp)
        layerPanel.FitInside()
        self.SetSizer(bs)

    def AddMenuItem(self, menu, name, func):
        menu.Append(self.menuid, name)
        menu.Bind(wx.EVT_MENU, func, id=self.menuid)
        self.menuid += 1

    def OnColor(self, e):
        data = wx.ColourData()
        data.SetColour(self.canvas.GetPenColor())
        dlg = CubeColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            self.canvas.SetPenColor(color)
            
            bitmap = self.colorbtn.GetBitmap()
            mdc = wx.MemoryDC(bitmap)
            
            clip = wx.Region(0,0,32,32)
            clip.Subtract(wx.Rect(9, 9, 14, 14))
            mdc.SetDeviceClippingRegion(clip)
            
            mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
            mdc.SetPen(wx.NullPen)
            mdc.DrawRectangle(0,0,32,32)
            
            mdc.SelectObject(wx.NullBitmap)
            del mdc
            
            self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)
        
    def PenColorChanged(self, color):
        bitmap = self.colorbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        clip = wx.Region(0,0,32,32)
        clip.Subtract(wx.Rect(9, 9, 14, 14))
        mdc.SetDeviceClippingRegion(clip)
        mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        mdc.SetPen(wx.NullPen)
        mdc.DrawRectangle(0,0,32,32)
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)

    def ImageSizeChanged(self, w, h):
        self.txtWidth.SetValue(str(w))
        self.txtHeight.SetValue(str(h))
        
    def PixelSizeChanged(self, value):
        self.txtPixel.SetValue(str(value))

    def Undid(self):
        self.RefreshLayers()
        
    def Redid(self):
        self.Undid()
        
    def AddToolButton(self, tb, label, function, icon):
        btn = tb.AddTool(wx.ID_ANY, label, icon, shortHelp=label)
        self.Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn
        
    def AddToggleButton(self, tb, label, function, icon, default=False):
        btn = tb.AddCheckTool(wx.ID_ANY, label, icon, shortHelp=label)
        tb.ToggleTool(btn.GetId(), default)
        self.Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn
        
    def AddToolControl(self, tb, control):
        control.SetSize(wx.DefaultCoord, wx.DefaultCoord, 30, wx.DefaultCoord)
        tb.AddControl(control)

    def OnClear(self, e):
        self.canvas.ClearCurrentLayer()
        self.RefreshLayers()

    def OnDocResize(self, e):
        width = int(self.txtWidth.GetValue())
        height = int(self.txtHeight.GetValue())
        self.canvas.Resize(width, height)

    def CheckDirty(self):
        if self.canvas.IsDirty():
            diag = wx.GenericMessageDialog(self, 'Save Changes?', style=wx.YES_NO | wx.CANCEL)
            ret = diag.ShowModal()
            if ret == wx.ID_YES:
                self.OnSave(None)
                return True
            elif ret == wx.ID_CANCEL:
                return False

        return True

    def OnRefImage(self, e):
        ret = wx.LoadFileSelector(PROGRAM_NAME, "png", parent=self)
        if ret:
            self.canvas.LoadRefImage(ret)
            self.canvas.Refresh()

    def OnLoad(self, e):
        if not self.CheckDirty():
            return

        with wx.FileDialog(self, "Open Image file",
                           wildcard="supported|*.tif;*.png|tif files (*.tif)|*.tif|png files (*.png)|*.png",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
                
            pixel = int(self.txtPixel.GetValue())
            self.canvas.Load(pixel, fd.GetPath())
            self.canvas.Refresh()
            self.RefreshLayers()

    def OnToggleGrid(self, e):
        self.canvas.gridVisible = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorX(self, e):
        self.canvas.mirrorx = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorY(self, e):
        self.canvas.mirrory = e.IsChecked()
        self.canvas.Refresh()

    def OnSmoothLine(self, e):
        self.canvas.smoothLine = e.IsChecked()
        self.canvas.Refresh()

    def OnNew32x32(self, e):
        self.OnNew(e, 32, 32)
        
    def OnNew(self, e, width=None, height=None):
        if not self.CheckDirty():
            return

        pixel = int(self.txtPixel.GetValue())
        if width:
            self.txtWidth.SetValue(str(width))
        else:
            width = int(self.txtWidth.GetValue())
        if height:
            self.txtHeight.SetValue(str(height))
        else:
            height = int(self.txtHeight.GetValue())
            
        self.canvas.New(pixel, width, height)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnSave(self, e):
        with wx.FileDialog(self, "Save Image file", wildcard="tif files (*.tif)|*.tif|png files (*.png)|*.png",
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
                
            self.canvas.Save(fd.GetPath())

    def OnSaveGif(self, e):
        ret = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if ret:
            self.canvas.SaveGif(ret)

    def OnKeyDown(self, e):
        keycode = e.GetUnicodeKey()

        if keycode == ord('Z'):
            if e.ControlDown():
                if e.ShiftDown():
                    self.canvas.Redo()
                else:
                    self.canvas.Undo()
        elif keycode == ord('['):
            self.canvas.AdjustBrushSize(-1)
        elif keycode == ord(']'):
            self.canvas.AdjustBrushSize(1)
        elif keycode == ord('F'):
            self.canvas.OnFloodFill()
        else:
            e.Skip()

    def OnTool(self, e):
        self.canvas.SetTool(e.GetString())

    def OnGradient(self, e):
        dlg = GradientEditor(self, self.canvas.GetGradientStops())
        if dlg.ShowModal() == wx.ID_OK:
            stops = dlg.GetStops()
            self.canvas.SetGradientStops(stops)
            
            bitmap = e.GetEventObject().GetBitmap()
            mdc = wx.MemoryDC(bitmap)
            gc = wx.GraphicsContext.Create(mdc)
            
            clip = wx.Region(2,2,60,28)
            mdc.SetDeviceClippingRegion(clip)
            
            brush = gc.CreateLinearGradientBrush(0, 0, 64, 0, stops)
            gc.SetBrush(brush)
            gc.SetPen(wx.NullPen)
            gc.DrawRectangle(0,0,64,32)
            
            mdc.SelectObject(wx.NullBitmap)
            del mdc
            
            e.GetEventObject().SetBitmap(bitmap)
        dlg.Destroy()
        
    def OnCenter(self, e):
        self.canvas.CenterCanvasInPanel(self.canvas.Size)
        self.canvas.Refresh()

    def OnResize(self, e):
        if self.FirstTimeResize:
            self.OnCenter(e)
            self.FirstTimeResize = False
        self.canvas.Refresh()
        e.Skip()

    def OnSelectAll(self, e):
        self.canvas.Select()
        self.Refresh()
        
    def OnDeselect(self, e):
        self.canvas.Select(wx.Region())
        self.Refresh()
        
    def OnReselect(self, e):
        self.canvas.Reselect()
        self.Refresh()
        
    def OnSelectInvert(self, e):
        self.canvas.SelectInvert()
        self.Refresh()
    
    def OnLayerClicked(self, e):
        self.canvas.layers.SelectIndex(e.index)
        self.RefreshLayers()
        
    def OnLayerVisibility(self, e):
        self.canvas.layers.ToggleVisible(e.index)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnLayerAlphaChange(self, e):
        self.canvas.layers.SetAlpha(e.alpha)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnAddLayer(self, e):
        self.canvas.AddLayer()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnRemoveLayer(self, e):
        self.canvas.RemoveLayer()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def RefreshLayers(self):
        self.lyrctrl.UpdateLayers(self.canvas.layers)
        self.lyrctrl.FitInside()
        
def CreateWindows():
    global app

    app = wx.App()

    Frame().Show()

def RunProgram():
    app.MainLoop()

CreateWindows()
RunProgram()
