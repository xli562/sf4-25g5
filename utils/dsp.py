from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QWidget
import numpy as np
from collections import deque
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
        self.pretrig = 0.3
        self._len = 500
        self.frame_buffer = np.zeros((2, self._len))
        # frame buffer pointer points to the earliest filled
        # location in frame_buffer[1] (buffer
        # fills from high index to low index)
        # buffer empty: self.frame_buffer_ptr = self.len
        # buffer full : self.frame_buffer_ptr = 0
        self.frame_buffer_ptr = self._len

        self._post_len   = self._len - int(self._len * self.pretrig)
        self._lookahead  = deque(maxlen=self._len + self._post_len)

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
    
    def set_pretrig(self, new_pretrig):
        self.pretrig = new_pretrig
        self._post_len   = self._len - int(self._len * self.pretrig)
        self._lookahead  = deque(maxlen=self._len + self._post_len)

    def set_threshold(self, new_threshold):
        self.trig_threshold = new_threshold
    
    def init_source(self, src:Signal):
        """ Connects serial input signal to channel """
        self.source = src
        self.source.connect(lambda val: self.stream_in(val))
    
    def _rotate(self):
        self.frame_buffer[0] = self.frame_buffer[1].copy()
        self.frame_buffer_ptr = self._len
        self.frame_ready.emit(self.frame_buffer[0])
        print('rotated')
    
    def _first_crossing(self, data:np.ndarray, thr:float):
        """ Find index of the last crossing of threshold,
        that satisfies self.trig_mode
        For example, data = [-3,-1,0,1,2,3,1,2], threshold = 2.3 returns 4.
         
        :param data: (np.ndarray) the data sequence
        :param threshold: (float) the threshold
        
        :return idx: index of the last crossing, None 
                if not found or invalid self.trig_mode
        """
        data = np.asarray(data, dtype=float)
        if data.size < 2:
            return None
        high = data > thr
        if self.trig_mode == self.RISE:
            idcs = np.flatnonzero(~high[:-1] &  high[1:])
        elif self.trig_mode == self.FALL:
            idcs = np.flatnonzero( high[:-1] & ~high[1:])
        elif self.trig_mode == self.RISE_FALL:
            idcs = np.flatnonzero(high[:-1] ^  high[1:])
        else:
            return None
        return int(idcs[0]) if idcs.size else None

    def stream_in(self, new_data:np.ndarray[float]):
        """ Adds data to current frame, spills into next frame.
        Does nothing if self.is_active == False.
                
        :param new_data: (np.ndarray[float]) list of new 
                data, newest values last
        """
        if not self.is_active:
            return

        # 1.  Append the fresh samples to the look-ahead queue
        self._lookahead.extend(np.asarray(new_data, dtype=float))

        # 2.  Not enough data yet?  Just wait for the next chunk
        if len(self._lookahead) < self._lookahead.maxlen:
            return

        # 3.  Build a contiguous array of exactly maxlen samples
        full = np.asarray(self._lookahead, dtype=float)   # length = 750
        s0   = int(self._len * self.pretrig)              # 250

        # 4.  Find the **first** edge that leaves room for the post-trigger tail
        idx_rel = None
        if self.trig_mode != self.NONE:
            cand = self._first_crossing(full[s0:], self.trig_threshold)
            if cand is not None:
                edge_abs = s0 + cand
                if edge_abs + self._post_len <= len(full):
                    idx_rel = cand                       # accept

        # 5.  If still no edge → free-run (never freezes)
        if idx_rel is None:
            fragment = full[-self._len:]                 # last 500 samples
            triggered = False
        else:
            start     = idx_rel                          # edge at x = s0
            fragment  = full[start:start + self._len]
            triggered = True

        # 6.  Ship the frame
        self.frame_buffer[0] = fragment                  # front buffer
        self.frame_ready.emit(fragment)
        print('frame ready', end='')

        # 7.  Keep the *last* (len + post_len) samples for next search
        #     (= drop exactly the len samples we just plotted)
        for _ in range(self._len):
            self._lookahead.popleft()
            