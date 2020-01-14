"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

import colorsys
import numpy as np
from math import atan2, ceil, floor, pi
import random

import wx, wx.adv
import wx.lib.agw.cubecolourdialog as CCD

from PIL import Image, ImageDraw

COLOR_BLANK = wx.Colour(0,0,0,0)

PROGRAM_NAME = "Pixel Portal"
WINDOW_SIZE = (700, 550)
NUM_UNDOS = 100

DEFAULT_DOC_SIZE = (80, 80)
DEFAULT_PIXEL_SIZE = 5

TOOLS = {"Pen": (wx.CURSOR_PENCIL, "toolpen.png"), "Sel Rect": (wx.CURSOR_CROSS, "toolselectrect.png"), "Line": (wx.CURSOR_CROSS, "toolline.png"), "Rectangle": (wx.CURSOR_CROSS, "toolrect.png"), "Ellipse": (wx.CURSOR_CROSS, "toolellipse.png"), "Move": (wx.CURSOR_SIZING, "toolmove.png"), "Bucket": (wx.CURSOR_PAINT_BRUSH, "toolbucket.png"), "Picker": (wx.CURSOR_RIGHT_ARROW, "toolpicker.png")}

#Debug
RENDER_DRAWING_LAYER = True
RENDER_CURRENT_LAYER = True
RENDER_PREVIEW = True

app = None

def minmax(a, b):
    if b < a:
        return b, a
    else:
        return a, b

