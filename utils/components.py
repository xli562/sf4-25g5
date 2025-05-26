from PySide6.QtWidgets import QPushButton

class MultButton(QPushButton):
    """ e.g. for Channel 1 / 2 selection """
    
    def __init__(self, parent=None):
        super().__init__(parent)
