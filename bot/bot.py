import csv
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "applications.csv"
CSV_HEADERS = ["datetime", "name", "phone", "comment"]

PASSWORD, NAME, PHONE, COMMENT = range(4)

authenticated_users: set[int] = set()
blocked_users: set[int] = set()

PHONE_PATTERN = re.compile(r"^\+?[\d\s\-()]{10,20}$")


def validate_config() -> None:
    missing = [
        name
        for name, value in [
            ("BOT_TOKEN", BOT_TOKEN),
            ("ADMIN_CHAT_ID", ADMIN_CHAT_ID),
            ("BOT_PASSWORD", BOT_PASSWORD),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def ensure_csv_exists() -> None:
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)
        logger.info("Created applications.csv")


def save_application(name: str, phone: str, comment: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, name, phone, comment])
    return timestamp


def normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-()]", "", phone.strip())


def is_valid_phone(phone: str) -> bool:
    if not PHONE_PATTERN.match(phone.strip()):
        return False
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


async def reject_blocked_user(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id in blocked_users:
        if update.message:
            await update.message.reply_text(
                "Доступ заборонено. Невірний пароль було введено раніше."
            )
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await reject_blocked_user(update):
        return ConversationHandler.END

    user_id = update.effective_user.id
    if user_id in authenticated_users:
        context.user_data.clear()
        await update.message.reply_text("Введіть ваше ім'я:")
        return NAME

    await update.message.reply_text(
        "Вітаємо! Для доступу до бота введіть пароль:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PASSWORD


async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    password = update.message.text.strip()

    if password != BOT_PASSWORD:
        blocked_users.add(user_id)
        logger.warning("User %s entered wrong password", user_id)
        await update.message.reply_text(
            "Невірний пароль. Доступ заборонено.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    authenticated_users.add(user_id)
    logger.info("User %s authenticated successfully", user_id)
    await update.message.reply_text("Пароль прийнято! Введіть ваше ім'я:")
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Ім'я занадто коротке. Введіть коректне ім'я:")
        return NAME

    context.user_data["name"] = name

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Поділитись номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Надішліть номер телефону кнопкою нижче або введіть його вручну:",
        reply_markup=keyboard,
    )
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith("+"):
            phone = f"+{phone}"
    else:
        phone = update.message.text.strip()

    if not is_valid_phone(phone):
        await update.message.reply_text(
            "Невірний формат номера. Введіть номер у форматі +380XXXXXXXXX "
            "або натисніть «Поділитись номером»:"
        )
        return PHONE

    context.user_data["phone"] = normalize_phone(phone)
    await update.message.reply_text(
        "Додайте коментар до заявки:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return COMMENT


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    comment = update.message.text.strip()
    if not comment:
        await update.message.reply_text("Коментар не може бути порожнім. Введіть коментар:")
        return COMMENT

    name = context.user_data["name"]
    phone = context.user_data["phone"]

    try:
        timestamp = save_application(name, phone, comment)
    except OSError as exc:
        logger.exception("Failed to save application: %s", exc)
        await update.message.reply_text(
            "Помилка збереження заявки. Спробуйте пізніше або зверніться до адміністратора."
        )
        return ConversationHandler.END

    await update.message.reply_text("Дякуємо! Ваша заявка прийнята ✅")

    admin_message = (
        "📋 Нова заявка\n\n"
        f"🕐 Дата/час: {timestamp}\n"
        f"👤 Ім'я: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"💬 Коментар: {comment}\n"
        f"🆔 User ID: {update.effective_user.id}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as exc:
        logger.exception("Failed to notify admin: %s", exc)

    context.user_data.clear()
    logger.info("Application saved for user %s", update.effective_user.id)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Заявку скасовано. Щоб почати знову, надішліть /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def handle_unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id in blocked_users:
        await update.message.reply_text(
            "Доступ заборонено. Невірний пароль було введено раніше."
        )
        return

    if update.effective_user.id not in authenticated_users:
        await update.message.reply_text(
            "Спочатку авторизуйтесь. Надішліть /start"
        )


def main() -> None:
    validate_config()
    ensure_csv_exists()

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            PHONE: [
                MessageHandler(filters.CONTACT, receive_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
            ],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unauthorized)
    )

    logger.info("Bot started in polling mode")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
