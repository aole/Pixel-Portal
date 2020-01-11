"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

import colorsys
import numpy as np
from math import atan2, ceil, floor, pi
import random
import wx, wx.adv

from PIL import Image, ImageDraw

PROGRAM_NAME = "Pixel Portal"
WINDOW_SIZE = (650, 550)
NUM_UNDOS = 100

DEFAULT_DOC_SIZE = (80, 80)
DEFAULT_PIXEL_SIZE = 5

TOOLS = {"Pen": (wx.CURSOR_PENCIL, "toolpen.png"), "Sel Rect": (wx.CURSOR_CROSS, "toolselectrect.png"), "Line": (wx.CURSOR_CROSS, "toolline.png"), "Rectangle": (wx.CURSOR_CROSS, "toolrect.png"), "Ellipse": (wx.CURSOR_CROSS, "toolellipse.png"), "Move": (wx.CURSOR_SIZING, "toolmove.png"), "Bucket": (wx.CURSOR_PAINT_BRUSH, "toolbucket.png"), "Picker": (wx.CURSOR_RIGHT_ARROW, "toolpicker.png")}

#Debug
RENDER_DRAWING_LAYER = True
RENDER_CURRENT_LAYER = True

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

    def SetPixel(self, x, y, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        gc.DrawRectangle(x, y, 1, 1)

    def SetPixels(self, pixels, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        for x, y in pixels:
            gc.DrawRectangle(x, y, 1, 1)

    def Line(self, x0, y0, x1, y1, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color))
        gc.StrokeLine(x0, y0, x1, y1)

    def Rectangle(self, x, y, w, h, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color))
        gc.DrawRectangle(x, y, w, h)

    def Ellipse(self, x, y, w, h, color, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color))
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

        self.movex, self.movey = 0, 0
        self.selection = wx.Region()
        
        self.mouseState = 0

        self.current_tool = "Pen"
        self.mirrorx = False
        self.mirrory = False
        self.gridVisible = True

        self.pixel_size = DEFAULT_PIXEL_SIZE

        self.penColor = 1  #
        self.eraserColor = 2  #
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

        self.layers["current"].Clear(self.palette[self.eraserColor], self.selection)

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
            for x in range(self.panx, min(self.panx + self.layers["width"] * self.pixel_size + 1, w), midpx):
                path.MoveToPoint(x, self.pany)
                path.AddLineToPoint(x, min(self.pany + self.layers["height"] * self.pixel_size, h))
        if midpy:
            for y in range(self.pany, min(self.pany + self.layers["height"] * self.pixel_size + 1, h), midpy):
                path.MoveToPoint(self.panx, y)
                path.AddLineToPoint(min(self.panx + self.layers["width"] * self.pixel_size, w), y)
        gc.StrokePath(path)

    def GetXMirror(self, x):
        w = int(self.layers["width"] / 2)
        return ((x + 1 - w) * -1) + w

    def GetYMirror(self, y):
        h = int(self.layers["height"] / 2)
        return ((y + 1 - h) * -1) + h

    def DrawPixel(self, layer, x, y, color, canmirrorx=True, canmirrory=True):
        self.layers[layer].SetPixel(x, y, self.palette[color], self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawPixel(layer, self.GetXMirror(x), y, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawPixel(layer, x, self.GetYMirror(y), color, False, False)

    def FloodFill(self, layer, x, y, color):
        if x < 0 or y < 0 or x > self.layers["width"] - 1 or y > self.layers["height"] - 1:
            return
        if not self.selection.IsEmpty() and not self.selection.Contains(x, y):
            return

        #self.layers[layer].FloodFill(x, y, self.palette[color], self.selection)
        l = self.layers[layer]
        replace = l.GetPixel(x, y)

        color = self.palette[color]
        queue = {(x, y)}
        while queue:
            # replace current pixel
            x, y = queue.pop()
            if not self.selection or self.selection.IsEmpty() or self.selection.Contains(x, y):
                l.SetPixel(x, y, color)

                # north
                if y > 0 and l.GetPixel(x, y - 1) == replace and l.GetPixel(x, y - 1) != color:
                    queue.add((x, y - 1))
                # east
                if x < self.layers["width"] - 1 and l.GetPixel(x + 1, y) == replace and l.GetPixel(x + 1, y) != color:
                    queue.add((x + 1, y))
                # south
                if y < self.layers["height"] - 1 and l.GetPixel(x, y + 1) == replace and l.GetPixel(x, y + 1) != color:
                    queue.add((x, y + 1))
                # west
                if x > 0 and l.GetPixel(x - 1, y) == replace and l.GetPixel(x - 1, y) != color:
                    queue.add((x - 1, y))
        
    def DrawLine(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True):
        self.layers[layer].Line(x0, y0, x1, y1, self.palette[color], self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawLine(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawLine(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def DrawRectangle(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        if equal and w!=h:
            w = h = min(w,h)
            x1 = x0+w
            y1 = y0+h
        if w==0 or h==0:
            if w==0 and h==0:
                self.layers[layer].SetPixel(x, y, self.palette[color], self.selection)
            else:
                self.layers[layer].Line(x0, y0, x1, y1, self.palette[color], self.selection)
                
        self.layers[layer].Rectangle(x, y, w, h, self.palette[color], self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawRectangle(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawRectangle(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def DrawEllipse(self, layer, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        if equal and w!=h:
            w = h = min(w,h)
            x1 = x0+w
            y1 = y0+h
        if w==0 or h==0:
            if w==0 and h==0:
                self.layers[layer].SetPixel(x, y, self.palette[color], self.selection)
            else:
                self.layers[layer].Line(x0, y0, x1, y1, self.palette[color], self.selection)
                
        self.layers[layer].Ellipse(x, y, w, h, self.palette[color], self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawEllipse(layer, self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawEllipse(layer, x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def GetPenColor(self):
        return self.palette[self.penColor]

    def GetEraserColor(self):
        return self.palette[self.eraserColor]

    def SetPenColor(self, color):
        color = color + "FF"
        if color not in self.palette:
            self.penColor = len(self.palette)
            self.palette.append(color)
        else:
            self.penColor = self.palette.index(color)

    def SetEraserColor(self, color):
        color = color + "FF"
        if color not in self.palette:
            self.eraserColor = len(self.palette)
            self.palette.append(color)
        else:
            self.eraserColor = self.palette.index(color)

    def PixelAtPosition(self, x, y, func=int):
        return (func((x - self.panx) / self.pixel_size),
                func((y - self.pany) / self.pixel_size))

    def ChangePenColor(self, color):
        self.penColor = self.ColorIndex(color.GetAsString(wx.C2S_HTML_SYNTAX))
        for l in self.listeners:
            l.PenColorChanged(color)

    def ChangeEraserColor(self, color):
        self.eraserColor = self.ColorIndex(color.GetAsString(wx.C2S_HTML_SYNTAX))
        for l in self.listeners:
            l.EraserColorChanged(color)

    def ResetSelection(self):
        self.selection = wx.Region()

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

        # draw with 1st color
        if self.mouseState == 1:
            if self.current_tool == "Pen":
                if e.AltDown():
                    color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                    self.ChangePenColor(color)
                else:
                    self.DrawLine("drawing", *self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.penColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Rectangle":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawRectangle("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor, equal=e.ShiftDown())
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor, equal=e.ShiftDown())
            elif self.current_tool == "Move":
                self.movex, self.movey = x - self.origx, y - self.origy
                # move in grid spaces
                self.movex -= self.movex % self.pixel_size
                self.movey -= self.movey % self.pixel_size
            elif self.current_tool == "Picker":
                color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                self.ChangePenColor(color)

            self.Refresh()

        # draw with 2nd color
        elif self.mouseState == 2:
            if self.current_tool == "Pen":
                if e.AltDown():
                    color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                    self.ChangeEraserColor(color)
                else:
                    self.DrawLine("drawing", *self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.eraserColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                              self.eraserColor)
            elif self.current_tool == "Rectangle":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawRectangle("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 self.eraserColor, equal=e.ShiftDown())
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 self.eraserColor, equal=e.ShiftDown())
            elif self.current_tool == "Picker":
                color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                self.ChangeEraserColor(color)
            elif self.current_tool == "Sel Rect":
                px, py = self.PixelAtPosition(self.prevx, self.prevy)
                if not self.selection.IsEmpty():
                    self.selection.Offset(gx - px, gy - py)

            self.Refresh()

        elif self.mouseState == 3:
            self.panx += x - self.prevx
            self.pany += y - self.prevy

            self.full_redraw = True
            self.Refresh()

        self.prevx, self.prevy = x, y

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
            self.DrawPixel("drawing", gx, gy, self.penColor)
        elif self.current_tool == "Move":
            self.layers["drawing"].Draw(self.layers["current"], self.selection)
            if not e.ControlDown():
                self.layers["current"].Clear(self.palette[self.eraserColor], self.selection)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.layers["current"].GetPixel(gx, gy)
                self.ChangePenColor(color)
            else:
                self.Blit("current", "drawing")
                self.layers["current"].Clear(self.palette[0])
                self.FloodFill("drawing", gx, gy, self.penColor)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers["current"].GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Sel Rect":
            if not e.ControlDown() and not e.AltDown():
                self.selection = wx.Region()

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def UpdateSelectionRect(self, x0, y0, x1, y1, subtract=False):
        minx, maxx = minmax(x0, x1)
        miny, maxy = minmax(y0, y1)
        minx, miny = self.PixelAtPosition(minx, miny)
        maxx, maxy = self.PixelAtPosition(maxx, maxy, ceil)
        if subtract:
            self.selection.Subtract(wx.Rect(minx, miny, maxx - minx, maxy - miny))
        else:
            self.selection.Union(minx, miny, maxx - minx, maxy - miny)
            
        self.selection.Intersect(0, 0, self.layers["width"], self.layers["height"])
        
    def OnLeftUp(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.mouseState = 0

        self.noUndo = False
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
            self.noUndo = True
            self.UpdateSelectionRect(x, y, self.origx, self.origy, e.AltDown())

        self.movex, self.movey = 0, 0

        self.layers["drawing"].Clear(self.palette[0])

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
        elif self.current_tool in ["Line", "Ellipse"]:
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
                self.layers["current"].Clear(self.palette[0])
                self.FloodFill("drawing", gx, gy, self.eraserColor)
        elif self.current_tool == "Sel Rect":
            self.noUndo = True
            if not self.selection.Contains(gx, gy):
                self.ResetSelection()

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnRightUp(self, e):
        x, y = e.GetPosition()
        self.mouseState = 0

        self.noUndo = True
        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool in ("Pen", "Line", "Rectangle", "Ellipse", "Bucket"):
            self.Blit("drawing", "current")
            self.noUndo = False

        self.movex, self.movey = 0, 0

        self.layers["drawing"].Clear(self.palette[0])

        # create an undo command
        if not self.noUndo:
            self.history.Store(LayerCommand(self.layers, self.beforeLayer, Layer(self.layers["current"])))
            self.noUndo = False
            
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

    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        
        # PAINT WHOLE CANVAS
        if self.full_redraw:
            dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
            dc.Clear()
            self.full_redraw = False

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
                           self.layers["width"], self.layers["height"])

        # DRAWING LAYER
        if RENDER_DRAWING_LAYER:
            mdc = wx.MemoryDC(self.layers["drawing"])
            dc.StretchBlit(self.panx + self.movex, self.pany + self.movey,
                               self.layers["width"] * self.pixel_size, self.layers["height"] * self.pixel_size,
                               mdc,
                               0, 0,
                               self.layers["width"], self.layers["height"])

        display_selection_rect = True
        if self.mouseState == 1 and self.current_tool in ("Move"):
            display_selection_rect = False
        
        gc = wx.GraphicsContext.Create(dc)

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
        if self.mouseState == 1 and self.current_tool == "Sel Rect":
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22222288", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawRectangle(min(self.prevx, self.origx), min(self.prevy, self.origy), abs(self.prevx - self.origx),
                             abs(self.prevy - self.origy))
        if not self.selection.IsEmpty() and display_selection_rect:
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22222288", 2, wx.PENSTYLE_LONG_DASH))
            for r in self.selection:
                gc.DrawRectangle(r.x * self.pixel_size + self.panx,
                                 r.y * self.pixel_size + self.pany,
                                 r.width * self.pixel_size,
                                 r.height * self.pixel_size)

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
        self.palette = ["#00000000", "#000000FF", "#FFFFFFFF"]
        self.penColor = 1  #
        self.eraserColor = 2  #
        self.pixel_size = pixel

        # to ensure alpha
        current_layer = Layer(wx.Bitmap.FromRGBA(width, height, 255, 255, 255, 255))
        drawing_layer = Layer(wx.Bitmap.FromRGBA(width, height, 0, 0, 0, 0))

        self.layers["width"] = width
        self.layers["height"] = height
        self.layers["drawing"] = drawing_layer
        self.layers["current"] = current_layer

        self.history.ClearCommands()

    def ColorIndex(self, color):
        if len(color) == 7:
            color += "FF"
        if color not in self.palette:
            self.palette.append(color)
            return len(self.palette) - 1
        else:
            return self.palette.index(color)

    def Resize(self, width, height):
        if width == self.layers["width"] and height == self.layers["height"]:
            return

        current_layer = Layer(wx.Bitmap.FromRGBA(width, height, 255, 255, 255, 255))
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

        if self.panx < 10:
            self.panx = 10
        if self.pany < 10:
            self.pany = 10

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
        
class ColorPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.mouseState = 0

        self.lightness = 1.0
        self.backgroundBrush = wx.TheBrushList.FindOrCreateBrush("#998877FF")
        self.padding = 5

        self.image = self.Parent.colorImage.AdjustChannels(self.lightness, self.lightness, self.lightness)
        self.bitmap = wx.Bitmap(self.image, 24)
        self.blitw, self.blith = 0, 0

    def OnMouseMove(self, e):
        if self.mouseState == 1:
            x, y = e.GetPosition()
            iw, ih = self.bitmap.GetSize()
            sw, sh = self.blitw, self.blith
            x, y = x - self.padding, y - self.padding
            x = int(x * iw / sw)
            y = int(y * ih / sh)
            if x >= 0 and x < iw and y >= 0 and y < ih:
                print(self.image.GetRed(x, y), self.image.GetGreen(x, y), self.image.GetBlue(x, y))

    def OnLeftDown(self, e):
        self.mouseState = 1

    def OnLeftUp(self, e):
        self.mouseState = 0

    def OnPaint(self, e):
        if self.blitw < 1 or self.blith < 1:
            return

        dc = wx.PaintDC(self)
        dc.SetBackground(self.backgroundBrush)
        dc.Clear()

        iw, ih = self.bitmap.GetSize()

        mdc = wx.MemoryDC(self.bitmap)
        dc.StretchBlit(self.padding, self.padding,
                       self.blitw, self.blith,
                       mdc,
                       0, 0,
                       iw, ih)

    def OnSize(self, e):
        iw, ih = self.bitmap.GetSize()
        ar = iw / ih

        w, h = e.GetSize()
        m = min(w - self.padding * 2, h * ar - self.padding * 2)

        self.blitw, self.blith = m, m / ar
        self.Refresh()

class ColorDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, size=(300, 300), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)  # | wx.STAY_ON_TOP)

        self.CreateColorWheel(0.5)

        cp = ColorPanel(self)
        cp.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        cp.Bind(wx.EVT_PAINT, cp.OnPaint)
        cp.Bind(wx.EVT_SIZE, cp.OnSize)

        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(cp, wx.ID_ANY, wx.EXPAND | wx.ALL, 2)
        self.SetSizer(bs)

    def CreateColorWheel(self, lightness):
        imgw, imgh = 1000, 1000
        w, h = imgw + 100, imgh

        c = imgw / 2, imgh / 2
        r = min(imgw, imgh) / 2

        data = []
        alpha = []
        for y in range(h):
            for x in range(w):
                rx = x - c[0]
                ry = y - c[1]
                s = ((x - c[0]) ** 2.0 + (y - c[1]) ** 2.0) ** 0.5

                if x < imgw and s <= r:  # 1.0:
                    hue = ((atan2(ry, rx) / pi) + 1.0) / 2.0
                    rgb = colorsys.hsv_to_rgb(hue, s / r, 1.0)
                    data.extend((int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)))
                    alpha.append(255)
                else:
                    if x >= imgw + 20 and x < imgw + 50:
                        col = int(((h - 1) - y) * 255 / (h - 1))
                        data.extend((col, col, col))
                        alpha.append(255)
                    elif x >= imgw + 70 and x < imgw + 100:
                        col = int(((h - 1) - y) * 255 / (h - 1))
                        data.extend((255, 255, 255))
                        alpha.append(col)
                    else:
                        data.extend((0, 0, 0))
                        alpha.append(0)

        image = wx.Image(w, h, bytearray(data), bytearray(alpha))
        self.colorImage = image

class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=PROGRAM_NAME, size=WINDOW_SIZE)

        self.FirstTimeResize = True

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        self.canvas = Canvas(self)
        self.canvas.New(DEFAULT_PIXEL_SIZE, *DEFAULT_DOC_SIZE)
        self.canvas.listeners.append(self)

        self.testDialog = ColorDialog(self)

        # MENU
        self.menuid = 20001

        mbar = wx.MenuBar()

        medit = wx.Menu()
        mbar.Append(medit, "Edit")
        self.AddMenuItem(medit, "Flip Horizontal", self.canvas.OnFlipH)
        self.AddMenuItem(medit, "Mirror to Right", self.canvas.OnMirrorTR)
        self.AddMenuItem(medit, "Mirror Down", self.canvas.OnMirrorTB)
        self.AddMenuItem(medit, "Reference Image ...", self.OnRefImage)
        self.AddMenuItem(medit, "Remove Reference Image", self.canvas.RemoveRefImage)
        self.AddMenuItem(medit, "Rotate 90 CW", self.canvas.Rotate90)

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
        self.AddToolButton(tb, 'T', self.OnTest, icon=wx.Bitmap("icons/NA.png"))

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
        data.SetChooseFull(True)
        #data.SetChooseAlpha(True)
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            self.canvas.SetPenColor(color.GetAsString(wx.C2S_HTML_SYNTAX))
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
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            self.canvas.SetEraserColor(color.GetAsString(wx.C2S_HTML_SYNTAX))
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

    def OnMirrorY(self, e):
        self.canvas.mirrory = e.IsChecked()

    def OnNew(self, e):
        if not self.CheckDirty():
            return

        try:
            self.PenColorChanged("#000000FF")
            self.EraserColorChanged("#FFFFFFFF")
            pixel = int(self.txtPixel.GetValue())
            width = int(self.txtWidth.GetValue())
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
                return

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

    def OnTest(self, e):
        self.testDialog.SetTitle('Color')
        self.testDialog.Show()

def CreateWindows():
    global app

    app = wx.App()

    Frame().Show()

def RunProgram():
    app.MainLoop()

CreateWindows()
RunProgram()