class Layer(wx.Bitmap):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = self.GetWidth()
        self.height = self.GetHeight()

    def Scaled(self, factor):
        bitmap = wx.Bitmap.FromRGBA(self.width * factor, self.height * factor, 0, 0, 0, 0)
        mdcd = wx.MemoryDC(bitmap)
        mdcs = wx.MemoryDC(self)
        mdcd.StretchBlit(0, 0,
                         self.width * factor, self.height * factor,
                         mdcs,
                         0,
                         0,
                         self.width, self.height)

        return bitmap

    def Clear(self, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))

        # gc.DrawRectangle(0, 0, *gc.GetSize())
        # weird bug ^^^ can't correctly draw a big rectangle in one go
        w, h = self.width, self.height
        for x in range(0, w, 60):
            for y in range(0, h, 60):
                gc.DrawRectangle(x, y, min(w, 60), min(h, 60))

    def GetPixel(self, x, y):
        mdc = wx.MemoryDC(self)
        return mdc.GetPixel(x, y)

    def SetPixel(self, x, y, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        gc.DrawRectangle(int(x-size/2+.5), int(y-size/2+.5), size, size)

    def SetPixels(self, pixels, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        for x, y in pixels:
            gc.DrawRectangle(x, y, 1, 1)

    # BUG?? FloodFill is painting with alpha=0
    def FloodFill(self, x0, y0, color, clip=None):
        pdc = wx.adv.PseudoDC()
        mdc = wx.MemoryDC(self)
        replace = mdc.GetPixel(x0, y0)
        
        mdc.SetBrush(wx.Brush(color))
        mdc.FloodFill(x0, y0, replace)
        return 
        
        gc = wx.GraphicsContext.Create(mdc)
        region = wx.Region(self, replace)
        w, h = self.width, self.height
        if not region.IsEmpty():
            region.Xor(0, 0, w, h)
            if clip and not clip.IsEmpty():
                region.Intersect(clip)
            gc.Clip(region)
            gc.SetBrush(wx.Brush(color))
            gc.SetPen(wx.NullPen)
            for x in range(0, w, 60):
                for y in range(0, h, 60):
                    gc.DrawRectangle(x, y, min(w, 60), min(h, 60))
            #gc.DrawRectangle(0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)
        
    def Line(self, x0, y0, x1, y1, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.StrokeLine(x0, y0, x1, y1)

    def Rectangle(self, x, y, w, h, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.DrawRectangle(x, y, w, h)

    def Ellipse(self, x, y, w, h, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.DrawEllipse(x, y, w, h)

    def Blit(self, layer, x=0, y=0, w=0, h=0):
        if w == 0:
            w = layer.width
        if h == 0:
            h = layer.height

        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, x, y, w, h)

    def Draw(self, layer, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, 0, 0, self.width, self.height)

    def Load(self, name):
        bitmap = wx.Bitmap()
        bitmap.LoadFile(name)

        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(bitmap, 0, 0, self.width, self.height)

class LayerCommand(wx.Command):
    def __init__(self, layers, before, after):
        super().__init__(True)

        self.layers = layers
        self.before = before
        self.after = after

    def Do(self):
        self.layers["current"].Blit(self.after)
        return True

    def Undo(self):
        self.layers["current"].Blit(self.before)
        return True

class ResizeCommand(wx.Command):
    def __init__(self, layers, before, after):
        super().__init__(True)

        self.layers = layers
        self.before = before
        self.after = after

    def Do(self):
        self.layers["width"] = self.after.width
        self.layers["height"] = self.after.height
        self.layers["current"] = Layer(wx.Bitmap.FromRGBA(self.after.width, self.after.height, 255, 255, 255, 255))
        self.layers["current"].Draw(self.after)
        self.layers["drawing"] = Layer(wx.Bitmap.FromRGBA(self.after.width, self.after.height, 0, 0, 0, 0))
        return True

    def Undo(self):
        self.layers["width"] = self.before.width
        self.layers["height"] = self.before.height
        self.layers["current"] = Layer(wx.Bitmap.FromRGBA(self.before.width, self.before.height, 255, 255, 255, 255))
        self.layers["current"].Draw(self.before)
        self.layers["drawing"] = Layer(wx.Bitmap.FromRGBA(self.before.width, self.before.height, 0, 0, 0, 0))
        return True

class UndoManager(wx.CommandProcessor):
    def __init__(self):
        super().__init__(NUM_UNDOS)

    def Store(self, command):
        super().Store(command)

class Canvas(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)

        self.full_redraw = True

        self.panx = 20
        self.pany = 20

        self.prevx, self.prevy = 0, 0
        self.origx, self.origy = 0, 0
        self.prevgx, self.prevgy = -1, -1
        
        self.movex, self.movey = 0, 0
        self.selection = wx.Region()
        self.lastSelection = None
        
        self.mouseState = 0
        self.current_tool = "Pen"
        self.mirrorx = False
        self.mirrory = False
        self.gridVisible = True

        self.pixel_size = DEFAULT_PIXEL_SIZE

        self.penSize = 1
        self.penColor = wx.BLACK
        self.eraserColor = wx.WHITE
        self.palette = None

        self.refAlpha = 0.3
        self.refScale = 1
        self.layers = {"width": 0,
                       "height": 0,
                       "drawing": None,
                       "current": None,
                       "reference": None}
        self.alphabg = wx.Bitmap("alphabg.png")

        # UNDO / REDO
        self.history = UndoManager()
        self.beforeLayer = None
        self.noUndo = False

        self.SetCursor(wx.Cursor(TOOLS[self.current_tool][0]))

        self.listeners = []

    def Blit(self, source, destination, x=0, y=0, w=0, h=0):
        self.layers[destination].Blit(self.layers[source], x, y, w, h)

    def ClearCurrentLayer(self):
        self.beforeLayer = Layer(self.layers["current"])

        self.layers["current"].Clear(self.eraserColor, clip=self.selection)

        self.history.Store(LayerCommand(self.layers, self.beforeLayer, Layer(self.layers["current"])))
        self.beforeLayer = None
        self.Refresh()

    def DrawGrid(self, gc):
        w, h = self.GetClientSize()

        # minor lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#55555555'))
        path = gc.CreatePath()
        for x in range(self.panx, min(self.panx + self.layers["width"] * self.pixel_size + 1, w), self.pixel_size):
            path.MoveToPoint(x, self.pany)
            path.AddLineToPoint(x, min(self.pany + self.layers["height"] * self.pixel_size, h))
        for y in range(self.pany, min(self.pany + self.layers["height"] * self.pixel_size + 1, h), self.pixel_size):
            path.MoveToPoint(self.panx, y)
            path.AddLineToPoint(min(self.panx + self.layers["width"] * self.pixel_size, w), y)
        gc.StrokePath(path)

        midpx = self.pixel_size * int(self.layers["width"] / 2)
        midpy = self.pixel_size * int(self.layers["height"] / 2)

        # major lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#22222255'))
        path = gc.CreatePath()
        if midpx:
            path.MoveToPoint(midpx+self.panx, self.pany)
            path.AddLineToPoint(midpx+self.panx, min(self.pany + self.layers["height"] * self.pixel_size, h))
            if self.mirrorx:
                path.MoveToPoint(midpx+self.panx-self.pixel_size, self.pany)
                path.AddLineToPoint(midpx+self.panx-self.pixel_size, min(self.pany + self.layers["height"] * self.pixel_size, h))
        if midpy:
            path.MoveToPoint(self.panx, midpy+self.pany)
            path.AddLineToPoint(min(self.panx + self.layers["width"] * self.pixel_size, w), midpy+self.pany)
            if self.mirrory:
                path.MoveToPoint(self.panx, midpy+self.pany-self.pixel_size)
                path.AddLineToPoint(min(self.panx + self.layers["width"] * self.pixel_size, w), midpy+self.pany-self.pixel_size)
        gc.StrokePath(path)

    def GetXMirror(self, x):
        w = int(self.layers["width"] / 2)
        return ((x + 1 - w) * -1) + w - 1

    def GetYMirror(self, y):
        h = int(self.layers["height"] / 2)
        return ((y + 1 - h) * -1) + h - 1

    def DrawPixel(self, layer, x, y, color, canmirrorx=True, canmirrory=True):
        self.layers[layer].SetPixel(x, y, color, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawPixel(layer, self.GetXMirror(x), y, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawPixel(layer, x, self.GetYMirror(y), color, False, False)

    def FloodFill(self, layer, x, y, color):
        w, h = self.layers["width"], self.layers["height"]
        
        if x < 0 or y < 0 or x > w - 1 or y > h - 1:
            return
        if not self.selection.IsEmpty() and not self.selection.Contains(x, y):
            return

        buf = bytearray(w*h*4)
        self.layers[layer].CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        buf = np.array(buf).reshape(h, w, 4)
        
        replace = np.array(buf[y][x])
        
        rgba = np.array([color.red, color.green, color.blue, color.alpha])
        
        queue = {(x, y)}
        while queue:
            # replace current pixel
            x, y = queue.pop()
            if not self.selection or self.selection.IsEmpty() or self.selection.Contains(x, y):
                buf[y][x] = rgba
                # north
                if y > 0 and np.array_equal(buf[y-1][x], replace) and not np.array_equal(buf[y-1][x], rgba):
                    queue.add((x, y - 1))
                # east
                if x < w - 1 and np.array_equal(buf[y][x + 1], replace) and not np.array_equal(buf[y][x + 1], rgba):
                    queue.add((x + 1, y))
                # south
                if y < h - 1 and np.array_equal(buf[y + 1][x], replace) and not np.array_equal(buf[y+1][x], rgba):
                    queue.add((x, y + 1))
                # west
                if x > 0 and np.array_equal(buf[y][x - 1], replace) and not np.array_equal(buf[y][x - 1], rgba):
                    queue.add((x - 1, y))
                    
        self.layers[layer].CopyFromBuffer(bytes(buf), wx.BitmapBufferFormat_RGBA)
        
    def DrawLine(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True):
        self.layers[layer].Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawLine(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawLine(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def DrawRectangle(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
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
                self.layers[layer].SetPixel(x, y, color, size=self.penSize, clip=self.selection)
            else:
                self.layers[layer].Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
        elif center:
            self.layers[layer].Rectangle(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
        else:
            self.layers[layer].Rectangle(x, y, w, h, color, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.DrawRectangle(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.DrawRectangle(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def DrawEllipse(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
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
                self.layers[layer].SetPixel(x, y, color, size=self.penSize, clip=self.selection)
            else:
                self.layers[layer].Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
        elif center:
            self.layers[layer].Ellipse(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
        else:
            self.layers[layer].Ellipse(x, y, w, h, color, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.DrawEllipse(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.DrawEllipse(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def SetPenColor(self, color):
        self.penColor = self.StoreColor(color)

    def SetEraserColor(self, color):
        self.eraserColor = self.StoreColor(color)

    def PixelAtPosition(self, x, y, func=int):
        return (func((x - self.panx) / self.pixel_size),
                func((y - self.pany) / self.pixel_size))

    def AdjustBrushSize(self, amount):
        self.penSize += amount
        if self.penSize<1:
            self.penSize = 1
            
        self.Refresh()
        
    def ChangePenColor(self, color):
        self.penColor = self.StoreColor(color)
        for l in self.listeners:
            l.PenColorChanged(color)

    def ChangeEraserColor(self, color):
        self.eraserColor = self.StoreColor(color)
        for l in self.listeners:
            l.EraserColorChanged(color)

    def Select(self, region=None):
        self.lastSelection = None
        if not region: # Select All
            self.selection = wx.Region(0,0,self.layers["width"], self.layers["height"])
        else:
            if self.selection and not self.selection.IsEmpty(): # Deselection
                self.lastSelection = self.selection
            self.selection = region
            
    def Reselect(self):
        if not self.selection or self.selection.IsEmpty():
            self.selection = self.lastSelection
            self.lastSelection = None
            
    def SelectInvert(self):
        s = wx.Region(0, 0, self.layers["width"], self.layers["height"])
        s.Subtract(self.selection)
        self.selection = s
        
    def UpdateSelection(self, x0, y0, x1, y1, subtract=False):
        minx, maxx = minmax(x0, x1)
        miny, maxy = minmax(y0, y1)
        minx, miny = self.PixelAtPosition(minx, miny)
        maxx, maxy = self.PixelAtPosition(maxx, maxy, ceil)
        if subtract:
            self.selection.Subtract(wx.Rect(minx, miny, maxx - minx, maxy - miny))
        else:
            self.selection.Union(minx, miny, maxx - minx, maxy - miny)
            
        self.selection.Intersect(0, 0, self.layers["width"], self.layers["height"])
        
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

        self.full_redraw = True
        self.Refresh()

    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.prevgx, self.prevgy = gx, gy

        # draw with 1st color
        if self.mouseState == 1:
            if self.current_tool == "Pen":
                if e.AltDown():
                    color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                    self.ChangePenColor(color)
                else:
                    self.DrawLine("drawing", *self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.penColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Rectangle":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawRectangle("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor, equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor,
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Move":
                self.movex, self.movey = x - self.origx, y - self.origy
                # move in grid spaces
                self.movex -= self.movex % self.pixel_size
                self.movey -= self.movey % self.pixel_size
            elif self.current_tool == "Picker":
                color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                self.ChangePenColor(color)

        # draw with 2nd color
        elif self.mouseState == 2:
            if self.current_tool == "Pen":
                if e.AltDown():
                    color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                    self.ChangeEraserColor(color)
                else:
                    self.DrawLine("drawing", *self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.eraserColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                              self.eraserColor)
            elif self.current_tool == "Rectangle":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawRectangle("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 self.eraserColor, equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(COLOR_BLANK)
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 self.eraserColor, equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Picker":
                color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                self.ChangeEraserColor(color)
            elif self.current_tool == "Sel Rect":
                px, py = self.PixelAtPosition(self.prevx, self.prevy)
                if not self.selection.IsEmpty():
                    self.selection.Offset(gx - px, gy - py)

        elif self.mouseState == 3:
            self.panx += x - self.prevx
            self.pany += y - self.prevy

            self.full_redraw = True

        self.prevx, self.prevy = x, y

        self.Refresh()

    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 1
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = Layer(self.layers["current"])

        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangePenColor(color)
            else:
                self.DrawPixel("drawing", gx, gy, self.penColor)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangePenColor(color)
            else:
                self.DrawPixel("drawing", gx, gy, self.penColor)
        elif self.current_tool == "Move":
            self.layers["drawing"].Draw(self.layers["current"], clip=self.selection)
            if not e.ControlDown():
                self.layers["current"].Clear(self.eraserColor, clip=self.selection)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangePenColor(color)
            else:
                self.Blit("current", "drawing")
                self.layers["current"].Clear(COLOR_BLANK)
                self.FloodFill("drawing", gx, gy, self.penColor)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers["current"].GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Sel Rect":
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
        if self.current_tool in ("Pen", "Line", "Ellipse", "Rectangle"):
            self.Blit("drawing", "current")
        elif self.current_tool == "Bucket":
            self.Blit("drawing", "current")
        elif self.current_tool == "Move":
            self.Blit("drawing", "current", int(self.movex / self.pixel_size), int(self.movey / self.pixel_size))
            if not self.selection.IsEmpty():
                ox, oy = self.PixelAtPosition(self.origx, self.origy)
                self.selection.Offset(int(self.movex / self.pixel_size), int(self.movey / self.pixel_size))
        elif self.current_tool == "Sel Rect":
            self.UpdateSelection(x, y, self.origx, self.origy, e.AltDown())

        self.movex, self.movey = 0, 0

        self.layers["drawing"].Clear(COLOR_BLANK)

        # create an undo command
        if not self.noUndo:
            self.history.Store(LayerCommand(self.layers, self.beforeLayer, Layer(self.layers["current"])))
        self.beforeLayer = None

        self.noUndo = False

        self.Refresh()

    def OnRightDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)
        self.mouseState = 2

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = Layer(self.layers["current"])

        # put a dot
        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangeEraserColor(color)
            else:
                self.DrawPixel("drawing", gx, gy, self.eraserColor)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangeEraserColor(color)
            else:
                self.DrawPixel("drawing", gx, gy, self.eraserColor)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers["current"].GetPixel(gx, gy)
            self.ChangeEraserColor(color)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangeEraserColor(color)
            else:
                self.Blit("current", "drawing")
                self.layers["current"].Clear(COLOR_BLANK)
                self.FloodFill("drawing", gx, gy, self.eraserColor)
        elif self.current_tool == "Sel Rect":
            self.noUndo = True
            if not self.selection.Contains(gx, gy):
                self.Select(wx.Region())

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnRightUp(self, e):
        x, y = e.GetPosition()
        self.mouseState = 0

        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool in ("Pen", "Line", "Rectangle", "Ellipse", "Bucket"):
            self.Blit("drawing", "current")

        self.movex, self.movey = 0, 0

        self.layers["drawing"].Clear(COLOR_BLANK)

        # create an undo command
        if not self.noUndo:
            self.history.Store(LayerCommand(self.layers, self.beforeLayer, Layer(self.layers["current"])))
            self.noUndo = True
            
        self.beforeLayer = None
        self.Refresh()

    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 3
        self.noUndo = False

    def OnMiddleUp(self, e):
        self.mouseState = 0
        self.noUndo = False

    def OnMouseEnter(self, e):
        self.SetFocus()
        
    def FullRedraw(self):
        self.full_redraw = True
        self.Refresh()

    def DrawBrushOnCanvas(self, gc, px, py):
        gc.SetPen(wx.NullPen)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(self.penColor))
        x, y = int(px-self.penSize/2+.5), int(py-self.penSize/2+.5)
        sz = self.penSize*self.pixel_size
        gc.DrawRectangle(self.panx+x*self.pixel_size, self.pany+y*self.pixel_size, sz, sz)
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        lw, lh = self.layers["width"], self.layers["height"]
        # PAINT WHOLE CANVAS
        if self.full_redraw:
            dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
            dc.Clear()
            self.full_redraw = False

        # PAINT RULERS
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
        dc.SetClippingRegion(self.panx, self.pany, self.layers["width"] * self.pixel_size,
                             self.layers["height"] * self.pixel_size)

        # RENDER ALPHA BACKGROUND
        dc.DrawBitmap(self.alphabg, self.panx, self.pany)
        # LAYERS
        if RENDER_CURRENT_LAYER:
            mdc = wx.MemoryDC(self.layers["current"])
            dc.StretchBlit(self.panx, self.pany,
                           self.layers["width"] * self.pixel_size, self.layers["height"] * self.pixel_size,
                           mdc,
                           0, 0,
                           lw, lh)

        # DRAWING LAYER
        if RENDER_DRAWING_LAYER:
            mdc = wx.MemoryDC(self.layers["drawing"])
            dc.StretchBlit(self.panx + self.movex, self.pany + self.movey,
                               self.layers["width"] * self.pixel_size, self.layers["height"] * self.pixel_size,
                               mdc,
                               0, 0,
                               lw, lh)

        display_selection_rect = True
        if self.mouseState == 1 and self.current_tool in ("Move"):
            display_selection_rect = False
        
        gc = wx.GraphicsContext.Create(dc)

        # DRAW BRUSH PREVIEW
        if self.mouseState == 0 and self.current_tool in ["Pen", "Line", "Rectangle", "Ellipse"]:
            self.DrawBrushOnCanvas(gc, self.prevgx, self.prevgy)
            
        # REFERENCE
        if self.layers["reference"]:
            w, h = int(self.layers["reference"].width*self.refScale), int(self.layers["reference"].height*self.refScale)
            ar = w/h
            cw, ch = self.layers["width"] * self.pixel_size, self.layers["height"] * self.pixel_size
            gc.DrawBitmap(self.layers["reference"], self.panx, self.pany, min(cw, ch*ar), min(cw/ar,ch))
            
        # GRID
        if self.gridVisible and self.pixel_size > 2:
            self.DrawGrid(gc)

        # SELECTION
        gc.SetCompositionMode(wx.COMPOSITION_XOR)
        gc.SetBrush(wx.NullBrush)
        if self.mouseState == 1 and self.current_tool == "Sel Rect":
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22222288", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawRectangle(min(self.prevx, self.origx), min(self.prevy, self.origy), abs(self.prevx - self.origx),
                             abs(self.prevy - self.origy))
        if self.selection and not self.selection.IsEmpty() and display_selection_rect:
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22222288", 2, wx.PENSTYLE_LONG_DASH))
            for r in self.selection:
                gc.DrawRectangle(r.x * self.pixel_size + self.panx,
                                 r.y * self.pixel_size + self.pany,
                                 r.width * self.pixel_size,
                                 r.height * self.pixel_size)

        # PREVIEW
        if RENDER_PREVIEW:
            dc.DestroyClippingRegion()
            w, h = e.GetEventObject().GetSize()
            # BUG? dc.GetSize provide does not reduce in size if the window is expanded and them reduced.
            
            mdc = wx.MemoryDC(self.layers["current"])
            dc.StretchBlit(w-lw, 0,
                           lw, lh,
                           mdc,
                           0, 0,
                           lw, lh)
        
    def Undo(self):
        self.history.Undo()
        self.full_redraw = True
        self.Refresh()

    def Redo(self):
        self.history.Redo()
        self.full_redraw = True
        self.Refresh()

    def IsDirty(self):
        return self.history.IsDirty()

    def New(self, pixel, width, height):
        self.palette = [COLOR_BLANK, wx.BLACK, wx.WHITE]
        self.penColor = wx.BLACK  #
        self.eraserColor = wx.WHITE  #
        self.pixel_size = pixel

        # to ensure alpha
        current_layer = Layer(wx.Bitmap.FromRGBA(width, height, 255, 255, 255, 255))
        drawing_layer = Layer(wx.Bitmap.FromRGBA(width, height, 0, 0, 0, 0))

        self.layers["width"] = width
        self.layers["height"] = height
        self.layers["drawing"] = drawing_layer
        self.layers["current"] = current_layer

        self.history.ClearCommands()

    def StoreColor(self, color):
        if color not in self.palette:
            self.palette.append(color)
        return color

    def Resize(self, width, height):
        if width == self.layers["width"] and height == self.layers["height"]:
            return

        bgcolor = self.eraserColor
        current_layer = Layer(wx.Bitmap.FromRGBA(width, height, bgcolor.red, bgcolor.green, bgcolor.blue, bgcolor.alpha))
        current_layer.Blit(self.layers["current"])

        drawing_layer = Layer(wx.Bitmap.FromRGBA(width, height, 0, 0, 0, 0))

        cmd = ResizeCommand(self.layers, Layer(self.layers["current"]), Layer(current_layer))
        self.history.Store(cmd)

        self.layers["width"] = width
        self.layers["height"] = height
        self.layers["drawing"] = drawing_layer
        self.layers["current"] = current_layer

        self.full_redraw = True
        self.Refresh()

    def LoadRefImage(self, filename):
        image = Image.open(filename)
        image.putalpha(int(self.refAlpha*255))
        
        self.layers["reference"] = Layer(wx.Bitmap.FromBufferRGBA(*image.size, image.tobytes()))

    def RemoveRefImage(self, e):
        self.layers["reference"] = None
        self.Refresh()

    def Load(self, pixel, filename):
        image = wx.Image(filename)
        self.pixel_size = pixel
        width, height = int(image.GetWidth() / pixel), int(image.GetHeight() / pixel)

        self.New(pixel, width, height)

        self.layers["current"].Load(filename)

        self.history.ClearCommands()

        print('Loaded:', filename)

    def Save(self, filename):
        self.layers["current"].Scaled(self.pixel_size).SaveFile(filename, wx.BITMAP_TYPE_PNG)
        self.history.MarkAsSaved()

    def SaveGif(self, filename):
        images = []
        wxImage = self.history.GetCommands()[0].before.Scaled(self.pixel_size).ConvertToImage()
        pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
        pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
        images.append(pilImage)

        for cmd in self.history.GetCommands():
            wxImage = cmd.after.Scaled(self.pixel_size).ConvertToImage()
            pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
            pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
            images.append(pilImage)
        images[0].save(filename, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)

    def SetTool(self, tool):
        self.current_tool = tool
        self.SetCursor(wx.Cursor(TOOLS[tool][0]))

    def ScrollToMiddle(self, size):
        self.panx = int(size[0] / 2 - self.layers["width"] * self.pixel_size / 2)
        self.pany = int(size[1] / 2 - self.layers["height"] * self.pixel_size / 2)

        if self.panx < 0:
            self.panx = 30
        if self.pany < 0:
            self.pany = 30

    def GetMirror(self, bitmap, horizontally=True):
        return bitmap.ConvertToImage().Mirror(horizontally).ConvertToBitmap()

    def OnMirrorTR(self, e):
        before = Layer(self.layers["current"])
        after = Layer(self.GetMirror(before))
        after.Draw(before, wx.Region(0, 0, int(before.width / 2), before.height))

        self.history.Store(LayerCommand(self.layers, before, Layer(after)))
        self.layers["current"] = after

        self.Refresh()

    def OnMirrorTB(self, e):
        before = Layer(self.layers["current"])
        after = Layer(self.GetMirror(before, False))
        after.Draw(before, wx.Region(0, 0, before.width, int(before.height / 2)))

        self.history.Store(LayerCommand(self.layers, before, Layer(after)))
        self.layers["current"] = after

        self.Refresh()

    def OnFlipH(self, e):
        before = Layer(self.layers["current"])
        after = self.GetMirror(before)

        self.history.Store(LayerCommand(self.layers, before, Layer(after)))
        self.layers["current"].Draw(after)

        self.Refresh()

    def Rotate90(self, e, clockwise=True):
        before = Layer(self.layers["current"])
        image = before.ConvertToImage()
        image = image.Rotate90(clockwise)
        after = image.ConvertToBitmap()

        self.history.Store(LayerCommand(self.layers, before, Layer(after)))
        self.layers["current"].Draw(after)

        self.Refresh()

class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=PROGRAM_NAME, size=WINDOW_SIZE)

        self.FirstTimeResize = True

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        self.canvas = Canvas(self)
        self.canvas.New(DEFAULT_PIXEL_SIZE, *DEFAULT_DOC_SIZE)
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
        
        mselect = wx.Menu()
        mbar.Append(mselect, "&Selection")
        self.AddMenuItem(mselect, "Select &All\tCTRL+A", self.OnSelectAll)
        self.AddMenuItem(mselect, "&Deselect\tCTRL+SHIFT+A", self.OnDeselect)
        self.AddMenuItem(mselect, "&Reselect\tCTRL+SHIFT+D", self.OnReselect)
        self.AddMenuItem(mselect, "&Invert Selection\tCTRL+SHIFT+I", self.OnSelectInvert)

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
        self.eraserbtn = self.AddToolButton(tb, 'Background Color', self.OnEraser, icon=wx.Bitmap("icons/backcolor.png"))
        
        bcb = wx.adv.BitmapComboBox(tb, style=wx.CB_READONLY)
        for k, v in TOOLS.items():
            bcb.Append(k, wx.Bitmap("icons/"+v[1]))
        self.Bind(wx.EVT_COMBOBOX, self.OnTool, id=bcb.GetId())
        bcb.SetSelection(0)
        tb.AddControl(bcb)
        
        self.AddToggleButton(tb, 'Grid', self.OnToggleGrid, icon=wx.Bitmap("icons/grid.png"), default=True)
        self.AddToggleButton(tb, 'Mirror X', self.OnMirrorX, icon=wx.Bitmap("icons/mirrorx.png"))
        self.AddToggleButton(tb, 'Mirror Y', self.OnMirrorY, icon=wx.Bitmap("icons/mirrory.png"))
        self.AddToolButton(tb, 'Center', self.OnCenter, icon=wx.Bitmap("icons/center.png"))

        tb.Realize()

        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.canvas, wx.ID_ANY, wx.EXPAND | wx.ALL, 2)
        self.SetSizer(bs)

    def AddMenuItem(self, menu, name, func):
        menu.Append(self.menuid, name)
        menu.Bind(wx.EVT_MENU, func, id=self.menuid)
        self.menuid += 1

    def OnColor(self, e):
        bitmap = self.colorbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        color = mdc.GetPixel(1, 1)
        
        data = wx.ColourData()
        data.SetColour(color)
        #data.SetChooseFull(True)
        dlg = CCD.CubeColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            #self.canvas.SetPenColor(color.GetAsString(wx.C2S_HTML_SYNTAX))
            self.canvas.SetPenColor(color)
            clip = wx.Region(0,0,32,32)
            clip.Subtract(wx.Rect(9, 9, 14, 14))
            mdc.SetDeviceClippingRegion(clip)
            mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
            mdc.SetPen(wx.NullPen)
            mdc.DrawRectangle(0,0,32,32)
            mdc.SelectObject(wx.NullBitmap)
            self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)
            
    def OnEraser(self, e):
        bitmap = self.eraserbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        color = mdc.GetPixel(1, 1)
        
        data = wx.ColourData()
        data.SetColour(color)
        data.SetChooseFull(True)
        dlg = CCD.CubeColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            #self.canvas.SetEraserColor(color.GetAsString(wx.C2S_HTML_SYNTAX))
            self.canvas.SetEraserColor(color)
            clip = wx.Region(0,0,32,32)
            clip.Subtract(wx.Rect(9, 9, 14, 14))
            mdc.SetDeviceClippingRegion(clip)
            mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
            mdc.SetPen(wx.NullPen)
            mdc.DrawRectangle(0,0,32,32)
            mdc.SelectObject(wx.NullBitmap)
            self.toolbar.SetToolNormalBitmap(self.eraserbtn.GetId(), bitmap)

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
        self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)

    def EraserColorChanged(self, color):
        bitmap = self.eraserbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        clip = wx.Region(0,0,32,32)
        clip.Subtract(wx.Rect(9, 9, 14, 14))
        mdc.SetDeviceClippingRegion(clip)
        mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        mdc.SetPen(wx.NullPen)
        mdc.DrawRectangle(0,0,32,32)
        mdc.SelectObject(wx.NullBitmap)
        self.toolbar.SetToolNormalBitmap(self.eraserbtn.GetId(), bitmap)

    def PixelSizeChanged(self, value):
        self.txtPixel.SetValue(str(value))

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
            self.canvas.FullRedraw()

    def OnLoad(self, e):
        if not self.CheckDirty():
            return

        ret = wx.LoadFileSelector(PROGRAM_NAME, "png", parent=self)
        if ret:
            pixel = int(self.txtPixel.GetValue())
            self.canvas.Load(pixel, ret)
            self.canvas.FullRedraw()

    def OnToggleGrid(self, e):
        self.canvas.gridVisible = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorX(self, e):
        self.canvas.mirrorx = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorY(self, e):
        self.canvas.mirrory = e.IsChecked()
        self.canvas.Refresh()

    def OnNew32x32(self, e):
        self.OnNew(e, 32, 32)
        
    def OnNew(self, e, width=None, height=None):
        if not self.CheckDirty():
            return

        try:
            self.PenColorChanged("#000000FF")
            self.EraserColorChanged("#FFFFFFFF")
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
            self.canvas.FullRedraw()
        except:
            print('OnNew error')

    def OnSave(self, e):
        ret = wx.SaveFileSelector(PROGRAM_NAME, "png", parent=self)
        if ret:
            self.canvas.Save(ret)

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
        else:
            e.Skip()

    def OnTool(self, e):
        self.canvas.SetTool(e.GetString())

    def OnCenter(self, e):
        self.canvas.ScrollToMiddle(self.canvas.Size)
        self.canvas.FullRedraw()

    def OnResize(self, e):
        if self.FirstTimeResize:
            self.OnCenter(e)
            self.FirstTimeResize = False
        self.canvas.FullRedraw()
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
        
def CreateWindows():
    global app

    app = wx.App()

    Frame().Show()

def RunProgram():
    app.MainLoop()

CreateWindows()
RunProgram()
