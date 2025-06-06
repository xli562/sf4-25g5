import random
import time
from PySide6.QtCore import QThread, Signal
import numpy as np
from utils.xlogging import get_logger


logger = get_logger()

class Arduino(QThread):
    """Simulate Arduino data: random chunk sizes at random intervals.

    Continuously generates random float arrays and feeds them into
    the provided Channel instance via stream_in().
    """
    chn_1_serial_input = Signal(np.ndarray)

    def __init__(self, parent=None):
        """Initialize with a Channel instance to stream data into.

        :param channel: (Channel) the Channel instance whose stream_in()
            method will be called with each random data chunk
        """
        super().__init__(parent)
        self._running = True

    def run(self):
        """Thread entry point: generate random chunks at random intervals."""
        x = 0
        while self._running:
            # Sleep for a random interval between 5 and 50 ms
            interval = random.uniform(0.00005, 0.0005)
            time.sleep(interval)
            chunk_size = random.randint(1, 5)
            data = [np.sin(t/15) for t in np.arange(x, x + chunk_size)]
            self.chn_1_serial_input.emit(data)
            # logger.debug(data)
            x += chunk_size

    def stop(self):
        """Stop the simulator thread on next loop iteration."""
        self._running = False


# Example usage:
# channel = Channel()
# sim_thread = ArduinoSimulatorThread(channel)
# sim_thread.start()
# # ... later, to stop:
# # sim_thread.stop()
# # sim_thread.wait()
