import serial
import time


SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 250000 

def main():
    """
    Main function to connect to the Arduino, read and unpack data,
    and print the results.
    """
    print(f"Attempting to connect to {SERIAL_PORT} at {BAUD_RATE} baud...")

    try:
        # The 'with' statement ensures the serial port is automatically closed
        # even if an error occurs.
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            print(f"Successfully connected to {SERIAL_PORT}.")
            
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
                    print("\nProgram terminated by user.")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break
                    
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {SERIAL_PORT}. {e}")
        print("Please check the following:")
        print("1. Is the Arduino connected to the PC?")
        print("2. Is the correct SERIAL_PORT name specified in the script? (Check Device Manager)")
        print("3. Are you using the correct baud rate?")
        print("4. Do you have the necessary permissions to access the port?")

if __name__ == '__main__':
    main()