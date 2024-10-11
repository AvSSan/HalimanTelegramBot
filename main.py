import sqlite3
import requests
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

API_TOKEN = '6558494391:AAFatYzSEY_jbxqjRRJzPo_TyTr1impAM0Y'
WEATHER_API_KEY = "0f94b131398d98e61c71d797a44576a5"
url = f"https://api.weatherstack.com/current?access_key={WEATHER_API_KEY}"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

conn = sqlite3.connect('todo.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
              (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              task TEXT NOT NULL, 
              added_date TEXT NOT NULL, 
              completed INTEGER DEFAULT 0,
              user_id INTEGER NOT NULL)''')
conn.commit()

def main_menu():
    keyboard = [
        ["Добавить задачу", "Отметить выполненное"],
        ["Задачи на сегодня", "Все задачи"],
        ["Мои данные", "Погода"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

ADD_TASK, GET_WEATHER = range(2)

async def start(update, context):
    await update.message.reply_text("Добро пожаловать в ToDo бот!", reply_markup=main_menu())

async def add_task(update, context):
    await update.message.reply_text("Введите задачу:")
    return ADD_TASK

async def save_task(update, context):
    task = update.message.text
    added_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO tasks (task, added_date, user_id) VALUES (?, ?, ?)",
                   (task, added_date, update.message.chat_id))
    conn.commit()
    await update.message.reply_text("Задача добавлена!", reply_markup=main_menu())
    return ConversationHandler.END

async def today_tasks(update, context):
    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT id, task FROM tasks WHERE added_date=? AND completed=0 AND user_id=?",
                   (today_date, update.message.chat_id))
    tasks = cursor.fetchall()

    if tasks:
        response = "Задачи на сегодня:\n"
        for task in tasks:
            response += f" - {task[1]}\n"
    else:
        response = "На сегодня нет задач."

    await update.message.reply_text(response, reply_markup=main_menu())

async def all_tasks(update, context):
    cursor.execute("SELECT id, task, completed FROM tasks WHERE user_id=?", (update.message.chat_id,))
    tasks = cursor.fetchall()

    if tasks:
        response = "Все задачи:\n"
        for task in tasks:
            status = "✔" if task[2] else "❌"
            response += f" - {task[1]} [{status}]\n"
    else:
        response = "Нет задач."

    await update.message.reply_text(response, reply_markup=main_menu())

async def mark_completed(update, context):
    cursor.execute("SELECT id, task FROM tasks WHERE completed=0 AND user_id=?", (update.message.chat_id,))
    tasks = cursor.fetchall()

    if tasks:
        keyboard = [
            [InlineKeyboardButton(task[1], callback_data=f"complete_{task[0]}")] for task in tasks
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите задачу для отметки:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Нет невыполненных задач.", reply_markup=main_menu())

async def complete_task(update, context):
    query = update.callback_query
    task_id = query.data.split("_")[1]
    cursor.execute("UPDATE tasks SET completed=1 WHERE id=? AND user_id=?", (task_id, query.message.chat_id))
    conn.commit()
    await query.answer("Задача отмечена как выполненная!")
    await query.edit_message_reply_markup(reply_markup=None)

async def my_data(update, context):
    await update.message.reply_text(f"Ваш ID: {update.message.chat_id}")

async def weather(update, context):
    await update.message.reply_text("Введите название города (на английском):")
    return GET_WEATHER

async def get_weather(update, context):
    city = update.message.text
    querystring = {f"query": {city}}
    try:
        req = requests.get(url, params=querystring).json()
        answer = (f"Город: {req['request']['query']}\n"
                  f"Температура: {req['current']['temperature']} градусов\n"
                  f"Скорость ветра: {req['current']['wind_speed']} км/ч")
        await update.message.reply_text(answer, reply_markup=main_menu())
    except Exception:
        await update.message.reply_text("Город не найден или неправильное название.", reply_markup=main_menu())
    return ConversationHandler.END

def main():
    application = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("Добавить задачу"), add_task), MessageHandler(filters.Text("Погода"), weather)],
        states={
            ADD_TASK: [MessageHandler(filters.TEXT, save_task)],
            GET_WEATHER: [MessageHandler(filters.TEXT, get_weather)],
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))

    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.Text("Задачи на сегодня"), today_tasks))
    application.add_handler(MessageHandler(filters.Text("Все задачи"), all_tasks))
    application.add_handler(MessageHandler(filters.Text("Отметить выполненное"), mark_completed))
    application.add_handler(MessageHandler(filters.Text("Мои данные"), my_data))
    application.add_handler(MessageHandler(filters.Text("Погода"), weather))

    application.add_handler(CallbackQueryHandler(complete_task, pattern=r"^complete_"))

    application.run_polling()

if __name__ == "__main__":
    main()
