# TODO

Dont Worry about appearance until ALL functionalities are finished. Appearance (tickmarks, etc. included) should be dealt last. Give 2 days for this.

PySide6 quick guides:

- [plotting](https://www.pythonguis.com/tutorials/pyside6-plotting-pyqtgraph/)
- [combobox](https://www.pythonguis.com/docs/qcombobox/)

1. Make slider stick to specific values, make textlabel follow those values
1. Make dummy math channels, show channel colors on legend. Channel 1 & 2 should always have the same colors as Keysight scope, math channels should have a fixed color sequence. 3 math channels at most.
1. Make sure user cannot drag / zoom graph.
1. Add measurement region below wave_pane, 4 measurements at most, absolutely NO scrolling. Click mouse midkey to delete measurement.
1. (optional) Make measurement cursor for (x,y) readout

## Feature specification

- Input gain selection (e.g. 500mVpp)
- Bode
- FFT
- 2 channels
- sine wave generator
- arbitrary waveform generator

>\+ (Add) - Adds Channel 1 and Channel 2 voltage values, point by point (CH1 + CH2)
>\- (Subtract) - Subtracts Channel 1 and Channel 2 voltage values, point by point (CH1 – CH2, CH2 – CH1)
>\* (Multiply) - Multiplies Channel 1 and Channel 2 voltage values, point by point (CH1 * CH2)
>/ (Divide) - Divides Channel 1 and Channel 2 voltage values, point by point (CH1 / CH2, CH2 / CH1). If zero divides by zero, the result will be 1. If either Channel 1 or Channel 2 is positive and it is divided by zero, the result will be in positive infinity. If either Channel 1 or Channel 2 is negative and it is divided by zero, the result will be in negative infinity.

## Work allocation

Eric: analogue circuit
Henry: signal processing, GUI

Unallocated: Arduino firmware, Tx/Rx