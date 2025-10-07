import os
import json
import telebot
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# --- 🔧 Настройки: эти значения будут храниться в Railway Variables ---
# Ты НИЧЕГО не меняешь здесь в коде — просто создаешь такие переменные на Railway:
# BOT_TOKEN = токен твоего Telegram-бота
# SPREADSHEET_ID = ID твоего Google Sheets
# GOOGLE_CREDENTIALS_JSON = весь JSON из Google Cloud (в одну строку)
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

bot = telebot.TeleBot(BOT_TOKEN)

# --- 🔐 Авторизация в Google Sheets ---
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# --- 🧾 Функция записи в таблицу ---
def append_to_sheets(direction, chat_id, username, text):
    try:
        sheet.append_row([
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            direction,  # incoming / outgoing
            chat_id,
            username if username else "",
            text
        ])
    except Exception as e:
        print(f"Ошибка при записи в Google Sheets: {e}")

# --- 💬 Обработка всех сообщений ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    # 1️⃣ Сохраняем входящее сообщение
    append_to_sheets("incoming", message.chat.id, message.from_user.username, message.text)
    
    # 2️⃣ Отправляем ответ пользователю
    reply_text = "✅ Сообщение получено! Спасибо."
    bot.send_message(message.chat.id, reply_text)
    
    # 3️⃣ Сохраняем исходящее сообщение (ответ)
    append_to_sheets("outgoing", message.chat.id, None, reply_text)

# --- 🚀 Запуск бота ---
if __name__ == "__main__":
    print("Бот запущен и слушает сообщения...")
    bot.infinity_polling()
