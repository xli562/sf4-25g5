import sys, os
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout

from utils.window import BaseWidget, ControlPane, MainWindow, WaveCanvas

from utils.xlogging import get_logger, set_logging_level


logger = get_logger()
set_logging_level('DEBUG')

if __name__ == '__main__':
    # Use X11 forwarding on WSL
    os.environ['QT_QPA_PLATFORM'] = 'xcb'

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()

    window.arduino.stop()
    window.arduino.wait()
    sys.exit(exit_code)