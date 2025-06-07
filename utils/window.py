from PySide6.QtWidgets import QWidget, QComboBox, QGraphicsView, QButtonGroup, QDoubleSpinBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer, SignalInstance
from utils.components import MultButton, DiscreteSlider, DynamicLabel
from utils.dsp import Channel, Measurement
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
        """ Loads ui from .ui file, initialises any components """

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
        self.init_connections()
    
    def init_ui(self):
        super().init_ui()
        self.init_dlbls()
        self.init_sboxes()
        self.init_mbtns()
        self.init_cboxes()
        self.init_dslds()
        self.init_slds()
        self.init_btngrps()

    def init_dlbls(self):
        """ Inits the DynamicLabels """

        self.ui.hscale_dlbl.init(['5', 'm'], '{} {}s / div')
        self.ui.vscale_dlbl.init(['500', 'm'], '{} {}V / div')

    def init_sboxes(self):
        self.ui.trig_pretrg_sbox.setValue(0.5)

    def init_mbtns(self):
        """ Inits the MultButtons """

        # TODO: cover all mbtns
        self.ui.run_stop_mbtn.init([
                {'index'     : 0,
                 'state_name': 'stop',
                 'stylesheet': 'background-color: red;',
                 'text'      : self.ui.run_stop_mbtn.text()},
                 {'index'     : 1,
                 'state_name': 'run',
                 'stylesheet': 'background-color: green;',
                 'text'      : self.ui.run_stop_mbtn.text()}])
        self.ui.run_stop_mbtn.set_state(1)
        self.ui.v_coupling_mbtn.init([
                {'index'     : 0,
                 'state_name': 'dc',
                 'stylesheet': '',
                 'text'      : 'DC'},
                {'index'     : 1,
                 'state_name': 'ac',
                 'stylesheet': '',
                 'text'      : 'AC'}])
        self.ui.fft_vscale_mbtn.init([
                {'index'     : 0,
                 'state_name': 'dbv',
                 'stylesheet': '',
                 'text'      : Channel.DBV},
                {'index'     : 1,
                 'state_name': 'vrms',
                 'stylesheet': '',
                 'text'      : Channel.VRMS}])

    def init_cboxes(self):
        """ Inits the QComboBoxes """

        # TODO: cover all cboxes
        self.ui.fft_window_cbox.addItems([Channel.HAMMING,
                                          Channel.HANN,
                                          Channel.RECT])   # Optional add-on: Blackman, Flattop
        self.ui.measure_type_cbox.addItems([Measurement.MAX,
                                            Measurement.MIN,
                                            Measurement.RMS])   # Optional add-on: Blackman, Flattop

    def init_dslds(self):
        """ Inits the DiscreteSliders """

        # TODO: cover all dslds
        self.ui.hscale_dsld.set_levels([0.005, 0.1, 1])
        self.ui.vscale_dsld.set_levels([0.5, 1, 5])
        

    def init_slds(self):
        """ Inits the QSliders """

        # TODO: cover all slds
        self.ui.hoffset_sld.setRange(-180, 179)
        self.ui.hoffset_sld.setValue(0)
        self.ui.trig_pretrg_sld.setRange(0,100)
        self.ui.trig_pretrg_sld.setValue(50)

    def init_btngrps(self):
        """ Init button groups """

        self.trig_btngrp = QButtonGroup(self.ui)
        self.trig_btngrp.setExclusive(True)
        self.trig_btngrp.addButton(self.ui.trig_type_sing_btn, 0)
        self.trig_btngrp.addButton(self.ui.trig_type_none_btn, 1)
        self.trig_btngrp.addButton(self.ui.trig_type_rise_btn, 2)
        self.trig_btngrp.addButton(self.ui.trig_type_fall_btn, 3)
        self.trig_btngrp.addButton(self.ui.trig_type_risefall_btn, 4)
        for btn in self.trig_btngrp.buttons():
            btn.setCheckable(True)
        self.ui.trig_type_none_btn.setChecked(True)

    def init_connections(self):
        self.ui.hscale_dsld.snapped.connect(
            lambda val: self.ui.hscale_dlbl.update_unit(val))
        self.ui.vscale_dsld.snapped.connect(
            lambda val: self.ui.vscale_dlbl.update_unit(val))
        self.ui.trig_threshold_sld.valueChanged.connect(
            lambda val: self.ui.trig_threshold_sbox.setValue(round(val/100, 2)))
        self.ui.trig_threshold_sbox.valueChanged.connect(
            lambda val: self.ui.trig_threshold_sld.setValue(int(val*100)))
        self.ui.trig_pretrg_sld.valueChanged.connect(
            lambda val: self.ui.trig_pretrg_sbox.setValue(round(val/100, 2)))
        self.ui.trig_pretrg_sbox.valueChanged.connect(
            lambda val: self.ui.trig_pretrg_sld.setValue(int(val*100)))

