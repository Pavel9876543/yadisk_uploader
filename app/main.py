import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow
from utils.logger import LOG_PATH, logger


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


def excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    message = str(exc_value).strip() or exc_type.__name__
    details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    logger.critical(
        "Необработанное исключение: %s",
        message,
        exc_info=(exc_type, exc_value, exc_tb),
    )

    app = QApplication.instance()
    if app is None:
        print("Необработанная ошибка:", file=sys.stderr)
        print(message, file=sys.stderr)
        print(details, file=sys.stderr)
        return

    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle("Критическая ошибка")
    box.setText("Произошла непредвиденная ошибка.")
    box.setInformativeText(
        f"{message}\n\n"
        f"Подробности записаны в лог:\n{LOG_PATH}"
    )
    box.setDetailedText(details)
    box.exec_()


sys.excepthook = excepthook

if __name__ == "__main__":
    main()
