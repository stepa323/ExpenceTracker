import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication
from MainWindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('MainWindow.ui', self)
        self.initUi()

    def initUi(self):
        ...


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