class WaveCanvas(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'wave_pane'
        self.lines:list[pg.PlotDataItem] = []
        self.fft_view:pg.ViewBox = None
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(self.parent().size())
        self.getViewBox().setMouseEnabled(x=False, y=False)
        self.setBackground('black')
    
    def add_channel(self, chn:Channel):
        """ Adds a line in plot to represent added channel """

        pen = pg.mkPen(color=chn.color, width=3)
        if not chn.is_fft:
            line = self.plot(np.arange(len(chn)), np.zeros(len(chn)), pen=pen)
        else:
            if self.fft_view is None:
                self.add_viewbox()
            line = pg.PlotDataItem(np.arange(len(chn)), np.zeros(len(chn)), pen=pen)
            self.fft_view.addItem(line)
        self.lines.append(line)

    def update(self, line_idx:int, data:np.ndarray):
        self.lines[line_idx].setData(np.arange(len(data)), data)

    def add_viewbox(self):
        pi = self.getPlotItem()
        self.fft_view = pg.ViewBox()
        self.fft_view.setXLink(pi.vb)
        pi.showAxis('right')
        right_axis = pi.getAxis('right')
        right_axis.setPen(pg.mkPen('w'))
        right_axis.linkToView(self.fft_view)
        pi.scene().addItem(self.fft_view)

        def update_views():
            self.fft_view.setGeometry(pi.vb.sceneBoundingRect())
            self.fft_view.linkedViewChanged(pi.vb, self.fft_view.XAxis)
        
        pi.vb.sigResized.connect(update_views)
        update_views()

class StatusBar(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'stat_bar'
        self.init_ui()
    
    def init_ui(self):
        super().init_ui()
        self.init_dlbls()
        self.init_mbtns()

    def init_dlbls(self):
        """ Inits the DynamicLabels """
        
        self.ui.meas_1_dlbl.init(['Ch_', '_', '2', 'm', 'V'], '{}\n{} = {} {}{}', 2, 3)
        self.ui.meas_2_dlbl.init(['Ch_', '_', '2', 'm', 'V'], '{}\n{} = {} {}{}', 2, 3)
        self.ui.meas_3_dlbl.init(['Ch_', '_', '2', 'm', 'V'], '{}\n{} = {} {}{}', 2, 3)
        self.ui.meas_4_dlbl.init(['Ch_', '_', '2', 'm', 'V'], '{}\n{} = {} {}{}', 2, 3)

    def init_mbtns(self):
        """ Inits the MultButtons """

        self.ui.ch1_mbtn.init([
                {'index'     : 0,
                 'state_name': 'off',
                 'stylesheet': 'background-color: none',
                 'text'      : self.ui.ch1_mbtn.text()},
                {'index'     : 1,
                 'state_name': 'on',
                 'stylesheet': 'background-color: rgb(236, 252, 32)',
                 'text'      : self.ui.ch1_mbtn.text()}])
        self.ui.ch1_mbtn.set_state(1)
        self.ui.fft_mbtn.init([
                {'index'     : 0,
                 'state_name': 'off',
                 'stylesheet': 'background-color: none',
                 'text'      : self.ui.fft_mbtn.text()},
                {'index'     : 1,
                 'state_name': 'on',
                 'stylesheet': 'background-color: rgb(13, 215, 230)',
                 'text'      : self.ui.fft_mbtn.text()}])

class MainWindow(BaseWidget):
    """ All subsystems are connected together in the main window. """

    DEFAULT_SIMPLE_CHANNEL_LENGTH          = 500
    DEFAULT_SIMPLE_CHANNEL_SAMPLING_PERIOD = 1/50_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = 'main_window'
        self.channels:list[Channel] = []
        self.measurements = []
        self.init_ui()
        self.init_dsp()

    def init_ui(self):
        super().init_ui()
        self.ctrl_pane = ControlPane(self.ui.ctrl_pane_container)
        self.wave_pane = WaveCanvas(self.ui.wave_pane_container)
        self.stat_bar  = StatusBar(self.ui.stat_bar_container)

    def init_dsp(self):
        """ Inits the DSP backend """

        self.arduino = Arduino()
        self.arduino.start()
        # Init channel 1 by default
        self.add_simple_channel('Channel 1', self.arduino.chn_1_serial_input)
        self.set_trig_src()

        # Default not show FFT
        self.add_fft_channel(self.channels[0], Channel.DBV, Channel.HAMMING,
                             5000, 2000)
        self.ctrl_pane.ui.fft_vscale_mbtn.clicked.connect(self.set_fft_vscale)
        self.ctrl_pane.ui.fft_window_cbox.currentTextChanged.connect(self.set_fft_window)
        self.toggle_channel_on_off(1, False)

        self.ctrl_pane.ui.run_stop_mbtn.clicked.connect(
            lambda: self.toggle_run_stop(self.ctrl_pane.ui.run_stop_mbtn.state['index']))
        self.stat_bar.ui.ch1_mbtn.clicked.connect(
            lambda: self.toggle_channel_on_off(0, self.stat_bar.ui.ch1_mbtn.state['index']))
        self.stat_bar.ui.fft_mbtn.clicked.connect(
            lambda: self.toggle_channel_on_off(1, self.stat_bar.ui.fft_mbtn.state['index']))

    def toggle_channel_on_off(self, chn_idx:int, on_off:bool):
        """ Deactivates a channel and hides its line """

        if self.ctrl_pane.ui.run_stop_mbtn.state['index']:
            self.channels[chn_idx].set_active(on_off)
        if on_off:
            self.wave_pane.lines[chn_idx].show()
        else:
            self.wave_pane.lines[chn_idx].hide()

    def toggle_run_stop(self, run_stop:bool):
        """ Deactivates all channels but do not hide their line """

        for chn in self.channels:
            chn.set_active(run_stop)

    def add_simple_channel(self, chn_name:str, src:SignalInstance):
        """ Sets up and appends a simple channel to self.channels.
        
        :param chn_name: (str) either 'Channel 1' or 'Channel 2'.
        """

        chns_count = len(self.channels)
        chn = Channel()
        chn.name = chn_name
        if chn_name == 'Channel 1':
            chn.color = np.array([236, 252, 32, 180])
        elif chn_name == 'Channel 2':
            chn.color = np.array([61, 222, 57, 180])
        chn.set_length(self.DEFAULT_SIMPLE_CHANNEL_LENGTH)
        chn.trig_mode = chn.NONE
        self.wave_pane.add_channel(chn)
        chn.frame_ready.connect(
            lambda val: self.wave_pane.update(chns_count, val))
        chn.init_source(src)
        self.channels.append(chn)

    def add_fft_channel(self, source_chn:Channel, scale, window, span, centre, fft_size=2048):
        """ Inits an FFT channel from a source channel. """

        chns_count = len(self.channels)
        chn = Channel()
        chn.name = 'FFT'
        chn.color = np.array([13, 215, 230, 180])
        chn.init_fft(vscale=scale, window=window, span=span,
                     center=centre, fft_size=fft_size)
        self.wave_pane.add_channel(chn)
        chn.frame_ready.connect(
            lambda val: self.wave_pane.update(chns_count, val))
        chn.init_source(source_chn.source)
        self.channels.append(chn)

    def set_trig_src(self):
        """ Changes source channel for trigger control """

        # For two channels:
        # new_chn_idx = self.ctrl_pane.ui.trig_src_mbtn.state['index']
        new_chn_idx = 0
        self.ctrl_pane.trig_btngrp.idToggled.disconnect()
        self.ctrl_pane.ui.trig_threshold_sbox.valueChanged.disconnect()
        self.ctrl_pane.ui.trig_threshold_sbox.valueChanged.connect(
            lambda val: self.ctrl_pane.ui.trig_threshold_sld.setValue(int(val*100)))
        self.ctrl_pane.ui.trig_pretrg_sbox.valueChanged.disconnect()
        self.ctrl_pane.ui.trig_pretrg_sbox.valueChanged.connect(
            lambda val: self.ctrl_pane.ui.trig_pretrg_sld.setValue(int(val*100)))

        self.ctrl_pane.trig_btngrp.idToggled.connect(
            lambda id, _: self.channels[new_chn_idx].set_trig_mode(id))
        self.ctrl_pane.ui.trig_threshold_sbox.valueChanged.connect(
            lambda val: self.channels[new_chn_idx].set_trig_threshold_percentage(val))
        self.ctrl_pane.ui.trig_pretrg_sbox.valueChanged.connect(
            lambda val: self.channels[new_chn_idx].set_pretrg(val))

    def set_fft_vscale(self):
        new_vscale_idx = self.ctrl_pane.ui.fft_vscale_mbtn.state['index']
        fft_chn = next(chn for chn in self.channels if chn.name == 'FFT')
        fft_chn.fft_vscale = (fft_chn.DBV, fft_chn.VRMS)[new_vscale_idx]

    def set_fft_window(self, new_window:str):
        fft_chn = next(chn for chn in self.channels if chn.name == 'FFT')
        fft_chn.set_fft_window(new_window)

    def add_measurement(self):
        src_chn_name = self.ctrl_pane.ui.measure_src_cbox.currentText()
        src_chn = next(chn for chn in self.channels if chn.name == src_chn_name)
        meas_type = self.ctrl_pane.ui.measure_type_cbox.currentText()
        measurement = Measurement()
        measurement.init(src_chn, meas_type)
        self.measurements.append(measurement)
        self.stat_bar.ui.meas_1_dlbl.dynamic_texts = [
            src_chn.title(0), meas_type, 0, 'm', 'V']
        measurement.meas_ready.connect(
            lambda val: self.stat_bar.ui.meas_1_dlbl.update_unit(val))
