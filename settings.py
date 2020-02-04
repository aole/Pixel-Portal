"""
settings.py
Bhupendra Aole
1/31/2020
"""

import wx
import wx.propgrid

class Settings(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Pixel Portal Settings", size=wx.Size(300,400), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        pgm = wx.propgrid.PropertyGridManager(self,
            # These and other similar styles are automatically
            # passed to the embedded wx.PropertyGrid.
            style = wx.propgrid.PG_BOLD_MODIFIED|wx.propgrid.PG_SPLITTER_AUTO_CENTER|
            # Include toolbar.
            wx.propgrid.PG_TOOLBAR |
            # Include description box.
            wx.propgrid.PG_DESCRIPTION |
            # Plus defaults.
            wx.propgrid.PGMAN_DEFAULT_STYLE)
            
        page = pgm.AddPage("First Page")
        page.Append(wx.propgrid.PropertyCategory("Category A1"))
        page.Append(wx.propgrid.IntProperty("Number", wx.propgrid.PG_LABEL, 1))
        page.Append(wx.propgrid.ColourProperty("Colour",wx.propgrid.PG_LABEL, wx.WHITE))

        page = pgm.AddPage("Second Page")
        page.Append(wx.propgrid.StringProperty("Text", wx.propgrid.PG_LABEL, "(no text)"))
        page.Append(wx.propgrid.FontProperty("Font",wx.propgrid.PG_LABEL))

if __name__ == '__main__':
    app = wx.App()
    #f = wx.Frame(None)
    s = Settings(None)
    s.ShowModal()
    #app.MainLoop()
    