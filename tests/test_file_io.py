import unittest
import wx
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.mainframe import Frame
from src.settings import InitSettings, LoadSettings
from src.layermanager import Layer, LayerManager

import shutil

class TestFileIO(unittest.TestCase):
    def setUp(self):
        self.app = wx.App()
        InitSettings()
        LoadSettings('settings.ini')
        self.frame = Frame()
        self.canvas = self.frame.canvas
        self.canvas.document = LayerManager(10, 10)
        self.canvas.document.AppendSelect(Layer.CreateLayer(10, 10))

        # Create a temporary directory for test outputs
        self.output_dir = "temp_test_outputs"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        self.app.Destroy()

    def test_save_png(self):
        self.canvas.DrawPixel(5, 5, wx.BLACK)
        output_path = os.path.join(self.output_dir, "test.png")
        self.canvas.Save(output_path)
        self.assertTrue(os.path.exists(output_path))

    def test_load_png(self):
        output_path = os.path.join(self.output_dir, "test_load.png")

        # Create an image with a known pattern
        self.canvas.DrawPixel(3, 3, wx.RED)
        self.canvas.DrawPixel(7, 7, wx.BLUE)
        self.canvas.Save(output_path)

        # Clear the canvas and load the image back
        self.canvas.document.Current().Clear()
        self.canvas.Load(self.canvas.pixelSize, output_path)

        # Verify the content of the canvas
        image = self.canvas.document.Composite().ConvertToImage()
        self.assertTrue(self.are_colors_close(wx.Colour(image.GetRed(3, 3), image.GetGreen(3, 3), image.GetBlue(3, 3)), wx.RED))
        self.assertTrue(self.are_colors_close(wx.Colour(image.GetRed(7, 7), image.GetGreen(7, 7), image.GetBlue(7, 7)), wx.BLUE))
        # The background is not transparent, but white
        self.assertEqual(wx.Colour(image.GetRed(5, 5), image.GetGreen(5, 5), image.GetBlue(5, 5)), wx.WHITE)

    def are_colors_close(self, c1, c2, tolerance=5):
        return abs(c1.Red() - c2.Red()) <= tolerance and \
               abs(c1.Green() - c2.Green()) <= tolerance and \
               abs(c1.Blue() - c2.Blue()) <= tolerance

if __name__ == '__main__':
    unittest.main()
