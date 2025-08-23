"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

import wx

class MenuBar(wx.MenuBar):
    def __init__(self, parent):
        super().__init__()

        self.menuid = 20001

        mfile = wx.Menu()
        self.Append(mfile, "&File")

        self.AddMenuItem(mfile, "New\tCtrl+N", parent.OnNew)
        self.AddMenuItem(mfile, "Open\tCtrl+O", parent.OnOpen)
        self.AddMenuItem(mfile, "Save\tCtrl+S", parent.OnSave)
        self.AddMenuItem(mfile, "Save As\tCtrl+Alt+S", parent.OnSaveAs)
        self.AddMenuItem(mfile, "Export Animation\tCtrl+E",
                         parent.OnExportAnimation)
        self.AddMenuItem(mfile, "Export History as Animation",
                         parent.OnExportHistory)
        mfile.AppendSeparator()
        self.AddMenuItem(mfile, "Exit\tAlt+F4", parent.OnClose)

        medit = wx.Menu()
        self.Append(medit, "&Edit")
        self.AddMenuItem(medit, "Flip Horizontal", parent.canvas.OnFlipH)
        self.AddMenuItem(medit, "Mirror to Right", parent.canvas.OnMirrorTR)
        self.AddMenuItem(medit, "Mirror Down", parent.canvas.OnMirrorTB)
        self.AddMenuItem(medit, "Reference Image ...", parent.OnRefImage)
        self.AddMenuItem(medit, "Remove Reference Image",
                         parent.canvas.RemoveRefImage)
        self.AddMenuItem(medit, "Rotate 90 CW", parent.canvas.Rotate90)
        self.AddMenuItem(medit, "Crop to Selection",
                         parent.canvas.OnCropToSelection)
        medit.AppendSeparator()
        self.AddMenuItem(medit, "Settings ...", parent.OnSettings)

        mselect = wx.Menu()
        self.Append(mselect, "&Selection")
        self.AddMenuItem(mselect, "Select &All\tCtrl+A", parent.OnSelectAll)
        self.AddMenuItem(mselect, "&Deselect\tCtrl+D", parent.OnDeselect)
        self.AddMenuItem(mselect, "&Reselect\tCtrl+Shift+D", parent.OnReselect)
        self.AddMenuItem(
            mselect, "&Invert Selection\tCtrl+Shift+I", parent.OnSelectInvert)

        menu = wx.Menu()
        self.Append(menu, "&Layer")
        self.AddMenuItem(menu, "&Add Layer\tCtrl+Shift+N", parent.OnAddLayer)
        self.AddMenuItem(menu, "&Duplicate Layer\tCtrl+J",
                         parent.OnDuplicateLayer)
        self.AddMenuItem(menu, "&Remove Layer", parent.OnRemoveLayer)
        self.AddMenuItem(menu, "&Merge Down\tCtrl+E", parent.OnMergeDown)
        menu.AppendSeparator()
        self.AddMenuItem(menu, "&Clear\tDelete", parent.OnClear)

        maimenu = wx.Menu()
        self.Append(maimenu, "&AI")
        self.AddMenuItem(maimenu, "Image from Prompt...", parent.OnGenerateImage)
        item = self.AddMenuItem(maimenu, "Layer from Prompt...", parent.OnGenerateLayer)
        item.Enable(False)

        menu = wx.Menu()
        self.Append(menu, "&Help")
        #self.AddMenuItem(menu, "&Manual", parent.OnManual)
        self.AddMenuItem(menu, "&About", parent.OnAbout)

    def AddMenuItem(self, menu, name, func):
        item = menu.Append(self.menuid, name)
        menu.Bind(wx.EVT_MENU, func, id=self.menuid)
        self.menuid += 1
        return item
