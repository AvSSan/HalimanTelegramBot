import telebot
from telebot import types
import sqlite3
from datetime import datetime

API_TOKEN = '6558494391:AAFatYzSEY_jbxqjRRJzPo_TyTr1impAM0Y'
bot = telebot.TeleBot(API_TOKEN)

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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Добавить задачу"))
    keyboard.add(types.KeyboardButton("Задачи на сегодня"))
    keyboard.add(types.KeyboardButton("Все задачи"))
    keyboard.add(types.KeyboardButton("Отметить выполненное"))
    keyboard.add(types.KeyboardButton("Мои данные"))
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Добро пожаловать в ToDo бот!", reply_markup=main_menu())


@bot.message_handler(regexp="Добавить задачу")
def add_task(message):
    msg = bot.send_message(message.chat.id, "Введите задачу:")
    bot.register_next_step_handler(msg, save_task)


def save_task(message):
    task = message.text
    added_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO tasks (task, added_date, user_id) VALUES (?, ?, ?)", (task, added_date, message.chat.id))
    conn.commit()
    bot.send_message(message.chat.id, "Задача добавлена!", reply_markup=main_menu())


@bot.message_handler(regexp="Задачи на сегодня")
def today_tasks(message):
    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT id, task FROM tasks WHERE added_date=? AND completed=0 AND user_id=?", (today_date, message.chat.id))
    tasks = cursor.fetchall()

    if tasks:
        response = "Задачи на сегодня:\n"
        for task in tasks:
            response += f"{task[0]}. {task[1]}\n"
    else:
        response = "На сегодня нет задач."

    bot.send_message(message.chat.id, response, reply_markup=main_menu())


@bot.message_handler(regexp="Все задачи")
def all_tasks(message):
    cursor.execute("SELECT id, task, completed FROM tasks WHERE user_id=?", (message.chat.id,))
    tasks = cursor.fetchall()

    if tasks:
        response = "Все задачи:\n"
        for task in tasks:
            status = "✔" if task[2] else "❌"
            response += f" - {task[1]} [{status}]\n"
    else:
        response = "Нет задач."

    bot.send_message(message.chat.id, response, reply_markup=main_menu())


@bot.message_handler(regexp="Отметить выполненное")
def mark_completed(message):
    cursor.execute("SELECT id, task FROM tasks WHERE completed=0 AND user_id=?", (message.chat.id,))
    tasks = cursor.fetchall()

    if tasks:
        markup = types.InlineKeyboardMarkup()
        for task in tasks:
            markup.add(types.InlineKeyboardButton(text=task[1], callback_data=f"complete_{task[0]}"))
        bot.send_message(message.chat.id, "Выберите задачу для отметки:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Нет невыполненных задач.", reply_markup=main_menu())


@bot.callback_query_handler(func=lambda call: call.data.startswith("complete_"))
def complete_task(call):
    task_id = call.data.split("_")[1]
    cursor.execute("UPDATE tasks SET completed=1 WHERE id=? AND user_id=?", (task_id, call.message.chat.id))
    conn.commit()
    bot.answer_callback_query(call.id, "Задача отмечена как выполненная!")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)


@bot.message_handler(regexp="Мои данные")
def my_data(message):
    print(message.chat.id)
    bot.send_message(message.chat.id, f"{message.chat.id}")


bot.infinity_polling()
