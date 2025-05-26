import sys, os
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout

from utils.window import BaseWidget, ControlPane, MainWindow, WaveCanvas


if __name__ == '__main__':
    # Use X11 forwarding on WSL
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
