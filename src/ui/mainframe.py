"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

from src.constants import *

import wx.html
import wx
import wx.lib.agw.genericmessagedialog as GMD
from wx.adv import BitmapComboBox
from wx.lib.agw.cubecolourdialog import CubeColourDialog

from PIL import Image
import numpy as np

from array import array

from src.layermanager import *
from src.ui.canvas import Canvas, TOOLS
from src.ui.toolbar import Toolbar
from src.ui.menubar import MenuBar
from src.ui.gradienteditor import *
from src.ui.layercontrol import *
from src.ui.animationcontrol import *
from src.settings import *
from src.ui.dialogs.dictionarydialog import *
from src.ui.dialogs.aidialogs import *
from src import ai

PROGRAM_NAME = "Pixel Portal"

def nvl(v, nv):
    return v if v else nv


class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None)

        self.settings = Settings(self)

        self.SetIcon(wx.Icon('icons/application.png'))
        self.FirstTimeResize = True
        self.saveFile = None

        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        self.canvas = Canvas(self)
        self.canvas.listeners.append(self)

        self.SetMenuBar(MenuBar(self))

        self.toolbar = self.CreateToolBar()
        self.toolbar = Toolbar(self)
        self.SetToolBar(self.toolbar)

        bstop = wx.BoxSizer(wx.VERTICAL)
        # add CANVAS
        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.canvas, 2, wx.EXPAND | wx.ALL, 2)

        # RIGHT PANEL
        layerPanel = wx.Panel(self, size=(200, -1))
        bs.Add(layerPanel, 0, wx.EXPAND | wx.ALL, 2)
        bstop.Add(bs, 1, wx.EXPAND | wx.ALL, 2)

        # ANIMATION CONTROL
        self.animControl = AnimationControl(self, self.canvas.document)
        self.animControl.Bind(EVT_KEY_SET_EVENT, self.OnAnimationKeySet)
        self.animControl.Bind(EVT_VISIBILITY_CHANGED_EVENT,
                              self.OnLayerVisibilityFromKey)
        self.animControl.Bind(EVT_KEY_INSERT_EVENT, self.OnAnimationKeyInsert)
        self.animControl.Bind(EVT_KEY_DELETE_EVENT, self.OnAnimationKeyDelete)
        bstop.Add(self.animControl, 0, wx.EXPAND | wx.ALL, 2)

        # LAYERS PANEL
        bsp = wx.BoxSizer(wx.VERTICAL)
        self.lyrctrl = LayerControl(layerPanel)
        self.lyrctrl.UpdateLayers(self.canvas.document)
        self.lyrctrl.Bind(EVT_LAYER_CLICKED_EVENT, self.OnLayerClicked)
        self.lyrctrl.Bind(EVT_LAYER_VISIBILITY_EVENT, self.OnLayerVisibility)
        self.lyrctrl.Bind(EVT_LAYER_ALPHA_EVENT, self.OnLayerAlphaChange)
        self.lyrctrl.Bind(EVT_LAYER_DROP_EVENT, self.OnLayerDrop)
        self.lyrctrl.Bind(EVT_LAYER_RENAME_EVENT, self.OnLayerRename)
        bsp.Add(self.lyrctrl, 1, wx.EXPAND | wx.ALL, 3)

        # LAYER CONTROLS
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        conpanel = wx.Panel(layerPanel)
        but = wx.BitmapButton(conpanel, bitmap=wx.Bitmap('icons/layernew.png'))
        but.SetToolTip('Add new layer')
        self.Bind(wx.EVT_BUTTON, self.OnAddLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)

        sizer.AddSpacer(10)
        but = wx.BitmapButton(
            conpanel, bitmap=wx.Bitmap('icons/layerdelete.png'))
        but.SetToolTip('Delete layer')
        self.Bind(wx.EVT_BUTTON, self.OnRemoveLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)

        sizer.AddSpacer(10)
        but = wx.BitmapButton(
            conpanel, bitmap=wx.Bitmap('icons/layerduplicate.png'))
        but.SetToolTip('Duplicate layer')
        self.Bind(wx.EVT_BUTTON, self.OnDuplicateLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)

        sizer.AddSpacer(10)
        but = wx.BitmapButton(
            conpanel, bitmap=wx.Bitmap('icons/layermerge.png'))
        but.SetToolTip('Merge down')
        self.Bind(wx.EVT_BUTTON, self.OnMergeDown, id=but.GetId())
        sizer.Add(but, 0, 0, 1)
        sizer.AddSpacer(10)
        conpanel.SetSizer(sizer)
        bsp.Add(conpanel, 0, wx.EXPAND | wx.ALL, 2)

        # HELP
        # only if needed
        self.help = None

        docw = GetSetting('New Document', 'Document Width')
        doch = GetSetting('New Document', 'Document Height')
        self.OnNew(None, docw, doch, False)

        self.LoadConfiguration()

        layerPanel.SetSizer(bsp)
        layerPanel.FitInside()
        self.SetSizer(bstop)
        self.UpdateTitle()

        # paint pen color button
        self.SetColor(self.canvas.GetPenColor())

    def CheckDirty(self):
        if self.canvas.IsDirty():
            diag = wx.GenericMessageDialog(
                self, 'Save Changes?', style=wx.YES_NO | wx.CANCEL)
            ret = diag.ShowModal()
            if ret == wx.ID_YES:
                self.OnSave(None)
                return True
            elif ret == wx.ID_CANCEL:
                return False

        return True

    def LoadConfiguration(self):
        config = wx.Config("Pixel-Portal")

        fw = config.ReadInt("Frame/Width", 800)
        fh = config.ReadInt("Frame/Height", 700)
        self.SetSize(fw, fh)

        px = config.ReadInt("Frame/PosX", 0)
        py = config.ReadInt("Frame/PosY", 0)
        self.SetPosition(wx.Point(px, py))

        pc = config.ReadInt("General/PenColor", wx.BLACK.GetRGBA())
        c = wx.Colour()
        c.SetRGBA(pc)
        self.canvas.SetPenColor(c)
        self.PenColorChanged(c)

        ps = config.ReadInt("General/PenSize", 1)
        self.canvas.SetPenSize(ps)

    def OnAbout(self, e):
        msg = 'Pixel Portal\n' \
              'Version 1.0\n' \
              'Bhupendra Aole\n' \
              'https://github.com/aole/Pixel-Portal'
        dlg = GMD.GenericMessageDialog(self, msg, "About Pixel Portal",
                                       agwStyle=wx.ICON_INFORMATION | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnAddLayer(self, e):
        self.canvas.AddLayer()
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnAnimationKeyDelete(self, e):
        self.canvas.AddUndo(KeyDeleteCommand(
            self.animControl, e.frame, e.key.copy()))

    def OnAnimationKeyInsert(self, e):
        if GetSetting('Animation', 'Hide Current Layer'):
            self.canvas.document.SetVisible(False)
        if GetSetting('Animation', 'Duplicate Layer'):
            self.canvas.DuplicateLayer()
        if GetSetting('Animation', 'Insert Layer'):
            self.canvas.AddLayer()

        self.canvas.Refresh()
        self.RefreshLayers()
        self.canvas.AddUndo(KeyInsertCommand(
            self.animControl, e.frame, e.key.copy()))

    def OnAnimationKeySet(self, e):
        self.canvas.AddUndo(KeyMoveCommand(
            self.animControl, e.frame, e.fromFrame))

    def OnCenter(self, e):
        self.canvas.CenterCanvasInPanel(self.canvas.Size)
        self.canvas.Refresh()

    def OnClear(self, e):
        self.canvas.ClearCurrentLayer()
        self.RefreshLayers()

    def OnClose(self, e):
        if not self.CheckDirty():
            return

        self.SaveConfiguration()
        self.settings.Destroy()

        self.Destroy()

    def SetColor(self, color):
        self.canvas.SetPenColor(color)
        self.toolbar.SetColor(color)

    def OnColorBtn(self, e):
        data = wx.ColourData()
        data.SetColour(self.canvas.GetPenColor())
        dlg = CubeColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            self.SetColor(color)

    def OnGradientBtn(self, e):
        dlg = GradientEditor(self, self.canvas.GetGradientStops())
        if dlg.ShowModal() == wx.ID_OK:
            stops = dlg.GetStops()
            self.canvas.SetGradientStops(stops)

            bitmap = e.GetEventObject().GetBitmap()
            mdc = wx.MemoryDC(bitmap)
            gc = wx.GraphicsContext.Create(mdc)

            clip = wx.Region(2, 2, 60, 28)
            gc.Clip(clip)

            brush = gc.CreateLinearGradientBrush(0, 0, 64, 0, stops)
            gc.SetBrush(brush)
            gc.SetPen(wx.NullPen)
            gc.DrawRectangle(0, 0, 64, 32)

            mdc.SelectObject(wx.NullBitmap)
            del mdc

            e.GetEventObject().SetBitmap(bitmap)
        dlg.Destroy()

    def OnDeselect(self, e):
        self.canvas.Select(wx.Region())
        self.Refresh()

    def OnDocResize(self, e):
        dlg = ResizeDialog(
            self, self.canvas.document.Composite(), self.canvas.pixelSize)
        if dlg.ShowModal() == wx.ID_OK:
            width = dlg.GetWidth()
            height = dlg.GetHeight()
            self.canvas.Resize(width, height)

    def OnDuplicateLayer(self, e):
        self.canvas.DuplicateLayer()
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnExportAnimation(self, e):
        filename = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if filename:
            frames = self.animControl.GetAnimationFrames()
            pxlsz = self.canvas.GetPixelSize()
            if frames:
                fps = self.animControl.GetFPS()
                images = []
                for frame in frames:
                    wxImage = frame.Scaled(pxlsz).ConvertToImage()
                    pilImage = Image.new(
                        'RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
                    pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
                    images.append(pilImage)

                print('Saving to', filename)
                images[0].save(filename, save_all=True, append_images=images[1:],
                               optimize=False, duration=1000/fps, loop=0)
            else:
                print('No frames available! [Frame.OnExportAninmation]')

    def OnExportHistory(self, e):
        filename = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if filename:
            images = []
            pxlsz = self.canvas.GetPixelSize()
            for command in self.canvas.history.GetCommands():
                wxImage = command.composite.Scaled(pxlsz).ConvertToImage()
                pilImage = Image.new(
                    'RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
                pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
                images.append(pilImage)

            if images:
                print('Saving to', filename)
                fps = self.animControl.GetFPS()
                # render original image first
                wxImage = self.canvas.history.composite.Scaled(
                    pxlsz).ConvertToImage()
                pilImage = Image.new(
                    'RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
                pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
                # save to gif
                pilImage.save(filename, save_all=True, append_images=images,
                              optimize=False, duration=1000/fps, loop=0)

    def OnKeyDown(self, e):
        keycode = e.GetUnicodeKey()

        if keycode == ord('Z'):
            if e.ControlDown():
                if e.ShiftDown():
                    self.canvas.Redo()
                else:
                    self.canvas.Undo()
            else:
                # skip for other controls (eg renaming layer)
                e.Skip()
        elif keycode == ord('['):
            self.canvas.AdjustBrushSize(-1)
        elif keycode == ord(']'):
            self.canvas.AdjustBrushSize(1)
        elif keycode == ord('F'):
            if not self.canvas.OnFloodFill(e):
                e.Skip()
        else:
            e.Skip()

    def OnLayerAlphaChange(self, e):
        self.canvas.document.SetAlpha(e.alpha)
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnLayerClicked(self, e):
        self.canvas.document.SelectIndex(e.index)
        self.RefreshLayers()

    def OnLayerDrop(self, e):
        self.canvas.RearrangeLayer(e.layer, e.position)
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnLayerRename(self, e):
        self.canvas.RenameLayer(e.layer, e.oldName, e.newName)
        self.RefreshLayers()

    def OnLayerVisibility(self, e):
        self.canvas.document.ToggleVisible(e.index)
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnLayerVisibilityFromKey(self, e):
        self.canvas.document.SetVisibleExclusive(e.key)
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnManual(self, e):
        if not self.help:
            self.help = wx.html.HtmlHelpController(self)
            self.help.AddBook('help/Manual.hhp')
        self.help.DisplayContents()

    def OnMergeDown(self, e):
        self.canvas.MergeDown()
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnMirrorX(self, e):
        self.canvas.mirrorx = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorY(self, e):
        self.canvas.mirrory = e.IsChecked()
        self.canvas.Refresh()

    def OnNew(self, e, width=None, height=None, showDialog=True):
        if not self.CheckDirty():
            return

        self.saveFile = None
        if showDialog:
            dlg = DictionaryDialog(self, {'Width': nvl(width, GetSetting(
                'New Document', 'Document Width')), 'Height': nvl(height, GetSetting('New Document', 'Document Height'))})
            if dlg.ShowModal() == wx.ID_OK:
                width = dlg.Get('Width')
                height = dlg.Get('Height')
            else:
                return

        if width and height:
            self.canvas.New(width, height)
            self.animControl.SetDocument(self.canvas.document)
            self.canvas.Refresh()
            self.RefreshLayers()

    def OnGenerateImage(self, e):
        if not ai.CheckAIModels(self):
            return

        props = {'Width': 64,
                 'Height': 64,
                 'Prompt': ''}
        dlg = GenerateImageDialog(self, props)
        if dlg.ShowModal() == wx.ID_OK:
            width = dlg.Get('Width')
            height = dlg.Get('Height')
            prompt = dlg.Get('Prompt')

            progress = wx.ProgressDialog("Generating Image", "Please wait...", parent=self, style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)
            progress.Pulse()

            filename = ai.GenerateImage(prompt, width, height)

            progress.Destroy()

            if filename:
                self.canvas.Load(1, filename)
                self.canvas.Refresh()
                self.RefreshLayers()

    def OnGenerateLayer(self, e):
        if not ai.CheckAIModels(self):
            return

        props = {'Width': self.canvas.document.width,
                 'Height': self.canvas.document.height,
                 'Prompt': ''}
        dlg = GenerateLayerDialog(self, props)
        if dlg.ShowModal() == wx.ID_OK:
            # No functionality needed for OK yet
            pass


    def OnOpen(self, e):
        if not self.CheckDirty():
            return

        with wx.FileDialog(self, "Open Image file",
                           wildcard=FILE_DIALOG_FILTERS,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return

            self.saveFile = fd.GetPath()
            ps = 1
            # not native format as we already know the pixel size
            if self.saveFile[-5:] != '.aole':
                cpd = ChangePixelDialog(self, wx.Bitmap(self.saveFile))
                cpd.ShowModal()
                ps = cpd.GetPixelSize()

            self.canvas.Load(ps, self.saveFile)
            self.canvas.Refresh()
            self.animControl.SetDocument(self.canvas.document)
            self.RefreshLayers()

    def OnRefImage(self, e):
        with wx.FileDialog(self, "Open Reference Image file",
                           wildcard=REF_FILE_DIALOG_FILTERS,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return

            self.canvas.LoadRefImage(fd.GetPath())
            self.canvas.Refresh()

    def OnRemoveLayer(self, e):
        self.canvas.RemoveLayer()
        self.canvas.Refresh()
        self.RefreshLayers()

    def OnReselect(self, e):
        self.canvas.Reselect()
        self.Refresh()

    def OnResize(self, e):
        if self.FirstTimeResize:
            self.OnCenter(e)
            self.FirstTimeResize = False
        self.canvas.Refresh()
        e.Skip()

    def OnSave(self, e):
        if not self.saveFile:
            with wx.FileDialog(self, "Save Image file", wildcard=FILE_DIALOG_FILTERS,
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
                if fd.ShowModal() == wx.ID_CANCEL:
                    return

                self.saveFile = fd.GetPath()

        self.canvas.Save(self.saveFile)
        self.UpdateTitle()

    def OnSaveAs(self, e):
        with wx.FileDialog(self, "Save Image file", wildcard=FILE_DIALOG_FILTERS,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return

            self.saveFile = fd.GetPath()

            self.canvas.Save(self.saveFile)
            self.UpdateTitle()

    def OnSaveGif(self, e):
        ret = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if ret:
            self.canvas.SaveGif(ret)

    def OnSelectAll(self, e):
        self.canvas.Select()
        self.Refresh()

    def OnSelectInvert(self, e):
        self.canvas.SelectInvert()
        self.Refresh()

    def OnSettings(self, e):
        if self.settings.ShowModal():
            self.canvas.SettingsUpdated()

    def OnSmoothLine(self, e):
        self.canvas.smoothLine = e.IsChecked()
        self.canvas.Refresh()

    def OnToggleGrid(self, e):
        self.canvas.gridVisible = e.IsChecked()
        self.canvas.Refresh()

    def OnTool(self, e):
        self.canvas.SetTool(e.GetString())

    def PenColorChanged(self, color):
        self.toolbar.SetColor(color)

    def Redid(self):
        self.Undid()

    def RefreshLayers(self):
        self.lyrctrl.UpdateLayers(self.canvas.document)
        self.lyrctrl.FitInside()
        self.UpdateTitle()

    def SaveConfiguration(self):
        config = wx.Config("Pixel-Portal")

        sw, sh = self.GetSize()
        config.WriteInt("Frame/Width", sw)
        config.WriteInt("Frame/Height", sh)

        px, py = self.GetPosition()
        config.WriteInt("Frame/PosX", px)
        config.WriteInt("Frame/PosY", py)

        config.WriteInt("General/PenColor",
                        self.canvas.GetPenColor().GetRGBA())
        config.WriteInt("General/PenSize", self.canvas.GetPenSize())

    def Undid(self):
        self.RefreshLayers()
        self.animControl.Refresh()

    def UpdateTitle(self):
        if not self.saveFile:
            title = PROGRAM_NAME + ' - [Unsaved]'
        else:
            title = PROGRAM_NAME + ' - ' + self.saveFile
            if self.canvas.IsDirty():
                title += ' *'

        self.SetTitle(title)
