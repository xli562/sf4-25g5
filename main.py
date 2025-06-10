import serial
import time
import threading

class SerialController:
    """
    A class to manage serial communication with the Arduino in a background thread.
    This is designed to be easily integrated into a GUI application.
    """
    def _init_(self, port, baud_rate):
        """
        Initializes the controller.
        Args:
            port (str): The serial port name (e.g., 'COM6' on Windows or '/dev/ttyACM0' on Linux).
            baud_rate (int): The baud rate, matching the Arduino sketch.
        """
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=1)
        except serial.SerialException as e:
            print(f"Error: Could not open port {port}. {e}")
            raise  # Re-raise the exception to be handled by the GUI

        self.stop_event = threading.Event()
        self.data_lock = threading.Lock()
        self.latest_samples = [0, 0, 0, 0]
        
        # The reader thread is created but not started here.
        self.reader_thread = threading.Thread(target=self._data_reader_loop)
        self.reader_thread.daemon = True

    def _data_reader_loop(self):
        """
        [Private] This method runs in the background thread, continuously
        reading from the serial port and updating the latest_samples variable.
        """
        print("[Controller] Data reader thread started.")
        while not self.stop_event.is_set():
            try:
                if self.ser.in_waiting >= 5:
                    packed_data = self.ser.read(5)
                    samples_buffer = [0] * 4
                    samples_buffer[0] = (packed_data[0]) | ((packed_data[1] & 0b00000011) << 8)
                    samples_buffer[1] = ((packed_data[1] & 0b11111100) >> 2) | ((packed_data[2] & 0b00001111) << 6)
                    samples_buffer[2] = ((packed_data[2] & 0b11110000) >> 4) | ((packed_data[3] & 0b00111111) << 4)
                    samples_buffer[3] = ((packed_data[3] & 0b11000000) >> 6) | (packed_data[4] << 2)
                    
                    with self.data_lock:
                        self.latest_samples = samples_buffer
                else:
                    time.sleep(0.001) # Prevent CPU hogging
            except (serial.SerialException, Exception):
                print("[Controller] Error in reader thread. Stopping.")
                self.stop_event.set()
                break
        print("[Controller] Data reader thread finished.")

    # --- Public Methods for the GUI to Use ---
    
    def start(self):
        """Starts the background data reading thread."""
        if not self.reader_thread.is_alive():
            self.reader_thread.start()

    def stop(self):
        """Stops the thread and safely closes the serial port."""
        print("[Controller] Stop signal received.")
        self.stop_event.set()
        if self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1)
        if self.ser.is_open:
            self.ser.close()
        print("[Controller] Serial port closed.")

    def get_latest_samples(self):
        """
        [GUI USE] Safely gets the most recent ADC samples for plotting.
        Returns:
            list: A list of four integer ADC values.
        """
        with self.data_lock:
            # Return a copy to prevent race conditions if the GUI modifies it
            return list(self.latest_samples)

    def send_command(self, command_list):
        """
        [GUI USE] Sends a command to the Arduino to change a mux channel.
        Args:
            command_list (list or tuple): A list containing the mux number 
                                          and channel number, e.g., [1, 4].
        """
        if not isinstance(command_list, (list, tuple)) or len(command_list) != 2:
            print(f"[Controller] Invalid command format. Expected a list/tuple of two ints, but got {command_list}")
            return
            
        mux_num, channel_num = command_list
        
        if self.ser.is_open:
            command_str = f"{mux_num} {channel_num}"
            self.ser.write(command_str.encode('ascii') + b'\n')
            print(f"[Controller] Sent command: '{command_str}'")



if _name_ == '_main_':
    # On Windows, the port is 'COMX'. Check Device Manager for the number.
    # On Linux, the port is typically '/dev/ttyACM0' or '/dev/ttyUSB0'
    SERIAL_PORT = 'COM6' 
    BAUD_RATE = 250000

    controller = None # Define controller in the outer scope for the finally block
    try:
        # 1. The GUI creates an instance of the controller
        controller = SerialController(SERIAL_PORT, BAUD_RATE)
        
        # 2. The GUI starts the controller's background process
        controller.start()

        # 3. The GUI connects its buttons to the controller's methods.
        #    This is a simulation of button clicks.
        print("\n--- Simulating GUI Interaction ---")
        time.sleep(2)
        print("Simulating a click on 'Set Mux 1 to Channel 4' button...")
        controller.send_command([1, 4])
        time.sleep(2)
        print("Simulating a click on 'Set Mux 2 to Channel 2' button...")
        controller.send_command([2, 2])
        time.sleep(2)
        
        # 4. The GUI uses a timer to periodically get data and update the plot.
        #    This loop simulates that timer.
        print("\n--- Simulating GUI plot update (running for 10s) ---")
        for i in range(200): # Run for 10 seconds (200 * 0.05s)
            samples = controller.get_latest_samples()
            print(f"Live samples: {samples}", end='\r')
            time.sleep(0.05) # Refresh rate of 20Hz

    except Exception as e:
        print(f"\nAn error occurred in the main application: {e}")
    finally:
        # 5. When the GUI window is closed, it calls the stop method.
        print("\n\n--- Test finished. Shutting down. ---")
        if controller:
            controller.stop()