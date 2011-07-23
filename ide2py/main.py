#!/usr/bin/env python
# coding:utf-8

"Pythonic Integrated Development Environment for Rapid Application Development"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2011 Mariano Reingart"
__license__ = "GPL 3.0"
__version__ = "0.03"

# The original AUI skeleton is based on wx examples (demo)
# Also inspired by activegrid wx sample (pyide), wxpydev, pyragua, picalo, SPE,
#      pythonwin, drpython, idle

import os
import sys
import traceback

import wx
import wx.grid
import wx.html
import wx.aui

import images

from browser import SimpleBrowserPanel
from editor import EditorCtrl
from shell import Shell
from debugger import Debugger, EVT_DEBUG_ID
from console import ConsoleCtrl
from psp import PSPMixin
from repo import RepoMixin, RepoEvent, EVT_REPO_ID

TITLE = "ide2py w/PSP - v%s (rad2py)" % __version__

CONFIG_FILE = "ide2py.ini"

class PyAUIFrame(wx.aui.AuiMDIParentFrame, PSPMixin, RepoMixin):
    def __init__(self, parent):
        wx.aui.AuiMDIParentFrame.__init__(self, parent, -1, title=TITLE,
            size=(800,600), style=wx.DEFAULT_FRAME_STYLE)

        #sys.excepthook  = self.ExceptHook
        
        self._perspectives = []
        
        self.children = {}
        self.active_child = None
        
        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager(self)
        self.Show()
        ##self._mgr.SetManagedWindow(self)
        
        #self.SetIcon(images.GetMondrianIcon())

        # create menu
        self.menubar = wx.MenuBar()
        self.menu = {}

        file_menu = self.menu['file'] = wx.Menu()
        file_menu.Append(wx.ID_NEW, "New")
        file_menu.Append(wx.ID_OPEN, "Open")
        file_menu.Append(wx.ID_SAVE, "Save")
        file_menu.Append(wx.ID_SAVEAS, "Save As")        
        file_menu.AppendSeparator()        
        file_menu.Append(wx.ID_EXIT, "Exit")

        edit_menu = self.menu['edit'] = wx.Menu()
        edit_menu.Append(wx.ID_UNDO, "Undo")
        edit_menu.Append(wx.ID_REDO, "Redo")
        edit_menu.AppendSeparator()
        edit_menu.Append(wx.ID_CUT, "Cut")
        edit_menu.Append(wx.ID_COPY, "Copy")
        edit_menu.Append(wx.ID_PASTE, "Paste")
        edit_menu.AppendSeparator()        
        edit_menu.Append(wx.ID_FIND, "Find")
        edit_menu.Append(wx.ID_REPLACE, "Replace")
          
        help_menu = self.menu['help'] = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "About...")
        
        self.menubar.Append(file_menu, "File")
        self.menubar.Append(edit_menu, "Edit")
        #mb.Append(self._perspectives_menu, "Perspectives")
        self.menubar.Append(help_menu, "Help")
        
        self.SetMenuBar(self.menubar)

        self.statusbar = self.CreateStatusBar(2, wx.ST_SIZEGRIP)
        self.statusbar.SetStatusWidths([-2, -3])
        self.statusbar.SetStatusText("Ready", 0)
        self.statusbar.SetStatusText("Welcome To wxPython!", 1)

        # min size for the frame itself isn't completely done.
        # see the end up FrameManager::Update() for the test
        # code. For now, just hard code a frame minimum size
        self.SetMinSize(wx.Size(400, 300))

        # create some toolbars

        self.toolbar = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                         wx.TB_FLAT | wx.TB_NODIVIDER)
        tsize = (16, 16)
        self.toolbar.SetToolBitmapSize(wx.Size(*tsize))

        GetBmp = wx.ArtProvider.GetBitmap
        self.toolbar.AddSimpleTool(
            wx.ID_NEW, GetBmp(wx.ART_NEW, wx.ART_TOOLBAR, tsize), "New")
        self.toolbar.AddSimpleTool(
            wx.ID_OPEN, GetBmp(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, tsize), "Open")
        self.toolbar.AddSimpleTool(
            wx.ID_SAVE, GetBmp(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, tsize), "Save")
        self.toolbar.AddSimpleTool(
            wx.ID_SAVEAS, GetBmp(wx.ART_FILE_SAVE_AS, wx.ART_TOOLBAR, tsize),
            "Save As...")
        self.toolbar.AddSimpleTool(
            wx.ID_PRINT, GetBmp(wx.ART_PRINT, wx.ART_TOOLBAR, tsize), "Print")
        #-------
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_UNDO, GetBmp(wx.ART_UNDO, wx.ART_TOOLBAR, tsize), "Undo")
        self.toolbar.AddSimpleTool(
            wx.ID_REDO, GetBmp(wx.ART_REDO, wx.ART_TOOLBAR, tsize), "Redo")
        self.toolbar.AddSeparator()
        #-------
        self.toolbar.AddSimpleTool(
            wx.ID_CUT, GetBmp(wx.ART_CUT, wx.ART_TOOLBAR, tsize), "Cut")
        self.toolbar.AddSimpleTool(
            wx.ID_COPY, GetBmp(wx.ART_COPY, wx.ART_TOOLBAR, tsize), "Copy")
        self.toolbar.AddSimpleTool(
            wx.ID_PASTE, GetBmp(wx.ART_PASTE, wx.ART_TOOLBAR, tsize), "Paste")
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_FIND, GetBmp(wx.ART_FIND, wx.ART_TOOLBAR, tsize), "Find")
        self.toolbar.AddSimpleTool(
            wx.ID_REPLACE, GetBmp(wx.ART_FIND_AND_REPLACE, wx.ART_TOOLBAR, tsize), "Replace")
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(
            wx.ID_ABOUT, GetBmp(wx.ART_HELP, wx.ART_TOOLBAR, tsize), "About")

        self.toolbar.AddSeparator()
        
        self.ID_RUN = wx.NewId()
        self.ID_DEBUG = wx.NewId()
        self.ID_CHECK = wx.NewId()

        self.ID_STEPIN = wx.NewId()
        self.ID_STEPRETURN = wx.NewId()
        self.ID_STEPNEXT = wx.NewId()
        self.ID_CONTINUE = wx.NewId()
        self.ID_STOP = wx.NewId()
        
        self.toolbar.AddSimpleTool(
            self.ID_RUN, images.GetRunningManBitmap(), "Run")
        self.toolbar.AddSimpleTool(
            self.ID_DEBUG, images.GetDebuggingBitmap(), "Debug")
        self.toolbar.AddSimpleTool(
            self.ID_CHECK, images.ok_16.GetBitmap(), "Check")

        self.toolbar.Realize()

        menu_handlers = [
            (wx.ID_NEW, self.OnNew),
            (wx.ID_OPEN, self.OnOpen),
            (wx.ID_SAVE, self.OnSave),
            (wx.ID_SAVEAS, self.OnSaveAs),
            (self.ID_CHECK, self.OnCheck),
            (self.ID_RUN, self.OnRun),
            (self.ID_DEBUG, self.OnDebug),
            #(wx.ID_PRINT, self.OnPrint),
            #(wx.ID_FIND, self.OnFind),
            #(wx.ID_REPLACE, self.OnModify),
            #(wx.ID_CUT, self.OnCut),
            #(wx.ID_COPY, self.OnCopy),
            #(wx.ID_PASTE, self.OnPaste),
            #(wx.ID_ABOUT, self.OnAbout),
        ]
        for menu_id, handler in menu_handlers:
            self.Bind(wx.EVT_MENU, handler, id=menu_id)
    
        # debugging facilities:

        self.toolbardbg = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                         wx.TB_FLAT | wx.TB_NODIVIDER)
        tsize = (16, 16)
        self.toolbardbg.SetToolBitmapSize(wx.Size(*tsize))

        self.toolbardbg.AddSimpleTool(
            self.ID_DEBUG, images.GetBreakBitmap(), "Break")
        self.toolbardbg.AddSimpleTool(
            self.ID_STEPIN, images.GetStepInBitmap(), "Step")
        self.toolbardbg.AddSimpleTool(
            self.ID_STEPNEXT, images.GetStepReturnBitmap(), "Next")
        self.toolbardbg.AddSimpleTool(
            self.ID_CONTINUE, images.GetContinueBitmap(), "Continue")
        self.toolbardbg.AddSimpleTool(
            self.ID_STOP, images.GetStopBitmap(), "Quit")
        self.toolbardbg.AddSimpleTool(
            self.ID_DEBUG, images.GetAddWatchBitmap(), "AddWatch")            
        self.toolbardbg.AddSimpleTool(
            self.ID_DEBUG, images.GetCloseBitmap(), "Close")
        self.toolbardbg.Realize()

        for menu_id in [self.ID_STEPIN, self.ID_STEPRETURN, self.ID_STEPNEXT,
                        self.ID_CONTINUE, self.ID_STOP]:
            self.Bind(wx.EVT_MENU, self.OnDebugCommand, id=menu_id)

        self.debugger = Debugger(self)

        # add a bunch of panes                      
        self._mgr.AddPane(self.toolbar, wx.aui.AuiPaneInfo().
                          Name("General Toolbar").
                          ToolbarPane().Top().Row(1).Position(1).
                          LeftDockable(False).RightDockable(False).CloseButton(True))

        self._mgr.AddPane(self.toolbardbg, wx.aui.AuiPaneInfo().
                          Name("Debug Toolbar").
                          ToolbarPane().Top().Row(1).Position(2).
                          LeftDockable(False).RightDockable(False).CloseButton(True))
                      
        #self._mgr.AddPane(tb3, wx.aui.AuiPaneInfo().
        #                  Name("tb3").Caption("Toolbar 3").
        #                  ToolbarPane().Top().Row(1).Position(1).
        #                  LeftDockable(False).RightDockable(False))
                      
        #self._mgr.AddPane(tb5, wx.aui.AuiPaneInfo().
        #                  Name("tbvert").Caption("Sample Vertical Toolbar").
        #                  ToolbarPane().Left().GripperTop().
        #                  TopDockable(False).BottomDockable(False))
                      
        #self._mgr.AddPane(wx.Button(self, -1, "Test Button"),
        #                  wx.aui.AuiPaneInfo().Name("tb5").
        #                  ToolbarPane().Top().Row(2).Position(1).
        #                  LeftDockable(False).RightDockable(False))

        self.browser = self.CreateBrowserCtrl()
        self._mgr.AddPane(self.browser, wx.aui.AuiPaneInfo().
                          Caption("Simple Browser").
                          Right().CloseButton(True))

        self.shell = Shell(self)
        self._mgr.AddPane(self.shell, wx.aui.AuiPaneInfo().
                          Caption("PyCrust Shell").
                          Bottom().Layer(1).Position(1).CloseButton(True))

        self.console = ConsoleCtrl(self)
        self._mgr.AddPane(self.console, wx.aui.AuiPaneInfo().
                          Name("stdio").Caption("Console (stdio)").
                          Bottom().Layer(1).Position(2).CloseButton(True).MaximizeButton(True))

        # "commit" all changes made to FrameManager   
        self._mgr.Update()

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Show How To Use The Closing Panes Event
        self.Bind(wx.aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)
        
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)

        self.Connect(-1, -1, EVT_DEBUG_ID, self.GotoFileLine)
        
        PSPMixin.__init__(self)
        RepoMixin.__init__(self)


    def OnPaneClose(self, event):

        caption = event.GetPane().caption

        if caption in ["Tree Pane", "Dock Manager Settings", "Fixed Pane"]:
            msg = "Are You Sure You Want To Close This Pane?"
            dlg = wx.MessageDialog(self, msg, "AUI Question",
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)

            if dlg.ShowModal() in [wx.ID_NO, wx.ID_CANCEL]:
                event.Veto()
            dlg.Destroy()


    def OnClose(self, event):
        self._mgr.UnInit()
        del self._mgr
        self.Destroy()


    def OnExit(self, event):
        self.Close()

    def OnAbout(self, event):
        msg = "%s - Licenced under the GPLv3\n"  % TITLE + \
              "A modern, minimalist, cross-platform, complete and \n" + \
              "totally Integrated Development Environment\n" + \
              "for Rapid Application Development in Python \n" + \
              "guided by the Personal Software Process (TM).\n" + \
              "(c) Copyright 2011, Mariano Reingart\n" + \
              "Inspired by PSP Process Dashboard and several Python IDEs. \n" + \
              "Some code was based on wxPython demos and other projects\n" + \
              "(see sources or http://code.google.com/p/rad2py/)"
        dlg = wx.MessageDialog(self, msg, TITLE,
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()        

    def GetDockArt(self):
        return self._mgr.GetArtProvider()

    def DoUpdate(self):
        self._mgr.Update()

    def OnEraseBackground(self, event):
        event.Skip()

    def OnSize(self, event):
        event.Skip()

    def OnCreatePerspective(self, event):
        dlg = wx.TextEntryDialog(self, "Enter a name for the new perspective:", "AUI Test")
        dlg.SetValue(("Perspective %d")%(len(self._perspectives)+1))
        if dlg.ShowModal() != wx.ID_OK:
            return
        if len(self._perspectives) == 0:
            self._perspectives_menu.AppendSeparator()
        self._perspectives_menu.Append(ID_FirstPerspective + len(self._perspectives), dlg.GetValue())
        self._perspectives.append(self._mgr.SavePerspective())

    def OnCopyPerspective(self, event):
        s = self._mgr.SavePerspective()
        if wx.TheClipboard.Open():
        
            wx.TheClipboard.SetData(wx.TextDataObject(s))
            wx.TheClipboard.Close()
        
    def OnRestorePerspective(self, event):
        self._mgr.LoadPerspective(self._perspectives[event.GetId() - ID_FirstPerspective])

    def GetStartPosition(self):
        self.x = self.x + 20
        x = self.x
        pt = self.ClientToScreen(wx.Point(0, 0))
        return wx.Point(pt.x + x, pt.y + x)

    def OnCreateTree(self, event):
        self._mgr.AddPane(self.CreateTreeCtrl(), wx.aui.AuiPaneInfo().
                          Caption("Tree Control").
                          Float().FloatingPosition(self.GetStartPosition()).
                          FloatingSize(wx.Size(150, 300)).CloseButton(True).MaximizeButton(True))
        self._mgr.Update()


    def OnCreateGrid(self, event):
        self._mgr.AddPane(self.CreateGrid(), wx.aui.AuiPaneInfo().
                          Caption("Grid").
                          Float().FloatingPosition(self.GetStartPosition()).
                          FloatingSize(wx.Size(300, 200)).CloseButton(True).MaximizeButton(True))
        self._mgr.Update()


    def OnCreateHTML(self, event):
        self._mgr.AddPane(self.CreateHTMLCtrl(), wx.aui.AuiPaneInfo().
                          Caption("HTML Content").
                          Float().FloatingPosition(self.GetStartPosition()).
                          FloatingSize(wx.Size(300, 200)).CloseButton(True).MaximizeButton(True))
        self._mgr.Update()

    def OnCreateText(self, event):
        self._mgr.AddPane(self.CreateTextCtrl(), wx.aui.AuiPaneInfo().
                          Caption("Text Control").
                          Float().FloatingPosition(self.GetStartPosition()).
                          CloseButton(True).MaximizeButton(True))
        self._mgr.Update()

    def OnCreateBrowser(self, event):       
        self._mgr.AddPane(self.CreateBrowserCtrl(), wx.aui.AuiPaneInfo().
                          Caption("Simple Browser").
                          Float().CloseButton(True))
        self._mgr.Update()

    def OnNew(self, event):
        child = AUIChildFrame(self, "")
        child.Show()
        return child

    def OnOpen(self, event):
        dlg = wx.FileDialog(
            self, message="Choose a file",
            defaultDir=os.getcwd(), 
            defaultFile="hola.py",
            wildcard="Python Files (*.py)|*.py",
            style=wx.OPEN 
            )
        
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            filename = dlg.GetPaths()[0]        
            self.DoOpen(filename)
            
        dlg.Destroy()
   
    def DoOpen(self, filename):
        if filename not in self.children:
            child = AUIChildFrame(self, filename)
            child.Show()
            self.children[filename] = child
        else:
            child = self.children[filename]
        return child

    def OnSave(self, event):
        if self.active_child:
            self.active_child.OnSave(event)

    def OnSaveAs(self, event):
        if self.active_child:
            self.active_child.OnSaveAs(event)

    def OnRun(self, event, debug=False):
        if self.active_child:
            # add the path of this script so we can import things
            syspath = [ os.path.split(self.active_child.filename)[0] ]  
     
            # create a code object and run it in the main thread
            code = self.active_child.GetCodeObject()
            if code:         
                self.shell.RunScript(code, syspath, debug and self.debugger, self.console)

    def OnDebug(self, event):
        self.OnRun(event, debug=True)
        self.GotoFileLine()
            
    def GotoFileLine(self, event=None, running=True):
        if event and running:
            filename, lineno = event.data
        elif not running:
            filename, lineno, offset = event
        # first, clean all current debugging markers
        for child in self.children.values():
            if running:
                child.SynchCurrentLine(None)
        # then look for the file being debugged
        if event:
            child = self.DoOpen(filename)
            if child:
                if running:
                    child.SynchCurrentLine(lineno)
                else:
                    child.GotoLineOffset(lineno, offset)
                    
    def OnDebugCommand(self, event):
        event_id = event.GetId()
        if event_id == self.ID_STEPIN:
            self.debugger.Step()
        elif event_id == self.ID_STEPNEXT:
            self.debugger.Next()
        elif event_id == self.ID_STEPRETURN:
            self.debugger.StepReturn()
        elif event_id == self.ID_CONTINUE:
            self.debugger.Continue()
        elif event_id == self.ID_STOP:
            self.debugger.Quit()
            self.GotoFileLine()

    def OnCheck(self, event):
        # TODO: separate checks and tests, add reviews and diffs...
        if self.active_child:
            import checker
            for error in checker.check(self.active_child.filename):
                self.NotifyDefect(**error)
            import tester
            for error in tester.test(self.active_child.filename):
                self.NotifyDefect(**error)

    def CreateTextCtrl(self):
        text = ("This is text box")
        return wx.TextCtrl(self,-1, text, wx.Point(0, 0), wx.Size(150, 90),
                           wx.NO_BORDER | wx.TE_MULTILINE)

    def CreateBrowserCtrl(self):
        return SimpleBrowserPanel(self)

    def CreateGrid(self):
        grid = wx.grid.Grid(self, -1, wx.Point(0, 0), wx.Size(150, 250),
                            wx.NO_BORDER | wx.WANTS_CHARS)
        grid.CreateGrid(50, 20)
        return grid


    def CreateHTMLCtrl(self):
        ctrl = wx.html.HtmlWindow(self, -1, wx.DefaultPosition, wx.Size(400, 300))
        if "gtk2" in wx.PlatformInfo:
            ctrl.SetStandardFonts()
        ctrl.SetPage("hola!")
        return ctrl    

    def ExceptHook(self, type, value, trace): 
        exc = traceback.format_exception(type, value, trace) 
        for e in exc: wx.LogError(e) 
        wx.LogError(u'Unhandled Error: %s: %s'%(str(type), unicode(value)))
        # TODO: automatic defect classification
        tb = traceback.extract_tb(trace)
        if tb:
            filename, lineno, function_name, text = tb[-1]
            self.NotifyDefect(description=str(e), type="60", filename=filename, lineno=lineno, offset=1)
        # enter post-mortem debugger
        self.debugger.pm()

    def NotifyRepo(self, filename, action="", status=""):
        wx.PostEvent(self, RepoEvent(filename, action, status))


class AUIChildFrame(wx.aui.AuiMDIChildFrame):

    def __init__(self, parent, filename):
        wx.aui.AuiMDIChildFrame.__init__(self, parent, -1,
                                         title="")  
        self.filename = filename     
        self.editor = EditorCtrl(self,-1, filename=filename,    
                                 debugger=parent.debugger)
        sizer = wx.BoxSizer()
        sizer.Add(self.editor, 1, wx.EXPAND)
        self.SetSizer(sizer)        
        wx.CallAfter(self.Layout)

        self.parent = parent
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)   # window focused
        self.Bind(wx.EVT_ACTIVATE, self.OnFocus)   # window focused
        self.OnFocus(None) # emulate initial focus
 
    def OnFocus(self, event):
        self.parent.active_child = self

    def OnSave(self, event):
        self.editor.OnSave(event)

    def OnSaveAs(self, event):
        self.editor.OnSaveAs(event)

    def GetCodeObject(self,):
        return self.editor.GetCodeObject()

    def SynchCurrentLine(self, lineno):
        if lineno:
            self.SetFocus()
        self.editor.SynchCurrentLine(lineno)

    def GotoLineOffset(self, lineno, offset):
        if lineno:
            self.SetFocus()
            self.editor.GotoLineOffset(lineno, offset)

    def NotifyDefect(self, *args, **kwargs):
        self.parent.NotifyDefect(*args, **kwargs)
    
    def NotifyRepo(self, *args, **kwargs):
        self.parent.NotifyRepo(*args, **kwargs)


    
if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = PyAUIFrame(None)
    frame.Show()
    app.MainLoop()

