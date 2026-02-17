from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout

class HelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Как пользоваться")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            "1. Укажите токен Яндекс.Диска и сохраните его\n"
            "2. Укажите локальные пути и пути на Яндекс.Диске\n"
            "3. При необходимости измените последнюю подпапку с датой\n"
            "4. Нажмите кнопку 'Загрузить' для нужной категории\n"
            "5. Дождитесь завершения загрузки\n"
        )
        layout = QVBoxLayout(self)
        layout.addWidget(text)
