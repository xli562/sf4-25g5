from PySide6.QtCore import Signal, SignalInstance, QObject
from PySide6.QtWidgets import QWidget
import numpy as np
from collections import deque
from utils.xlogging import get_logger


logger = get_logger()

class Channel(QObject):
    """ Represents a channel. Slightly optimised for speed. 
    
    There are three types of channels: simple (raw output), arithmetic and FFT.
    Simple channels are 'Channel 1' and 'Channel 2' (strict naming convention).
    """
    frame_ready = Signal(np.ndarray)
    RISE      = 'rise'
    FALL      = 'fall'
    RISE_FALL = 'risefall'
    NONE      = 'none'
    SINGLE    = 'single'
    HAMMING   = 'Hamming'
    HANN      = 'Hann'
    RECT      = 'Rect'
    VRMS      = 'Vrms'
    DBV       = 'dBV'

    def __init__(self, parent=None):
        """ N.B assumes even self.len """
        super().__init__(parent)
        self.name = ''
        self.color = np.array([0, 0, 0, 0]) # RGBA
        self.is_active = True
        self.trig_mode = self.NONE
        self.trig_threshold = 0.0
        self.pretrg = 0.3
        self._len = 10
        self._hoffset_percent = 0
        self.vscale = 1
        self._voffset_absolute = 0
        self.frame_buffer = np.zeros((2, self._len))
        # frame buffer pointer points to the earliest filled
        # location in frame_buffer[1] (buffer
        # fills from high index to low index)
        # buffer empty: self.frame_buffer_ptr = self.len
        # buffer full : self.frame_buffer_ptr = 0
        self._frame_buffer_ptr = self._len
        self._post_len   = self._len - int(self._len * self.pretrg)
        self._lookahead  = deque(maxlen=int(self._len*2 + self._post_len))
        # FFT-specific state
        self.is_fft          = False
        self.sampling_period = 1.0

    def __str__(self):
        retstr  = f'{self.name}:'
        retstr += f'{str(self.frame_buffer[0])}\n'
        retstr += f'{str(self.frame_buffer[1])}'
        return retstr

    def __len__(self):
        return self._len
    
    def title(self, length:int):
        """ Returns short, medium or full name of channel.
        Only works if self.name = 'Channel 1' or 'Channel 2'.
        
        :param length: (int) 0: short, 1: medium, 2: full
        :return: (str) e.g. Ch1, Chn. 1, Channel 1
        """
        retstr = ''
        if length == 0:
            retstr = f'Ch{self.name[-1]}'
        elif length == 1:
            retstr = f'Chn. {self.name[-1]}'
        elif length == 2:
            retstr = self.name
        else:
            logger.debug(f'Invalid length specified: {length}')
        return retstr

    def set_active(self, is_active:bool):
        self.is_active = is_active

    def set_length(self, new_len):
        self._len = new_len
        self.frame_buffer = np.zeros((2, self._len))
        self._frame_buffer_ptr = self._len
        self._post_len   = self._len - int(self._len * self.pretrg)
        self._lookahead  = deque(maxlen=int(self._len*2 + self._post_len))

    def set_hoffset(self, hoffset_percent):
        """ Sets horizontal offset (+/- 5%) """

        self._hoffset_percent = hoffset_percent / 100 * 5

    def set_vscale(self, new_vscale):
        """ Sets vertical axis scaling factor """

        self.vscale = new_vscale

    def set_voffset(self, voffset_absolute):
        """ Sets vertical offset by absolute value """

        self._voffset_absolute = voffset_absolute

    def set_trig_mode(self, new_trig_mode_idx:int):
        """ Set trig mode to corresponding QPushButton in
        ctrl_pane.trig_btngrp with id == new_trig_mode_idx """

        options = (self.SINGLE, self.NONE, self.RISE, 
                   self.FALL, self.RISE_FALL)
        self.trig_mode = options[new_trig_mode_idx]

    def set_pretrg(self, new_pretrg):
        self.pretrg = new_pretrg
        self._post_len   = self._len - int(self._len * self.pretrg)
        self._lookahead  = deque(maxlen=int(self._len*2 + self._post_len))

    def set_trig_threshold_percentage(self, new_threshold_percentage):
        # TODO: new_threshold_percentage should be percentage of channel's
        # current range (volts / div), not a fixed value.
        self.trig_threshold = 5 * new_threshold_percentage

    def set_sampling_period(self, new_t_s: float) -> None:
        """Set ADC sampling interval in seconds (constant for all channels)."""
        if new_t_s <= 0:
            logger.debug(f'Sampling period must be > 0, got {new_t_s}')
        self.sampling_period = new_t_s

    def init_source(self, src:SignalInstance):
        """ Connects serial input signal to channel """
        self.source = src
        self.source.connect(lambda val: self.stream_in(val))
    
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

    def init_fft(
        self,
        vscale: str        = VRMS,     # 'Vrms' or 'dBV'
        window: str       = HANN,       # 'Hamming' | 'Hann' | 'Rect'
        span:   int       = 1_000,          # Hz
        center: int       = 0,              # Hz
        fft_size: int     = 2048      # power-of-two is fastest
    ) -> None:
        """
        Switch the channel into FFT mode and configure its parameters.
        After calling this the channel will emit magnitude spectra
        (1-D float array) on every `_fft_size` fresh samples.
        """
        # -------- basic validation ----------
        if vscale not in (self.VRMS, self.DBV):
            raise ValueError('scale must be "Vrms" or "dBV"')
        if window not in (self.HANN, self.HAMMING, self.RECT):
            raise ValueError('window must be Hann/Hamming/Rect')
        if fft_size < 128 or fft_size & (fft_size - 1):
            raise ValueError('fft_size must be a power of two ≥ 128')
        if span <= 0:
            raise ValueError('span must be > 0 Hz')

        # -------- save config ---------------
        self.is_fft   = True
        self._fft_size   = fft_size
        self._fft_span   = float(span)
        self._fft_center = float(center)
        self.fft_vscale = vscale
        self._fft_buf    = deque(maxlen=self._fft_size)   # reset buffer

        # -------- pre-compute helpers -------
        self._bins = np.fft.rfftfreq(self._fft_size, d=self.sampling_period)       # Hz
        self.fft_window  = self._make_window(self._fft_size, window)   # 1-D

        # determine indices for the requested span/center
        half = self._fft_span / 2.0
        lo   = self._fft_center - half
        hi   = self._fft_center + half
        self._idx_span = np.where((self._bins >= lo) & (self._bins <= hi))[0]

        if not self._idx_span.size:
            raise ValueError('Requested span/center outside FFT range')
        self._len = len(self._idx_span)                   # new logical length
        self.frame_buffer = np.zeros((2, self._len))      # keep same shape

    @staticmethod
    def _make_window(N: int, kind: str) -> np.ndarray:
        """ helper to build the window table once """

        if kind == Channel.RECT:
            return np.ones(N)
        if kind == Channel.HANN:
            return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / (N - 1))
        if kind == Channel.HAMMING:
            return 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(N) / (N - 1))
        raise ValueError('Unknown window type')

    def set_fft_window(self, new_window:str):
        self.fft_window  = self._make_window(self._fft_size, new_window)

    def get_fft_freq_range(self) -> tuple[float, float]:
        """ Return (f_min, f_max) in Hz of the current FFT frame. """

        if not self.is_fft:
            raise RuntimeError('Channel is not in FFT mode')
        return (float(self._bins[self._idx_span[0]]),
                float(self._bins[self._idx_span[-1]]))

    def stream_in(self, new_data:np.ndarray[float]):
        if not self.is_active:
            return
        if self.is_fft:
            self._stream_in_fft(new_data)
        else:
            self._stream_in_time(new_data)

    def _stream_in_time(self, new_data:np.ndarray[float]):
        """ Adds data to current frame, spills into next frame.
        Does nothing if self.is_active == False.
                
        :param new_data: (np.ndarray[float]) list of new 
                data, newest values last
        """
        # 1.  Append the fresh samples to the look-ahead queue
        self._lookahead.extend(np.asarray(new_data, dtype=float))

        # 2.  Not enough data yet?  Just wait for the next chunk
        if len(self._lookahead) < self._lookahead.maxlen:
            return

        # 3.  Build a contiguous array of exactly maxlen samples
        full = np.asarray(self._lookahead, dtype=float)   # length = 750
        s0   = int(self._len * self.pretrg)              # 250

        # 4.  Find the **first** edge that leaves room for the post-trigger tail
        idx_rel = None
        if self.trig_mode != self.NONE:
            cand = self._first_crossing(full[s0:], self.trig_threshold)
            if cand is not None:
                edge_abs = s0 + cand
                if edge_abs + self._post_len <= len(full):
                    idx_rel = cand                       # accept

        offset = -int(self._hoffset_percent * self._len / 100)
        if idx_rel is None:
            # If still no edge found, run with no trigger
            # No offset allowed with no trigger
            base_start_idx = len(full) - self._len
            start_idx = base_start_idx
        else:
            # Triggered
            base_start_idx = idx_rel
            start_idx = base_start_idx + offset

        end_idx = start_idx + self._len

        if 0 <= start_idx and end_idx <= len(full):
            fragment = full[start_idx:end_idx]                 # last 500 samples
        else:
            fragment = np.zeros(self._len, dtype=full.dtype)
            src_lo = max(start_idx, 0)
            src_hi = min(end_idx, len(full))
            overlap = src_hi - src_lo
            if overlap > 0:                                # only if data exists
                dst_lo = max(0, -start_idx)
                fragment[dst_lo:dst_lo + overlap] = full[src_lo:src_hi]
        
        # apply scaling and offset element-wise
        fragment = fragment * self.vscale + self._voffset_absolute
        # 6.  Ship the frame
        self.frame_buffer[0] = fragment                  # front buffer
        self.frame_ready.emit(fragment)

        # 7.  Keep the *last* (len + post_len) samples for next search
        #     (= drop exactly the len samples we just plotted)
        for _ in range(self._len):
            self._lookahead.popleft()

    def _stream_in_fft(self, new_data: np.ndarray) -> None:
        """
        Collect raw samples until we have `_fft_size`, then emit an FFT frame.
        """
        self._fft_buf.extend(np.asarray(new_data, dtype=float))
        if len(self._fft_buf) < self._fft_size:
            return                                    # not enough yet

        # ----- build block & drop it from the deque ------------------------
        block = np.asarray(self._fft_buf, dtype=float)   # copy
        self._fft_buf.clear()                            # start fresh

        # ----- apply window & FFT -----------------------------------------
        block_win = block * self.fft_window
        spec = np.abs(np.fft.rfft(block_win)) / (self._fft_size / 2)

        # scale to Vrms or dBV
        if self.fft_vscale == self.VRMS:
            y = spec / np.sqrt(2.0)
        else:  # dBV
            y = 20.0 * np.log10(np.maximum(spec / np.sqrt(2.0), 1e-20))

        # limit to requested span
        frame = y[self._idx_span]

        # ----- hand frame to GUI ------------------------------------------
        self.frame_buffer[0] = frame
        self.frame_ready.emit(frame)

class Measurement(QObject):
    """ Represents a measurement of a channel """

    MAX = 'Max'
    MIN = 'Min'
    FREQ = 'freq'
    RMS = 'RMS'
    meas_ready = Signal(float)

    def __init__(self, parent=None):
        super().__init__()

    def __str__(self):
        retstr = f'self.source.title(0)\n'
        retstr += f'{self.type} = {self.val} {self.units}'
        return retstr
    
    def __repr__(self):
        retstr = f'Measurement {self.type} of {self.src.name}, value = {self.val}'
        return retstr
    
    def init(self, chn:Channel, type:str, units:str=''):
        self.src = chn
        self.type = type
        self.val = 0.0
        self.units = units
        self.src.frame_ready.connect(
            lambda val: self.update(val))
    
    def update(self, data:np.ndarray):
        """ Updates self.value. """

        if self.type == self.MAX:
            self.val = np.max(data)
        elif self.type == self.MIN:
            self.val = np.min(data)
        elif self.type == self.RMS:
            self.val = round(float(np.sqrt(np.mean(data**2))), 4)
        self.meas_ready.emit(self.val)