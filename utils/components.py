import pint
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QSlider, QLabel
from utils.xlogging import get_logger


logger = get_logger()

class MultButton(QPushButton):
    """ e.g. for Channel 1 / 2 selection """

    def __init__(self, parent=None, states:list[dict]=[]):
        super().__init__(parent)
        self.set_states(states)
        if self.states:
            self.set_state()
        else:
            self.state = {}
        self.clicked.connect(self.cycle_state)

    def init(self, states:list[dict]):
        self.set_states(states)
        self.set_state(0)

    def set_states(self, states:list[dict]):
        """ Sets self.states
        
        states = {'index'     : (int),
                  'state_name': (str),
                  'stylesheet': (str),
                  'text'      : (str) }
        """
        self.states = states

    def set_state(self, index):
        """ Sets state of button. Only updates stylesheet if stylesheet not empty.
         
        :param index: (int | str) index of state in
        self.states, or name of state as string.
        """
        if isinstance(index, int):
            self.state = self.states[index]
        elif isinstance(index, str):
            self.state = next(state for state in self.states if state['state_name'] == index)
        stylesheet = self.state['stylesheet']
        text = self.state['text']
        
        if stylesheet:
            self.setStyleSheet(stylesheet)
        self.setText(text)

    def cycle_state(self):
        """ Cycles between different options """

        self.set_state((self.state['index'] + 1) % len(self.states))

class DiscreteSlider(QSlider):
    """ Slider that snaps to discrete values """

    snapped = Signal(float)

    def __init__(self, parent=None):
        """ Initialises the discrete slider. """
        # TODO: Set default value (read from stored default settings)
        super().__init__(parent)
        self.levels = []
        self.level = 0.0
        self.step = 0
        self.range = self.maximum() - self.minimum() + 1
        self.valueChanged.connect(self.snap)

    def __len__(self):
        return len(self.levels)
        
    def set_levels(self, levels:list[float]):
        """ Sets discrete levels of slider.
        
        :param levels: (list[float]) e.g. = [0.5, 1, 5] for [500mV, 1V, 5V]
        """

        self.levels = levels
        self.step = round((self.maximum() - self.minimum()) / (len(self) - 1))
        self.setSingleStep(self.step)

    def snap(self, val:int):
        """ Snaps slider to discrete levels """

        snapped_val = round(val / self.step) * self.step
        self.level = self.levels[int(snapped_val / self.step)]
        if snapped_val != val:
            # block signals to avoid recursion
            self.blockSignals(True)
            self.setValue(snapped_val)
            self.blockSignals(False)
            self.snapped.emit(self.level)

class DynamicLabel(QLabel):
    """ Label with update handle """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dynamic_texts = []
        self.format = ''
        self.ureg = pint.UnitRegistry() # For V / mV / s / ms / ns etc. conversion
    
    def init(self, dynamic_texts:list[str], format:str):
        self.dynamic_texts = dynamic_texts
        self.format = format
        self.setText(self.format.format(*self.dynamic_texts))

    def update_text(self, index:int, new_text:str):
        """ Update one of the dynamic texts and refresh the label
        
        :param index: (int) index in dynamic_texts list to update
        :param new_text: (str) new text to set at the given index

        :return result: (str) updated formatted text
        """
        # replace the desired segment
        self.dynamic_texts[index] = new_text
        # reformat and update the QLabel
        self.setText(self.format.format(*self.dynamic_texts))
    
    def update_unit(self, new_val:str):
        """ Updates text, rounds to the largest possible
        unit without decimal points. 
        
        :param new_val: (str) 0.5 -> 500 m; 5e-5 -> 50u etc.
        """
        value = float(new_val)
        quantity = value * self.ureg.meter

        # Define the list of prefixes in ascending order
        prefixes = [
            ('f', 1e-15),
            ('p', 1e-12),
            ('n', 1e-9),
            ('u', 1e-6),
            ('m', 1e-3),
            ('', 1),
            ('k', 1e3),
            ('M', 1e6),
            ('G', 1e9),
            ('T', 1e12),
        ]

        # Find the appropriate prefix
        for prefix, factor in reversed(prefixes):
            if abs(value) >= factor:
                scaled_value = value / factor
                unit = f"{prefix}"
                break
        else:
            # If value is smaller than the smallest prefix
            scaled_value = value / 1e-15
            unit = 'f'

        # Format the display value
        displ_val = f"{scaled_value:.0f}"
        self.setText(self.format.format(displ_val, unit))
        # logger.debug(f'new val = {new_val}')
        # logger.debug(f'displ_val = {displ_val}')
        # logger.debug(f'unit = {unit}')


