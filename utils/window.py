from PySide6.QtWidgets import QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
from utils.components import MultButton
import pyqtgraph as pg
import numpy as np

class BaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'base_wgt'
        self.setParent(parent)

    def init_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(MultButton)
        file = QFile(f'./ui/{self.name}.ui')
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, self)

class ControlPane(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'ctrl_pane'
        self.init_ui()
    
    def init_ui(self):
        super().init_ui()
        print()

class WaveCanvas(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'wave_pane'
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(self.parent().size())

        self.xs = list(range(100))
        self.ys = [np.sin(x/10) for x in range(100)]
        self.setBackground('w')
        self.pen = pg.mkPen(color=(255, 0, 0))
        self.ch1_line = self.plot(self.xs, self.ys, pen=self.pen)

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.grab_data)
        self.timer.start()

    def grab_data(self):
        self.xs = self.xs[1:]
        self.xs.append(self.xs[-1] + 1)
        self.ys = self.ys[1:]
        self.ys.append(np.sin(self.xs[-1]/10))
        self.ch1_line.setData(self.xs, self.ys)
        


class MainWindow(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'main_window'
        self.init_ui()

    def init_ui(self):
        super().init_ui()
        self.ctrl_pane = ControlPane(self.ui.ctrl_pane_container)
        self.wave_pane = WaveCanvas(self.ui.wave_pane_container)
        # self.ui.wave_pane_container.setCentralWidget(self.wave_pane)
