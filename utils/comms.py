import random, serial, time, os, re
from PySide6.QtCore import QThread, Signal
import numpy as np
from utils.xlogging import get_logger


logger = get_logger()

class Arduino(QThread):
    """Simulate Arduino data: random chunk sizes at random intervals.

    Continuously generates random float arrays and feeds them into
    the provided Channel instance via stream_in().
    """
    BAUD_RATE = 250000 

    serial_data = Signal(np.ndarray)

    def __init__(self, parent=None):
        """Initialize with a Channel instance to stream data into.

        :param channel: (Channel) the Channel instance whose stream_in()
            method will be called with each random data chunk
        """
        super().__init__(parent)
        self.is_running = True

    def run(self):
        """Thread entry point: generate random chunks at random intervals."""
        self.connect_serial()
        self.generate_demo_data()
        # self.read_serial()

    def stop(self):
        """Stop the simulator thread on next loop iteration."""
        self.is_running = False

    def generate_demo_data(self):
        x = 0
        while self.is_running:
            # Sleep for a random interval between 5 and 50 ms
            interval = random.uniform(0.00005, 0.0005)
            time.sleep(interval)
            chunk_size = random.randint(1, 5)
            # data = [np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            # data = [0.1*t*np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            data = [np.sin(t) + np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            self.serial_data.emit(data)
            # logger.debug(data)
            x += chunk_size

    def connect_serial(self):
        """ Attempts to connect to the Arduino """

        # Scan `/dev` for USB devices
        pattern = re.compile(r'^(ttyACM\d+|ttyUSB\d+)$')
        ports = [f'/dev/{dev}' for dev in os.listdir('/dev') if pattern.match(dev)]
        if ports:
            logger.debug(f'Found {ports}')
        else:
            logger.debug('No USB devices found.')
            return

        for port in ports:
            try:
                logger.debug(f'Connecting to {port} with baud rate {self.BAUD_RATE}')
                with serial.Serial(port, self.BAUD_RATE, timeout=2) as ser:
                    logger.debug(f'Connected.')
                    self.port = port
                    break
            except serial.SerialException as e:
                logger.debug(f'Failed: {e}')


    def read_serial(self):
        """
        Main function to connect to the Arduino, read and unpack data,
        and print the results.
        """
        with serial.Serial(self.port, self.BAUD_RATE, timeout=2) as ser:
            ser.flushInput()
            while self.is_running:
                try:
                    if ser.in_waiting >= 5:
                        # Read one 5-byte packet
                        packed_data = ser.read(5)
                        samples = np.zeros(4)
                        # Reconstruct sample 0
                        samples[0] = (packed_data[0]) | ((packed_data[1] & 0b00000011) << 8)
                        # Reconstruct sample 1
                        samples[1] = ((packed_data[1] & 0b11111100) >> 2) | ((packed_data[2] & 0b00001111) << 6)
                        # Reconstruct sample 2
                        samples[2] = ((packed_data[2] & 0b11110000) >> 4) | ((packed_data[3] & 0b00111111) << 4)
                        # Reconstruct sample 3
                        samples[3] = ((packed_data[3] & 0b11000000) >> 6) | (packed_data[4] << 2)
                        # At this point, samples is a list of four 10-bit integer values.
                        # samples is the list of sample data
                        self.serial_data.emit(samples)
                except KeyboardInterrupt:
                    logger.debug('Keyboard interrupt')
                    break
                except Exception as e:
                    logger.debug(e)
                    break


