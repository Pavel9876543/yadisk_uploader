import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
import sys
import traceback

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

def excepthook(exc_type, exc_value, exc_tb):
    print("❌ Необработанное исключение:")
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

if __name__ == "__main__":
    main()