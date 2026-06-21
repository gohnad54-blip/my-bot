# Telegram Bot — збір заявок

Telegram-бот для збору заявок з захистом паролем. Зберігає дані в CSV і надсилає сповіщення адміністратору.

## Можливості

- Захист паролем при першому `/start`
- Послідовний збір: ім'я → телефон → коментар
- Кнопка «Поділитись номером» або ручне введення
- Збереження заявок у `applications.csv`
- Сповіщення адміністратора про нові заявки
- Команда `/cancel` для скасування поточної заявки

## Структура проєкту

```
bot/
├── bot.py              # основний файл
├── .env                # конфігурація (не комітити!)
├── .env.example        # шаблон конфігурації
├── requirements.txt    # залежності
└── applications.csv    # створюється автоматично
```

## Локальний запуск

### 1. Створіть бота в Telegram

1. Відкрийте [@BotFather](https://t.me/BotFather)
2. Надішліть `/newbot` і дотримуйтесь інструкцій
3. Скопіюйте отриманий токен

### 2. Дізнайтесь свій Chat ID (для ADMIN_CHAT_ID)

1. Напишіть [@userinfobot](https://t.me/userinfobot) або [@getmyid_bot](https://t.me/getmyid_bot)
2. Скопіюйте ваш числовий ID

### 3. Налаштуйте середовище

```bash
cd bot
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Відредагуйте `.env`:

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_CHAT_ID=987654321
BOT_PASSWORD=your_secret_password
```

### 4. Запустіть бота

```bash
python bot.py
```

## Запуск на VPS (Ubuntu/Debian)

### 1. Підключення та підготовка

```bash
ssh user@your-vps-ip

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Завантаження проєкту

```bash
# Варіант A: через git
git clone <your-repo-url> my-bot
cd my-bot/bot

# Варіант B: через scp з локальної машини
# scp -r bot/ user@your-vps-ip:~/my-bot/
```

### 3. Віртуальне середовище та залежності

```bash
cd ~/my-bot/bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Конфігурація

```bash
cp .env.example .env
nano .env
```

Заповніть `BOT_TOKEN`, `ADMIN_CHAT_ID` та `BOT_PASSWORD`.

### 5. Тестовий запуск

```bash
python bot.py
```

Перевірте роботу бота в Telegram, потім зупиніть (`Ctrl+C`).

### 6. Автозапуск через systemd

Створіть сервіс:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вміст файлу (замініть `user` та шлях):

```ini
[Unit]
Description=Telegram Application Bot
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/my-bot/bot
Environment=PATH=/home/user/my-bot/bot/venv/bin
ExecStart=/home/user/my-bot/bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активуйте сервіс:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

Перегляд логів:

```bash
sudo journalctl -u telegram-bot -f
```

## Команди бота

| Команда   | Опис                              |
|-----------|-----------------------------------|
| `/start`  | Початок роботи / запит пароля     |
| `/cancel` | Скасування поточної заявки        |

## Формат CSV

Файл `applications.csv` містить колонки:

| datetime            | name   | phone        | comment        |
|---------------------|--------|--------------|----------------|
| 2026-06-21 14:30:00 | Іван   | +380501234567 | Потрібна консультація |

## Безпека

- Ніколи не комітьте `.env` у git
- Використовуйте надійний пароль у `BOT_PASSWORD`
- Обмежте доступ до VPS (SSH-ключі, firewall)
