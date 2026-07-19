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
