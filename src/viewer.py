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
        self._map_input = wx.TextCtrl(self, -1, map_file)
        self._map_label = wx.StaticText(self, -1, 'Map file:')
        self._map_select_btn = wx.Button(self, ID_MAP_SELECT_BTN, 'Select')
        self._route_input = wx.TextCtrl(self, -1, route)
        self._route_label = wx.StaticText(self, -1, 'Route:')
        self._load_btn = wx.Button(self, ID_LOAD_BTN, 'Load')
        self._step_btn = wx.Button(self, ID_STEP_BTN, 'Step')
        self._step_input = wx.SpinCtrl(self, -1, '1', min=1, max=3000000, initial=1)
        self._run_btn = wx.Button(self, ID_RUN_BTN, 'Run')
        self._canvas = Canvas(self)
        self._canvas.EnableScrolling(True, True)
        # Sizer layout.
        self._main_sizer = wx.BoxSizer(wx.VERTICAL)
        self._map_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._route_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._canvas_area_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._canvas_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._command_sizer = wx.BoxSizer(wx.VERTICAL)
        self._main_sizer.Add(self._map_sizer, 0, flag = wx.EXPAND)
        self._main_sizer.Add(self._route_sizer, 0, flag = wx.EXPAND)
        self._main_sizer.Add(self._canvas_area_sizer, 1, flag = wx.EXPAND)
        self._map_sizer.Add(self._map_label, 1, flag = wx.ALIGN_LEFT)
        self._map_sizer.Add(self._map_input, 7, flag = wx.EXPAND)
        self._map_sizer.Add(self._map_select_btn, 0, flag = wx.ALIGN_RIGHT)
        self._route_sizer.Add(self._route_label, 1, flag = wx.ALIGN_LEFT)
        self._route_sizer.Add(self._route_input, 7, flag = wx.EXPAND)
        self._canvas_area_sizer.Add(self._command_sizer, 0, flag = wx.EXPAND)
        self._canvas_area_sizer.Add(self._canvas_sizer, 1, flag = wx.EXPAND)
        self._canvas_sizer.Add(self._canvas, 1, flag = wx.EXPAND)
        self._command_sizer.Add(self._load_btn, 0, flag = wx.EXPAND)
        self._command_sizer.Add(self._step_btn, 0, flag = wx.EXPAND)
        self._command_sizer.Add(self._step_input, 0, flag = wx.EXPAND)
        self._command_sizer.Add(self._run_btn, 0, flag = wx.EXPAND)
        self.SetSizer(self._main_sizer)
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
        dlg = wx.FileDialog(self,
                            'Open map file',
                            wildcard = 'Map (*.map)|*.map',
                            style = wx.OPEN | wx.FILE_MUST_EXIST | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self._map_input.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnLoadBtn(self, event):
        #print 'OnLoadBtn'
        map_path = self._map_input.GetValue()
        f = open(map_path)
        map_def = f.readlines()
        f.close()
        w = max((len(line) - 1 for line in map_def))
        h = len(map_def)
        self.sim = []
        for line in map_def:
            self.sim.append(line[0:-1] + " "*(w-(len(line)-1)))
        self._canvas.SetMapSize(w, h)
        self.UpdateStatusBar()

    def OnStepBtn(self, event):
        #print 'OnStepBtn'
        self.Run(int(self._step_input.GetValue()))

    def OnRunBtn(self, event):
        #print 'OnRunBtn'
        if self.sim_running:
            self.sim_running = False
            self._run_btn.SetLabel('Run')
        else:
            self.sim_running = True
            self._run_btn.SetLabel('Stop')
            self.AddPendingEvent(RunSimEvent(id=ID_RUN_EVENT))

    def OnRunEvent(self, event):
        #print 'OnRunEvent'
        self.Run(int(self._step_input.GetValue()))

    def OnClose(self, event):
        #print 'OnClose'
        self.Destroy()

    def Run(self, steps):
        self._canvas.Refresh()
        self.UpdateStatusBar()

    def UpdateStatusBar(self):
        bar = self.GetStatusBar()

class Canvas(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        # load bitmaps
        self._bmp_closed_lift = wx.Bitmap(os.path.join("images", "closed-lift.jpg"));
        self._bmp_earth = wx.Bitmap(os.path.join("images", "earth.jpg"));
        self._bmp_empty = wx.Bitmap(os.path.join("images", "empty.jpg"));
        self._bmp_lambda = wx.Bitmap(os.path.join("images", "lambda.jpg"));
        self._bmp_open_lift = wx.Bitmap(os.path.join("images", "open-lift.jpg"));
        self._bmp_robot = wx.Bitmap(os.path.join("images", "robot.jpg"));
        self._bmp_rock = wx.Bitmap(os.path.join("images", "rock.jpg"));
        self._bmp_wall = wx.Bitmap(os.path.join("images", "wall.jpg"));
        # Ensure scrollbars are used
        self.SetMapSize(10, 10)

    def OnSize(self, event):
        #print 'Canvas.OnSize'
        pass

    def OnPaint(self, event):
        #print 'Canvas.OnPaint'
        dc = wx.PaintDC(self)
        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.LIGHT_GREY_BRUSH)
        dc.SetBackground(wx.LIGHT_GREY_BRUSH)
        dc.Clear()
        parent = self.GetParent()
        if parent.sim is not None:
            def bmp_from_obj(obj):
                return {"#": self._bmp_wall,
                        "R": self._bmp_robot,
                        "*": self._bmp_rock,
                        "\\": self._bmp_lambda,
                        "L": self._bmp_closed_lift,
                        "O": self._bmp_open_lift,
                        ".": self._bmp_earth,
                        " ": self._bmp_empty}[obj]
            for y, line in enumerate(parent.sim):
                for x, pos in enumerate(line):
                    bmp = bmp_from_obj(pos)
                    p = self.CalcScrolledPosition((x*16, y*16))
                    dc.DrawBitmap(bmp, p.x, p.y, True)

    def SetMapSize(self, xw, yw):
        self._xp = 16 * xw
        self._yp = 16 * yw
        self.UpdateMapSize()

    def UpdateMapSize(self):
        # Size in world coordinates.
        self.SetClientSize((self._xp, self._yp))
        self.SetScrollbars(1, 1, self._xp, self._yp)
        self.SetScrollRate(16, 16)
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
