import os
import json
import time
import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 🔧 Настройки через Variables Railway ---
BOT_TOKEN = os.getenv("BOT_TOKEN")               # Твой токен бота
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")     # ID таблицы Google Sheets
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # JSON сервисного аккаунта
ADMIN_ID = int(os.getenv("ADMIN_ID"))            # Твой Telegram ID для админки

bot = telebot.TeleBot(BOT_TOKEN)

# --- 🔐 Google Sheets ---
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# --- 🧾 Логирование пользователей и сообщений ---
def log_user(chat_id, username, text):
    # если username пустой, подставляем chat_id
    if not username:
        username = f"user_{chat_id}"

    all_records = sheet.get_all_records()
    for i, row in enumerate(all_records, start=2):
        if str(row['chat_id']) == str(chat_id):
            sheet.update_cell(i, 3, text)  # last_message
            return
    # новый пользователь
    sheet.append_row([chat_id, username, text, "", False])

# --- 💬 Получение сообщений от всех пользователей ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.from_user.id == ADMIN_ID:
        handle_admin_message(message)
    else:
        log_user(message.chat.id, message.from_user.username, message.text)
        bot.send_message(ADMIN_ID, f"Новое сообщение от @{message.from_user.username or message.chat.id} ({message.chat.id}):\n{message.text}")

# --- 🟢 Админский функционал ---
active_chats = {}  # admin_id: выбранный chat_id

# Список пользователей кнопками
def send_user_list(admin_id):
    all_records = sheet.get_all_records()
    keyboard = types.InlineKeyboardMarkup()
    for row in all_records:
        # если username пустой, подставляем chat_id
        btn_text = row['username'] if row['username'] else f"user_{row['chat_id']}"
        btn = types.InlineKeyboardButton(text=btn_text, callback_data=f"user:{row['chat_id']}")
        keyboard.add(btn)
    bot.send_message(admin_id, "Выберите пользователя:", reply_markup=keyboard)

# Обработка кнопок выбора пользователя
@bot.callback_query_handler(func=lambda c: c.data.startswith("user:"))
def select_user(callback):
    chat_id = int(callback.data.split(":")[1])
    active_chats[callback.from_user.id] = chat_id
    bot.send_message(callback.from_user.id, f"Выбран пользователь {chat_id}. Теперь пишите сообщения.")

# --- 📤 Ответ админа выбранному пользователю ---
def handle_admin_message(message):
    if message.text.lower() == "/users":
        send_user_list(message.from_user.id)
        return
    chat_id = active_chats.get(message.from_user.id)
    if chat_id:
        bot.send_message(chat_id, message.text)
        bot.send_message(message.from_user.id, f"✅ Ответ отправлен пользователю {chat_id}")
        # логируем в Google Sheets
        all_records = sheet.get_all_records()
        for i, row in enumerate(all_records, start=2):
            if str(row['chat_id']) == str(chat_id):
                sheet.update_cell(i, 4, message.text)  # reply
                sheet.update_cell(i, 5, True)          # sent
    else:
        bot.send_message(message.from_user.id, "Сначала выберите пользователя командой /users")

# --- 🚀 Запуск бота ---
if __name__ == "__main__":
    print("Бот запущен...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Ошибка polling: {e}")
        time.sleep(1)
