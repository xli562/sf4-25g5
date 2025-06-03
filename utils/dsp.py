from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QWidget
import numpy as np


class Channel(QObject):
    """ Represents a channel. Slightly optimised for speed. """

    frame_ready = Signal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = ''
        self.color = np.array([0, 0, 0, 0])
        self.line_width = 5
        self.is_active = True
        self.len = 10
        self.frame_buffer = np.array([np.zeros(self.len), np.zeros(self.len)])
        # frame buffer pointer points to the first free
        # location in frame_buffer[1] (buffer
        # fills from high index to low index)
        self.frame_buffer_ptr = self.len - 1   
        self.frame_ready.connect(lambda val: print(f'frame ready: {val}'))

    def __str__(self):
        retstr  = 'Channel:'
        retstr += f'{str(self.frame_buffer[0])}\n'
        retstr += f'{str(self.frame_buffer[1])}'
        return retstr

    def __len__(self):
        return self.len
    
    def rotate_frame_buf(self):
        self.frame_buffer[0] = self.frame_buffer[1]
        self.frame_buffer_ptr = self.len - 1
        self.frame_ready.emit(self.frame_buffer[0])

    def stream_in(self, new_data:np.ndarray[float]):
        """ Adds data to current frame, spills into next frame. 
        
        :param new_data: (np.ndarray[float]) list of new 
                data, newest values last
        """
        new_data = np.array(new_data)
        new_data_len = len(new_data)
        if new_data_len < self.frame_buffer_ptr + 1:
            self.frame_buffer[1] = np.concatenate([
                    np.zeros(self.frame_buffer_ptr - new_data_len + 1),
                    self.frame_buffer[1][self.frame_buffer_ptr + 1:],
                    new_data])
            self.frame_buffer_ptr -= new_data_len
        elif self.frame_buffer_ptr + 1 <= new_data_len < self.len + self.frame_buffer_ptr + 1:
            temp_ptr = self.frame_buffer_ptr
            self.frame_buffer[1] = np.concatenate([
                    self.frame_buffer[1][self.frame_buffer_ptr + 1:],
                    new_data[0:self.frame_buffer_ptr + 1]])
            self.rotate_frame_buf()
            self.frame_buffer[1] = np.concatenate([
                    np.zeros(self.len + temp_ptr + 1 - new_data_len),
                    new_data[temp_ptr + 1:]])
            self.frame_buffer_ptr = self.len-new_data_len + temp_ptr
        elif new_data_len >= self.len + self.frame_buffer_ptr + 1:
            # Frame buffer overflows, some data is lost
            self.frame_buffer[1] = new_data[-self.len:]
            self.rotate_frame_buf()
            self.frame_buffer[1] = np.zeros(self.len)
            self.frame_buffer_ptr = 0
