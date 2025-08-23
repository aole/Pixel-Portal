import unittest
import wx
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.mainframe import Frame
from src.settings import InitSettings, LoadSettings

from src.layermanager import Layer, LayerManager

class TestDrawing(unittest.TestCase):
    def setUp(self):
        self.app = wx.App()
        InitSettings()
        LoadSettings('settings.ini')
        self.frame = Frame()
        self.canvas = self.frame.canvas
        self.canvas.document = LayerManager(10, 10)
        self.canvas.document.AppendSelect(Layer.CreateLayer(10, 10))


    def tearDown(self):
        self.app.Destroy()

    def test_draw_pixel(self):
        self.canvas.DrawPixel(5, 5, wx.BLACK)

        # Get the composite image from the canvas
        image = self.canvas.document.Composite().ConvertToImage()

        # Check the pixel color
        pixel_color = wx.Colour(image.GetRed(5, 5), image.GetGreen(5, 5), image.GetBlue(5, 5))
        self.assertEqual(pixel_color, wx.BLACK)
        self.assertEqual(image.GetAlpha(5,5), 255)
        # Check a transparent pixel
        self.assertEqual(image.GetAlpha(1, 1), 0)

    def test_draw_line(self):
        self.canvas.DrawLine(1, 1, 8, 8, wx.BLACK)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check a few pixels on the line
        self.assertEqual(wx.Colour(image.GetRed(1, 1), image.GetGreen(1, 1), image.GetBlue(1, 1)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(5, 5), image.GetGreen(5, 5), image.GetBlue(5, 5)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(8, 8), image.GetGreen(8, 8), image.GetBlue(8, 8)), wx.BLACK)
        # Check a transparent pixel
        self.assertEqual(image.GetAlpha(2, 1), 0)

    def test_draw_rectangle(self):
        self.canvas.DrawRectangle(2, 2, 7, 7, wx.BLACK)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check a few pixels on the rectangle
        self.assertEqual(wx.Colour(image.GetRed(2, 2), image.GetGreen(2, 2), image.GetBlue(2, 2)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(8, 2), image.GetGreen(8, 2), image.GetBlue(8, 2)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(2, 8), image.GetGreen(2, 8), image.GetBlue(2, 8)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(8, 8), image.GetGreen(8, 8), image.GetBlue(8, 8)), wx.BLACK)
        # Check a pixel inside the rectangle (should be transparent)
        self.assertEqual(image.GetAlpha(5, 5), 0)

    def test_draw_ellipse(self):
        self.canvas.document = LayerManager(20, 20)
        self.canvas.document.AppendSelect(Layer.CreateLayer(20, 20))
        self.canvas.DrawEllipse(5, 5, 15, 15, wx.BLACK)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check some pixels on the ellipse
        self.assertEqual(wx.Colour(image.GetRed(12, 5), image.GetGreen(12, 5), image.GetBlue(12, 5)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(5, 12), image.GetGreen(5, 12), image.GetBlue(5, 12)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(19, 12), image.GetGreen(19, 12), image.GetBlue(19, 12)), wx.BLACK)
        self.assertEqual(wx.Colour(image.GetRed(12, 19), image.GetGreen(12, 19), image.GetBlue(12, 19)), wx.BLACK)
        # Check a pixel inside the ellipse (should be transparent)
        self.assertEqual(image.GetAlpha(12, 12), 0)

    def test_flood_fill(self):
        self.canvas.DrawRectangle(2, 2, 7, 7, wx.BLACK)
        self.canvas.FloodFill(5, 5, wx.RED)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check a pixel inside the filled area
        self.assertEqual(wx.Colour(image.GetRed(5, 5), image.GetGreen(5, 5), image.GetBlue(5, 5)), wx.RED)
        # Check a pixel on the border
        self.assertEqual(wx.Colour(image.GetRed(2, 2), image.GetGreen(2, 2), image.GetBlue(2, 2)), wx.BLACK)
        # Check a pixel outside the filled area
        self.assertEqual(image.GetAlpha(1, 1), 0)

    def test_erase_pixel(self):
        self.canvas.DrawPixel(5, 5, wx.BLACK)
        self.canvas.ErasePixel(5, 5)
        image = self.canvas.document.Composite().ConvertToImage()
        self.assertEqual(image.GetAlpha(5, 5), 0)

    def test_erase_line(self):
        self.canvas.DrawLine(1, 1, 8, 8, wx.BLACK)
        self.canvas.EraseLine(1, 1, 8, 8)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check a few pixels on the line
        self.assertEqual(image.GetAlpha(1, 1), 0)
        self.assertEqual(image.GetAlpha(5, 5), 0)
        self.assertEqual(image.GetAlpha(8, 8), 0)

    def test_erase_rectangle(self):
        self.canvas.DrawRectangle(2, 2, 7, 7, wx.BLACK)
        self.canvas.EraseRectangle(2, 2, 7, 7)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check a few pixels on the rectangle
        self.assertEqual(image.GetAlpha(2, 2), 0)
        self.assertEqual(image.GetAlpha(8, 2), 0)
        self.assertEqual(image.GetAlpha(2, 8), 0)
        self.assertEqual(image.GetAlpha(8, 8), 0)

    def test_erase_ellipse(self):
        self.canvas.document = LayerManager(20, 20)
        self.canvas.document.AppendSelect(Layer.CreateLayer(20, 20))
        self.canvas.DrawEllipse(5, 5, 15, 15, wx.BLACK)
        self.canvas.EraseEllipse(5, 5, 15, 15)
        image = self.canvas.document.Composite().ConvertToImage()
        # Check some pixels on the ellipse
        self.assertEqual(image.GetAlpha(12, 5), 0)
        self.assertEqual(image.GetAlpha(5, 12), 0)
        self.assertEqual(image.GetAlpha(19, 12), 0)
        self.assertEqual(image.GetAlpha(12, 19), 0)

if __name__ == '__main__':
    unittest.main()
