# Yandex Disk Uploader

PyQt5-приложение для загрузки одной выбранной папки на Яндекс.Диск.
Приложение не ставит задачи в очередь: пока идёт загрузка, отправка других папок заблокирована.

## Подготовка

```bash
cd /root/yadisk_uploader
cp .env.example .env
```

OAuth-токен можно ввести в окне приложения: поле `Токен Яндекс.Диска`,
кнопка `Сохранить токен`. Приложение сохранит его в `.env` как
`YANDEX_TOKEN`.

Также токен можно указать вручную:

```bash
YANDEX_TOKEN=your_token_here
```

## Запуск в текущем окружении

Окружение `.venv` уже создано. Запуск:

```bash
cd /root/yadisk_uploader
./run.sh
```

Если запускаете из `proot-distro` на Android, сначала поднимите Termux:X11 в обычном Termux:

```bash
termux-x11 :0
```

Затем внутри Ubuntu:

```bash
proot-distro login ubuntu
cd /root/yadisk_uploader
export DISPLAY=:0
./run.sh
```

## Установка окружения заново

Для Ubuntu:

```bash
apt update
apt install -y python3-pyqt5 python3-venv qtwayland5 libxcb-cursor0
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Проверка без графического окна

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python app/main.py
```

Такой запуск нужен только для проверки импорта и инициализации Qt: окно видно не будет.

## Логи

Логи пишутся в консоль и в файл:

```text
~/.local/state/yadisk_uploader/app.log
```

Компиляция для Windows:

```cmd
build_windows.bat
```

Скрипт собирает onedir-пакет PyInstaller с каталогом зависимостей
`_internal`, копирует `install_yadisk_uploader.bat` рядом с основным exe,
проверяет, что в корне `dist\YadiskUploader` остались только:

```text
YadiskUploader.exe
install_yadisk_uploader.bat
_internal\
```

Также создаются:

```text
dist\YadiskUploader.zip
dist\install_yadisk_uploader.bat
```

Их можно передать пользователю вместе. Пользователь запускает
`install_yadisk_uploader.bat`; скрипт через стандартные окна Windows
предложит место установки и имя папки, по умолчанию равное названию архива,
распакует/скопирует приложение и создаст ярлык на рабочем столе с названием
основного exe.

Ручная команда PyInstaller, если сборочный bat не используется:

```cmd
pyinstaller --clean --windowed --name YadiskUploader ^
  --contents-directory _internal ^
  --collect-submodules=yadisk ^
  --hidden-import=numpy ^
  --hidden-import=pygame ^
  --hidden-import=matplotlib ^
  --add-data "app/config/config.json;config" ^
  app/main.py
```

После ручной сборки нужно отдельно скопировать
`install_yadisk_uploader.bat` в `dist\YadiskUploader\` и, если нужен
архивный установщик, положить копию bat рядом с `YadiskUploader.zip`.
