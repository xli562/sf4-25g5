import random, serial, time
from PySide6.QtCore import QThread, Signal
import numpy as np
from utils.xlogging import get_logger


logger = get_logger()

class Arduino(QThread):
    """Simulate Arduino data: random chunk sizes at random intervals.

    Continuously generates random float arrays and feeds them into
    the provided Channel instance via stream_in().
    """
    SERIAL_PORT = 'COM6' 
    BAUD_RATE = 250000 

    chn_1_demo_serial_input = Signal(np.ndarray)

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
            # data = [np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            # data = [0.1*t*np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            data = [np.sin(t) + np.sin(t/20) for t in np.arange(x, x + chunk_size)]
            self.chn_1_demo_serial_input.emit(data)
            # logger.debug(data)
            x += chunk_size

    def stop(self):
        """Stop the simulator thread on next loop iteration."""
        self._running = False

    def read_actual_arduino(self):
        """
        Main function to connect to the Arduino, read and unpack data,
        and print the results.
        """
        logger.debug(f"Attempting to connect to {self.SERIAL_PORT} at {self.BAUD_RATE} baud...")
        try:
            # The 'with' statement ensures the serial port is automatically closed
            # even if an error occurs.
            with serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=2) as ser:
                logger.debug(f"Successfully connected to {self.SERIAL_PORT}.")
                # Flush any old data in the input buffer
                ser.flushInput()
                while True:
                    try:
                        # Wait until we have 5 bytes in the buffer
                        if ser.in_waiting >= 5:
                            # Read one 5-byte packet
                            packed_data = ser.read(5)
                            samples = [0] * 4
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
                            print(f"Samples: {samples[0]:4d}, {samples[1]:4d}, {samples[2]:4d}, {samples[3]:4d}")
                    except KeyboardInterrupt:
                        logger.debug("\nProgram terminated by user.")
                        break
                    except Exception as e:
                        logger.debug(f"An error occurred: {e}")
                        break
                        
        except serial.SerialException as e:
            logger.debug(f"Error: Could not open serial port {self.SERIAL_PORT}. {e}")
            logger.debug("Please check the following:")
            logger.debug("1. Is the Arduino connected to the PC?")
            logger.debug("2. Is the correct SERIAL_PORT name specified in the script? (Check Device Manager)")
            logger.debug("3. Are you using the correct baud rate?")
            logger.debug("4. Do you have the necessary permissions to access the port?")
