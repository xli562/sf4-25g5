from PySide6.QtWidgets import QPushButton, QSlider
from utils.xlogging import get_logger


logger = get_logger()

class MultButton(QPushButton):
    """ e.g. for Channel 1 / 2 selection """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.states = []
        self.state = {}
        self.clicked.connect(self.cycle_state)

    def set_states(self, states:list[dict]):
        """ Sets self.states
        
        states = {'index'     : (int),
                  'state_name': (str),
                  'stylesheet': (str),
                  'text'      : (str) }
        """
        self.states = states

    def set_state(self, index):
        """ Sets state of button.
         
        :param index: (int | str) index of state in
        self.states, or name of state as string.
        """
        if isinstance(index, int):
            self.state = self.states[index]
        elif isinstance(index, str):
            self.state = next(state for state in self.states if state['state_name'] == index)
        stylesheet = self.state['stylesheet']
        text = self.state['text']
        
        self.setStyleSheet(stylesheet)
        self.setText(text)

    def cycle_state(self):
        """ Cycles between different options """

        self.set_state((self.state['index'] + 1) % len(self.states))

class DiscreteSlider(QSlider):
    """ Slider that snaps to discrete values """

    def __init__(self, parent=None):
        """ Initialises the discrete slider. """
        # TODO: Set default value (read from stored default settings)
        super().__init__(parent)
        self.levels = []
        self.step = 0
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

        step = self.step
        snapped = round(val / step) * step
        if snapped != val:
            # block signals to avoid recursion
            self.blockSignals(True)
            self.setValue(snapped)
            self.blockSignals(False)

