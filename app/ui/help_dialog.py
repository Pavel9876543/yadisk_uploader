from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser


class HelpDialog(QDialog):
    """
    Диалоговое окно со справкой по работе с приложением.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Справка")
        self.resize(680, 560)
        self.setObjectName("HelpDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Справка")
        title.setObjectName("HelpTitle")
        layout.addWidget(title)

        text = QTextBrowser()
        text.setObjectName("HelpText")
        text.setOpenExternalLinks(True)
        text.setHtml(self._get_help_text())
        layout.addWidget(text)

        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("PrimaryButton")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.setStyleSheet("""
            QDialog#HelpDialog {
                background: #111317;
            }

            QLabel#HelpTitle {
                color: #f7fafc;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 24px;
                font-weight: 800;
            }

            QTextBrowser#HelpText {
                background: #fbfcfe;
                color: #1f2937;
                border: 1px solid #dce2ea;
                border-radius: 8px;
                padding: 12px;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 14px;
                selection-background-color: #14b8a6;
            }

            QPushButton#PrimaryButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #14b8a6,
                    stop: 1 #2563eb
                );
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 14px;
                font-weight: 800;
                padding: 9px 14px;
            }

            QPushButton#PrimaryButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0d9488,
                    stop: 1 #1d4ed8
                );
            }
        """)

    def _get_help_text(self) -> str:
        return """
        <h3>Yandex Disk Uploader</h3>

<ol>
  <li>
    <b>Укажите токен Яндекс.Диска</b><br>
    Введите OAuth-токен Яндекс.Диска (в файл <code>.env</code> для переменной <code>YANDEX_TOKEN</code>)
    и сохраните его. Без корректного токена загрузка невозможна.
  </li>

  <li>
    <b>Настройте локальные пути</b><br>
    Для каждой категории файлов (исходные и обработанные фото/видео)
    укажите локальную папку с файлами. Путь можно выбрать через диалог
    или ввести вручную. После указания нажмите кнопку <i>Сохранить</i>.
    При следующем запуске они автоматически подставятся в поля.
  </li>

  <li>
    <b>Проверьте пути на Яндекс.Диске</b><br>
    Пути на Яндекс.Диске формируются автоматически при запуске приложения.
    Они включают:
    <ul>
      <li>базовый путь (например: <i>Медиатека/Богослужения</i>)</li>
      <li>текущий год</li>
      <li>текущую дату</li>
      <li>подпапки в зависимости от категории файлов</li>
    </ul>
    Вы видите итоговый путь и при необходимости можете отредактировать
    его вручную перед загрузкой.
  </li>

  <li>
    <b>Запуск загрузки</b><br>
    Нажмите кнопку <b>«Загрузить»</b> рядом с нужной категорией.
    Загрузка выполняется асинхронно и не блокирует интерфейс.
    Пока загрузка выполняется, отправка других папок недоступна:
    приложение загружает только одну папку за раз.
  </li>

  <li>
    <b>Прогресс загрузки</b><br>
    Прогресс-бар показывает обработку файлов в текущей задаче.
    В прогресс включаются:
    <ul>
      <li>загруженные файлы</li>
      <li>файлы, пропущенные из-за того, что они уже существуют на диске</li>
    </ul>
    Это гарантирует корректное достижение 100%.
  </li>

  <li>
    <b>Пропуск существующих файлов</b><br>
    Если файл с таким именем уже существует на Яндекс.Диске,
    он не загружается повторно и автоматически пропускается.
  </li>

  <li>
    <b>Сохранение путей</b><br>
    При нажатии <b>«Сохранить»</b>:
    <ul>
      <li>локальные пути сохраняются полностью</li>
      <li>для Яндекс.Диска сохраняется только базовый путь - первые две корневые папки
          (без года, даты и служебных подпапок)</li>
    </ul>
    Это предотвращает повторное наслаивание каталогов
    при следующем запуске приложения.
  </li>

  <li>
    <b>Ошибки и уведомления</b><br>
    Все ошибки отображаются в понятном виде.
    Технические детали логируются и не мешают работе пользователя.
  </li>

  <li>
    <b>Закрытие приложения</b><br>
    Если загрузка выполняется, при закрытии приложения
    будет предложено прервать процесс или дождаться его завершения.
  </li>
</ol>

<hr>

<p>
  <i>Совет:</i> перед началом загрузки убедитесь,
  что пути указаны корректно и доступны,
  а токен Яндекс.Диска действителен.
</p>
        """
