from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QWidget
import numpy as np
from utils.xlogging import get_logger


logger = get_logger()

class Channel(QObject):
    """ Represents a channel. Slightly optimised for speed. """

    frame_ready = Signal(np.ndarray)
    RISE      = 'rise'
    FALL      = 'fall'
    RISE_FALL = 'risefall'
    NONE      = 'none'
    SINGLE    = 'single'

    def __init__(self, parent=None):
        """ N.B assumes even self.len """
        super().__init__(parent)
        self.name = ''
        self.color = np.array([0, 0, 0, 0])
        self.line_width = 5
        self.is_active = True
        self.trig_mode = self.NONE
        self.trig_threshold = 0.0
        self.pretrig = 0.5
        self._len = 500
        self.frame_buffer = np.zeros((2, self._len))
        # frame buffer pointer points to the earliest filled
        # location in frame_buffer[1] (buffer
        # fills from high index to low index)
        # buffer empty: self.frame_buffer_ptr = self.len
        # buffer full : self.frame_buffer_ptr = 0
        self.frame_buffer_ptr = self._len

    def __str__(self):
        retstr  = 'Channel:'
        retstr += f'{str(self.frame_buffer[0])}\n'
        retstr += f'{str(self.frame_buffer[1])}'
        return retstr

    def __len__(self):
        return self._len
    
    def set_length(self, new_len):
        self._len = new_len
        self.frame_buffer = np.array([np.zeros(self._len), np.zeros(self._len)])
        self.frame_buffer_ptr = self._len   
    
    def init_source(self, src:Signal):
        """ Connects serial input signal to channel """
        self.source = src
        self.source.connect(lambda val: self.stream_in(val))
    
    def rotate_frame_buf(self):
        self.frame_buffer[0] = self.frame_buffer[1]
        self.frame_buffer_ptr = self._len
        self.frame_ready.emit(self.frame_buffer[0])
        print('rotated')
    
    def last_crossing(self, data, threshold):
        """ Find index of the last crossing of threshold,
        that satisfies self.trig_mode
        For example, data = [-3,-1,0,1,2,3,1,2], threshold = 2.3 returns 4.
         
        :param data: (np.ndarray) the data sequence
        :param threshold: (float) the threshold
        
        :return idx: index of the last crossing, None 
                if not found or invalid self.trig_mode
        """
        data = np.array(data)
        if self.trig_mode == self.RISE:
            idcs = np.flatnonzero((data[:-1] <= threshold) & (data[1:] > threshold))
            return int(idcs[-1]) if idcs.size else None
        elif self.trig_mode == self.FALL:
            idcs = np.flatnonzero((data[:-1] > threshold) & (data[1:] <= threshold))
            int(idcs[-1]) if idcs.size else None
        elif self.trig_mode == self.RISE_FALL:
            idcs_rise = np.flatnonzero((data[:-1] <= threshold) & (data[1:] > threshold))
            idcs_fall = np.flatnonzero((data[:-1] > threshold) & (data[1:] <= threshold))
            is_found = bool(idcs_rise.size) or bool(idcs_fall.size)
            idx = np.max(idcs_rise[-1], idcs_fall[-1])
            return idx if is_found else None
        else:
            return None

    def stream_in(self, new_data:np.ndarray[float]):
        """ Adds data to current frame, spills into next frame.
        Does nothing if self.is_active == False.
                
        :param new_data: (np.ndarray[float]) list of new 
                data, newest values last
        """
        if self.is_active:
            new_data = np.array(new_data)
            new_data_len = len(new_data)

            if new_data_len < self.frame_buffer_ptr:
                # Not enough data to fill frame. Push stack, no need to check edge.
                self.frame_buffer[1] = np.concatenate([
                        np.zeros(self.frame_buffer_ptr - new_data_len),
                        self.frame_buffer[1][self.frame_buffer_ptr:],
                        new_data])
                self.frame_buffer_ptr -= new_data_len
            elif self.frame_buffer_ptr <= new_data_len < self._len + self.frame_buffer_ptr:
                if self.trig_mode == self.NONE:
                    # Push stack
                    temp_ptr = self.frame_buffer_ptr
                    self.frame_buffer[1] = np.concatenate([
                            self.frame_buffer[1][self.frame_buffer_ptr:],
                            new_data[0:self.frame_buffer_ptr]])
                    self.rotate_frame_buf()
                    self.frame_buffer[1] = np.concatenate([
                            np.zeros(self._len + temp_ptr - new_data_len),
                            new_data[temp_ptr:]])
                    self.frame_buffer_ptr = self._len - new_data_len + temp_ptr
                else:
                    full_data = np.concatenate([self.frame_buffer[1][self.frame_buffer_ptr:], new_data])
                    search_start = int(self._len * self.pretrig)
                    search_end   = new_data_len + search_start + 1  # +1 to include endpoint
                    edge_relative_idx = self.last_crossing(full_data[search_start:search_end], self.trig_threshold)
                    # logger.debug(full_data[search_start:search_end])
                    if edge_relative_idx is not None:
                        # Place newest edge at pretrig position
                        edge_absolute_idx = edge_relative_idx + search_start
                        fragment = full_data[edge_absolute_idx:edge_absolute_idx+self._len+1]
                        if len(fragment) >= self._len:
                            self.frame_buffer[1] = fragment[-self._len:]
                            self.rotate_frame_buf()
                        elif len(fragment) < self._len:
                            length_difference = self._len - len(fragment)
                            try:
                                self.frame_buffer[1] = np.concatenate([self.frame_buffer[1][-length_difference:], fragment])
                            except:
                                breakpoint()
                            self.rotate_frame_buf()
                    else:
                        # Fall back to trig_mode='none'
                        temp_ptr = self.frame_buffer_ptr
                        self.frame_buffer[1] = np.concatenate([
                                self.frame_buffer[1][self.frame_buffer_ptr:],
                                new_data[0:self.frame_buffer_ptr]])
                        self.rotate_frame_buf()
                        self.frame_buffer[1] = np.concatenate([
                                np.zeros(self._len + temp_ptr - new_data_len),
                                new_data[temp_ptr:]])
                        self.frame_buffer_ptr = self._len - new_data_len + temp_ptr
            elif new_data_len >= self._len + self.frame_buffer_ptr + 1:
                # Frame buffer overflows, some data is lost
                self.frame_buffer[1] = new_data[-self._len:]
                self.rotate_frame_buf()
                self.frame_buffer[1] = np.zeros(self._len)
                self.frame_buffer_ptr = self._len