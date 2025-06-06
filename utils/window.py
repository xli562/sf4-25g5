from PySide6.QtWidgets import QWidget, QComboBox, QGraphicsView, QButtonGroup
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer
from utils.components import MultButton, DiscreteSlider, DynamicLabel
from utils.dsp import Channel
from utils.comms import Arduino
from utils.xlogging import get_logger
import pyqtgraph as pg
import numpy as np


logger = get_logger()

class BaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'base_wgt'
        self.setParent(parent)

    def init_ui(self):
        """ Loads ui from .ui file """

        loader = QUiLoader()
        loader.registerCustomWidget(MultButton)
        loader.registerCustomWidget(DiscreteSlider)
        loader.registerCustomWidget(DynamicLabel)
        file = QFile(f'./ui/{self.name}.ui')
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, self)

class ControlPane(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'ctrl_pane'
        self.init_ui()
    
    def init_ui(self):
        """ Loads ui, initialises components """

        super().init_ui()
        self.init_dlbls()
        self.init_mbtns()
        self.init_cboxes()
        self.init_dslds()
        self.init_slds()
        self.init_btngrps()

    def init_dlbls(self):
        """ Inits the DynamicLabels """

        self.ui.hscale_dlbl.init(['5', 'm'], '{} {}s / div')
        self.ui.vscale_dlbl.init(['500', 'm'], '{} {}V / div')

    def init_mbtns(self):
        """ Inits the MultButtons """

        # TODO: cover all mbtns
        self.ui.run_stop_mbtn.init([
                {'index'     : 0,
                 'state_name': 'run',
                 'stylesheet': 'background-color: green;',
                 'text'      : self.ui.run_stop_mbtn.text()},
                {'index'     : 1,
                 'state_name': 'stop',
                 'stylesheet': 'background-color: red;',
                 'text'      : self.ui.run_stop_mbtn.text()}])
        self.ui.v_src_mbtn.init([
                {'index'     : 0,
                 'state_name': 'ch1',
                 'stylesheet': '',
                 'text'      : 'Channel 1'},
                {'index'     : 1,
                 'state_name': 'ch2',
                 'stylesheet': '',
                 'text'      : 'Channel 2'}])
        self.ui.v_coupling_mbtn.init([
                {'index'     : 0,
                 'state_name': 'dc',
                 'stylesheet': '',
                 'text'      : 'DC'},
                {'index'     : 1,
                 'state_name': 'ac',
                 'stylesheet': '',
                 'text'      : 'AC'}])
        self.ui.fft_src_mbtn.init([
                {'index'     : 0,
                 'state_name': 'ch1',
                 'stylesheet': '',
                 'text'      : 'Chn. 1'},
                {'index'     : 1,
                 'state_name': 'ch2',
                 'stylesheet': '',
                 'text'      : 'Chn. 2'}])
        self.ui.fft_vscale_mbtn.init([
                {'index'     : 0,
                 'state_name': 'db',
                 'stylesheet': '',
                 'text'      : 'dB'},
                {'index'     : 1,
                 'state_name': 'vrms',
                 'stylesheet': '',
                 'text'      : 'Vrms'}])
        self.ui.arith_src1_mbtn.init([
                {'index'     : 0,
                 'state_name': 'ch1',
                 'stylesheet': '',
                 'text'      : 'Chn. 1'},
                {'index'     : 1,
                 'state_name': 'ch2',
                 'stylesheet': '',
                 'text'      : 'Chn. 2'}])
        self.ui.arith_src2_mbtn.init([
                {'index'     : 0,
                 'state_name': 'ch1',
                 'stylesheet': '',
                 'text'      : 'Chn. 1'},
                {'index'     : 1,
                 'state_name': 'ch2',
                 'stylesheet': '',
                 'text'      : 'Chn. 2'}])
        self.ui.arith_op_mbtn.init([
                {'index'     : 0,
                 'state_name': 'add',
                 'stylesheet': '',
                 'text'      : '+'},
                {'index'     : 1,
                 'state_name': 'sub',
                 'stylesheet': '',
                 'text'      : '-'},
                 {'index'     : 2,
                 'state_name': 'mul',
                 'stylesheet': '',
                 'text'      : 'x'},
                 {'index'     : 3,
                 'state_name': 'div',
                 'stylesheet': '',
                 'text'      : '/'}])
        self.ui.trig_src_mbtn.init([
                {'index'     : 0,
                 'state_name': 'ch1',
                 'stylesheet': '',
                 'text'      : 'Chn. 1'},
                {'index'     : 1,
                 'state_name': 'ch2',
                 'stylesheet': '',
                 'text'      : 'Chn. 2'}])

    def init_cboxes(self):
        """ Inits the QComboBoxes """

        # TODO: cover all cboxes
        self.ui.fft_window_cbox.addItems(['Hamming', 'Hann', 'Rect'])   # Optional add-on: Blackman, Flattop

    def init_dslds(self):
        """ Inits the DiscreteSliders """

        # TODO: cover all dslds
        self.ui.hscale_dsld.set_levels([0.005, 0.1, 1])
        self.ui.hscale_dsld.snapped.connect(
            lambda val: self.ui.hscale_dlbl.update_unit(val)
        )
        self.ui.vscale_dsld.set_levels([0.5, 1, 5])
        self.ui.vscale_dsld.snapped.connect(
            lambda val: self.ui.vscale_dlbl.update_unit(val)
        )
        self.ui.trig_pretrg_dsld.set_levels(list(range(0, 101, 10)))
        # self.ui.trig_pretrg_dsld.snapped.connect(
        #     lambda val: self.ui.vscale_dlbl.update_text(0, val)
        # )

    def init_slds(self):
        """ Inits the QSliders """

        # TODO: cover all slds
        self.ui.hoffset_sld.setRange(-180, 179)
        self.ui.hoffset_sld.setValue(0)

    def init_btngrps(self):
        """ Init button groups """
        self.trig_btngrp = QButtonGroup(self.ui)
        self.trig_btngrp.addButton(self.ui.trig_type_sing_btn)
        self.trig_btngrp.addButton(self.ui.trig_type_none_btn)
        self.trig_btngrp.addButton(self.ui.trig_type_rise_btn)
        self.trig_btngrp.addButton(self.ui.trig_type_fall_btn)
        self.trig_btngrp.addButton(self.ui.trig_type_risefall_btn)
        self.ui.trig_type_none_btn.setChecked(True)

class WaveCanvas(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'wave_pane'
        self.channels:list[Channel] = []
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(self.parent().size())
        self.getViewBox().setMouseEnabled(x=False, y=False)

        self.xs = np.array([])
        self.ys = np.array([])
        self.setBackground('w')
        self.pen = pg.mkPen(color=(255, 0, 0))
        self.ch1_line = self.plot(self.xs, self.ys, pen=self.pen)
    
    def add_channel(self, chn):
        """ Adds a channel to the wave canvas """
        chn.frame_ready.connect(lambda val: self.update(val))
        self.channels.append(chn)
    
    def update(self, data):
        self.xs = np.arange(self.channels[0]._len)
        self.ys = data
        self.ch1_line.setData(self.xs, self.ys)

class StatusBar(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'stat_bar'
        self.init_ui()
    
    def init_ui(self):
        """ Loads ui, initialises components """

        super().init_ui()
        self.init_dlbls()
        self.init_mbtns()

    def init_dlbls(self):
        """ Inits the DynamicLabels """
        pass

    def init_mbtns(self):
        """ Inits the MultButtons """

        # TODO: cover all mbtns
        pass


class MainWindow(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'main_window'
        self.init_ui()

    def init_ui(self):
        super().init_ui()
        self.ctrl_pane = ControlPane(self.ui.ctrl_pane_container)
        self.wave_pane = WaveCanvas(self.ui.wave_pane_container)
        self.stat_bar  = StatusBar(self.ui.stat_bar_container)
        self.arduino = Arduino()
        self.arduino.start()
        self.chn1 = Channel()
        # self.chn1.set_length(500)
        self.chn1.trig_mode = Channel.RISE
        self.wave_pane.add_channel(self.chn1)
        self.chn1.init_source(self.arduino.chn_1_serial_input)

        