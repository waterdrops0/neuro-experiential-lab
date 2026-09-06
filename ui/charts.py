from collections import deque
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

class LiveCharts(QWidget):
    def __init__(self, window=120):
        super().__init__()
        self.window = window
        self.points = deque()
        layout = QVBoxLayout(self)
        pg.setConfigOptions(antialias=True, foreground='#b8c9d9')
        self.hr_plot = pg.PlotWidget(title='Heart Rate · last 120 seconds', background='#101b28')
        self.rr_plot = pg.PlotWidget(title='RR / RMSSD · last 120 seconds', background='#101b28')
        for plot in (self.hr_plot, self.rr_plot):
            plot.showGrid(x=True, y=True, alpha=.15)
            plot.setLabel('bottom', 'Time relative to now', units='s')
            plot.setMouseEnabled(x=False, y=False)
            layout.addWidget(plot)
        self.hr_plot.setLabel('left', 'HR', units='BPM')
        self.rr_plot.setLabel('left', 'Interval', units='ms')
        self.rr_plot.addLegend()
        self.hr_curve = self.hr_plot.plot(pen=pg.mkPen('#42d3b0', width=2))
        self.rr_curve = self.rr_plot.plot(pen=pg.mkPen('#70afff', width=2), name='RR')
        # Separate right axis keeps the much smaller RMSSD trend readable.
        self.hrv_view = pg.ViewBox()
        self.rr_plot.showAxis('right')
        self.rr_plot.scene().addItem(self.hrv_view)
        self.rr_plot.getAxis('right').linkToView(self.hrv_view)
        self.rr_plot.getAxis('right').setLabel('RMSSD', units='ms', color='#edbc72')
        self.hrv_view.setXLink(self.rr_plot.getViewBox())
        self.hrv_curve = pg.PlotCurveItem(pen=pg.mkPen('#edbc72', width=2))
        self.hrv_view.addItem(self.hrv_curve)
        self.rr_plot.getViewBox().sigResized.connect(self.resize_hrv)
        self.resize_hrv()

    def resize_hrv(self):
        self.hrv_view.setGeometry(self.rr_plot.getViewBox().sceneBoundingRect())
        self.hrv_view.linkedViewChanged(self.rr_plot.getViewBox(), self.hrv_view.XAxis)

    def add(self, sample):
        self.points.append(sample)

    def refresh(self, now):
        while self.points and self.points[0].monotonic_time < now-self.window:
            self.points.popleft()
        points = list(self.points)
        xs = [p.monotonic_time-now for p in points]
        self.hr_curve.setData(xs, [p.hr for p in points])
        self.rr_curve.setData(xs, [p.rr for p in points])
        valid = [p for p in points if p.rmssd is not None]
        self.hrv_curve.setData([p.monotonic_time-now for p in valid], [p.rmssd for p in valid])
        for plot in (self.hr_plot, self.rr_plot):
            plot.setXRange(-self.window, 0, padding=0)
