import os
import sys
import wx
import wx.lib.newevent

# Main window title
TITLE = 'Lambda Lifter'

# Control IDs
ID_MAP_SELECT_BTN = 101
ID_LOAD_BTN = 103
ID_STEP_BTN = 104
ID_RUN_BTN = 105
ID_RUN_EVENT = 150

RunSimEvent, EVT_RUN_SIM = wx.lib.newevent.NewCommandEvent()

class Viewer(wx.Frame):
    def __init__(self, map_file, route):
        wx.Frame.__init__(self, None, -1, TITLE, size = (1000, 800), style = wx.DEFAULT_FRAME_STYLE)
        # Frame initializations.
        self.SetBackgroundColour(wx.LIGHT_GREY)
        self.SetMinSize((500, 300))
        # Child control initializations.
        self.mapInput = wx.TextCtrl(self, -1, map_file)
        self.mapLabel = wx.StaticText(self, -1, 'Map file:')
        self.mapSelectBtn = wx.Button(self, ID_MAP_SELECT_BTN, 'Select')
        self.routeInput = wx.TextCtrl(self, -1, route)
        self.routeLabel = wx.StaticText(self, -1, 'Route:')
        self.loadBtn = wx.Button(self, ID_LOAD_BTN, 'Load')
        self.stepBtn = wx.Button(self, ID_STEP_BTN, 'Step')
        self.stepInput = wx.SpinCtrl(self, -1, '1', min=1, max=3000000, initial=1)
        self.runBtn = wx.Button(self, ID_RUN_BTN, 'Run')
        self.canvas = Canvas(self)
        # Sizer layout.
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.mapSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.routeSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.canvasSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.commandSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer.Add(self.mapSizer, 0, flag = wx.EXPAND)
        self.mainSizer.Add(self.routeSizer, 0, flag = wx.EXPAND)
        self.mainSizer.Add(self.canvasSizer, 1, flag = wx.EXPAND)
        self.mapSizer.Add(self.mapLabel, 1, flag = wx.ALIGN_LEFT)
        self.mapSizer.Add(self.mapInput, 7, flag = wx.EXPAND)
        self.mapSizer.Add(self.mapSelectBtn, 0, flag = wx.ALIGN_RIGHT)
        self.routeSizer.Add(self.routeLabel, 1, flag = wx.ALIGN_LEFT)
        self.routeSizer.Add(self.routeInput, 7, flag = wx.EXPAND)
        self.canvasSizer.Add(self.commandSizer, 0, flag = wx.EXPAND)
        self.canvasSizer.Add(self.canvas, 1, flag = wx.EXPAND)
        self.commandSizer.Add(self.loadBtn, 0, flag = wx.EXPAND)
        self.commandSizer.Add(self.stepBtn, 0, flag = wx.EXPAND)
        self.commandSizer.Add(self.stepInput, 0, flag = wx.EXPAND)
        self.commandSizer.Add(self.runBtn, 0, flag = wx.EXPAND)
        self.SetSizer(self.mainSizer)
        # Status bar definitions.
        bar = self.CreateStatusBar(8)
        bar.SetStatusWidths([-2, -2, -2, -2, -2, -2, -2, -3])
        # Event initializations.
        self.Bind(wx.EVT_BUTTON, self.OnMapSelectBtn, id = ID_MAP_SELECT_BTN)
        self.Bind(wx.EVT_BUTTON, self.OnLoadBtn, id = ID_LOAD_BTN)
        self.Bind(wx.EVT_BUTTON, self.OnStepBtn, id = ID_STEP_BTN)
        self.Bind(wx.EVT_BUTTON, self.OnRunBtn, id = ID_RUN_BTN)
        self.Bind(EVT_RUN_SIM, self.OnRunEvent, id = ID_RUN_EVENT)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Simulation object.
        self.sim = None
        self.sim_running = False
        # Show window.
        self.Move((10, 10))
        self.Show()

    # Event handlers.
    def OnMapSelectBtn(self, event):
        #print 'OnMapSelectBtn'
        dlg = wx.FileDialog(self, 'Open map file', wildcard = 'Map (*.map)|*.map', style = wx.OPEN | wx.FILE_MUST_EXIST | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.mapInput.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnLoadBtn(self, event):
        #print 'OnLoadBtn'
        map_path = self.mapInput.GetValue()
        f = open(map_path)
        self.sim = f.readlines()
        self.canvas.SetMapSize(len(self.sim[0]), len(self.sim))
        self.UpdateStatusBar()

    def OnStepBtn(self, event):
        #print 'OnStepBtn'
        self.Run(int(self.stepInput.GetValue()))

    def OnRunBtn(self, event):
        #print 'OnRunBtn'
        if self.sim_running:
            self.sim_running = False
            self.runBtn.SetLabel('Run')
        else:
            self.sim_running = True
            self.runBtn.SetLabel('Stop')
            self.AddPendingEvent(RunSimEvent(id=ID_RUN_EVENT))

    def OnRunEvent(self, event):
        #print 'OnRunEvent'
        self.Run(int(self.stepInput.GetValue()))

    def OnClose(self, event):
        #print 'OnClose'
        self.Destroy()

    def Run(self, steps):
        self.canvas.Refresh()
        self.UpdateStatusBar()

    def UpdateStatusBar(self):
        bar = self.GetStatusBar()

class Canvas(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        # Requested world size.
        self.xwrq = 10
        self.ywrq = 10
        # Actual world size.
        self.xw = 10
        self.yw = 10
        # Draw area size in pixels.
        self.xp = 160
        self.yp = 160
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        # load bitmaps
        self.bmpClosedLift = wx.Bitmap(os.path.join("images", "closed-lift.jpg"));
        self.bmpEarth = wx.Bitmap(os.path.join("images", "earth.jpg"));
        self.bmpEmpty = wx.Bitmap(os.path.join("images", "empty.jpg"));
        self.bmpLambda = wx.Bitmap(os.path.join("images", "lambda.jpg"));
        self.bmpOpenLift = wx.Bitmap(os.path.join("images", "open-lift.jpg"));
        self.bmpRobot = wx.Bitmap(os.path.join("images", "robot.jpg"));
        self.bmpRock = wx.Bitmap(os.path.join("images", "rock.jpg"));
        self.bmpWall = wx.Bitmap(os.path.join("images", "wall.jpg"));

    def OnSize(self, event):
        #print 'Canvas.OnSize'
        size = self.GetClientSize()
        self.xp = size.x
        self.yp = size.y
        self.UpdateMapSize()

    def OnPaint(self, event):
        #print 'Canvas.OnPaint'
        dc = wx.PaintDC(self)
        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        parent = self.GetParent()
        if parent.sim is not None:
            def bmpFromObj(obj):
                return {"#": self.bmpWall,
                        "R": self.bmpRobot,
                        "*": self.bmpRock,
                        "\\": self.bmpLambda,
                        "L": self.bmpClosedLift,
                        "O": self.bmpOpenLift,
                        ".": self.bmpEarth,
                        " ": self.bmpEmpty}[obj]
            for y, line in enumerate(parent.sim):
                for x, pos in enumerate(line.strip()):
                    bmp = bmpFromObj(pos)
                    dc.DrawBitmap(bmp, x*16, y*16, True)

    def SetMapSize(self, xw, yw):
        self.xwrq = xw
        self.ywrq = yw
        self.UpdateMapSize()

    def UpdateMapSize(self):
        if (self.xwrq / self.xp) < (self.ywrq / self.yp):
            scale = self.ywrq / self.yp # m / pixel
        else:
            scale = self.xwrq / self.xp # m / pixel
        # Size in world coordinates.
        self.xw = scale * self.xp
        self.yw = scale * self.yp
        self.scale = scale
        self.Refresh()
        #print 'Set world size:', self.xw / EARTH_RADIUS, self.yw / EARTH_RADIUS, 'Scale = %.3e m/pxl' % scale

if __name__ == '__main__':
    map_file = ''
    route = ''
    if len(sys.argv) > 1:
        map_file = sys.argv[1]
    if len(sys.argv) > 2:
        route = sys.argv[2]
    app = wx.App(False)
    viewer = Viewer(map_file, route)
    app.MainLoop()
