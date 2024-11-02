import os, logging, asyncio, datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardRemove

# TODO: Make bot async

# INITIALIZING VARIABLES

load_dotenv()
bot = AsyncTeleBot(token=os.getenv('TOKEN'))
admins = os.getenv("ADMINS")
headman = int(os.getenv("HEADMAN"))
client = MongoClient("localhost", 27017)
db = client["student_hive_db"]
schedule_collection = db["schedules"]
day_weeks = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
user_states = {}
user_schedule = {}

# logging setup

logging.basicConfig(filename="logs.log", encoding="utf-8", level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# MARKUPS

def build_reply_buttons(admin_markup, labels):
    buttons = []
    for label in labels:
        button = types.KeyboardButton(label)
        buttons.append(button)
    admin_markup.add(*buttons)

def build_inline_buttons(admin_markup, labels):
    buttons = []
    for label in labels:
        button = types.InlineKeyboardButton(label, callback_data=label)
        buttons.append(button)
    admin_markup.add(*buttons)

back_keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
back_button = types.KeyboardButton("Повернутись")
back_keyboard.add(back_button)

main_menu_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
main_menu_labels = ["Розклад", "Відмітитись на парах", "Дедлайни", "Фідбек старості", "Адмін"]
build_reply_buttons(main_menu_markup, main_menu_labels)

main_schedule_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
main_schedule_labels = ["Сьогодні", "Тиждень", "Повернутись"]
build_reply_buttons(main_schedule_markup, main_schedule_labels)

admin_schedule_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_schedule_labels = ["Сьогодні", "Тиждень", "Повернутись", "Редагувати"]
build_reply_buttons(admin_schedule_markup, admin_schedule_labels)

admin_schedule_edit = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_schedule_edit_labels = day_weeks + ["Повернутись"]
build_reply_buttons(admin_schedule_edit, admin_schedule_edit_labels)

admin_schedule_day_edit = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_schedule_day_labels = ["Додати", "Редагувати", "Видалити", "Повернутись"]
build_reply_buttons(admin_schedule_day_edit, admin_schedule_day_labels)

main_mark_markup = types.InlineKeyboardMarkup(row_width=3)
main_mark_labels = ["1", "2", "3", "4", "5", "всіх", "Повернутись"]
build_inline_buttons(main_mark_markup, main_mark_labels)

main_deadline_markup = types.InlineKeyboardMarkup(row_width=1)
main_deadline_markup.add(back_button)

main_feedback_markup = types.InlineKeyboardMarkup(row_width=1)
main_feedback_markup.add(back_button)

# DB HANDLERS

def add_schedule_entry(day, number, type_l, time, subject, lecturer, link, note):
    entry = {
        "day": day,
        "number": number,
        "type": type_l,
        "time": time,
        "subject": subject,
        "lecturer": lecturer,
        "link": link,
        "note": note
    }
    schedule_collection.insert_one(entry)

async def get_schedule(day):
    entries = schedule_collection.find({"day": day})
    schedule_list = []
    for entry in entries:
        schedule_list.append(f"Дисципліна: {entry['subject']}\nТип: {entry['type']}\nВикладач: {entry['lecturer']}\nЧас: {entry['time']}\nПосилання: {entry['link']}\nПримітка: {entry['note']}")
    return "\n".join(schedule_list) if schedule_list else "Сьогодні немає пар."

async def get_week_schedule():
    result = "————————————————————"
    for day in day_weeks:
        schedule = schedule_collection.find({"day": day})
        result += f"\n\n{day}\n\n"

        has_entries = False
        for entry in schedule:
            has_entries = True
            result += f"Дисципліна: {entry['subject']}\nТип: {entry['type']}\nВикладач: {entry['lecturer']}\nЧас: {entry['time']}\nПосилання: {entry['link']}\nПримітка: {entry['note']}\n————————————————————\n"
        if not has_entries:
            result += "Пар немає.\n\n————————————————————\n"
    return result

# BOT HANDLERS

# Handle feedback and change user states

@bot.message_handler(content_types=["text"], func=lambda message: message.text == "Фідбек старості")
async def handle_feedback(message):
    await bot.send_message(message.chat.id, "Анонімний фідбек.\nВи можете надіслати фідбек старості, в повідомлені не будуть передані ваші особисті дані, також ці дані не доступні розробнику.\nУведіть текст повідомлення.", reply_markup=back_keyboard)
    user_states[message.chat.id] = "awaiting_feedback"


@bot.message_handler(content_types=['text'])
async def message_handler(message):
    global user_states
    # Default commands
    if message.chat.type == "private":
        # States checking
        # Feedback sending
        if user_states.get(message.chat.id) == "awaiting_feedback":
            if message.text == "Повернутись":
                await bot.send_message(message.chat.id, "Скасував відправку фідбеку.", reply_markup=main_menu_markup)
                user_states.pop(message.chat.id, None)
            else:
                feedback_message = f"*Анонімний фідбек:*\n\n{message.text}"
                await bot.send_message(headman, feedback_message, parse_mode="Markdown")
                await bot.send_message(message.chat.id, "Ваш фідбек надіслано, дякую!", reply_markup=main_menu_markup)
                user_states.pop(message.chat.id, None)
        elif message.text == "/start":
            await bot.send_message(message.chat.id, "Hello world!", reply_markup=main_menu_markup)
        elif message.text == "/help":
            pass
        elif message.text == "/admin_help":
            pass
        # Navigation
        elif message.text == "Повернутись":
            await bot.send_message(message.chat.id, "Надав головне меню.", reply_markup=main_menu_markup)
        elif message.text == "Розклад":
            if str(message.from_user.id) in admins:
                await bot.send_message(message.chat.id, "Оберіть режим", reply_markup=admin_schedule_markup)
            else:
                await bot.send_message(message.chat.id, "Оберіть режим", reply_markup=main_schedule_markup)
        elif message.text == "Сьогодні":
            today = datetime.datetime.now().strftime('%A')
            schedule = await get_schedule(today)
            await bot.send_message(message.chat.id, schedule)
        elif message.text == "Тиждень":
            schedule = await get_week_schedule()
            await bot.send_message(message.chat.id, schedule)
        elif message.text == "Редагувати":
            if str(message.from_user.id) in admins:
                await bot.send_message(message.chat.id, "Оберіть день.", reply_markup=admin_schedule_edit)
            else:
                await bot.send_message(message.chat.id, "Немає доступу.")
        elif message.text in day_weeks and str(message.from_user.id) in admins:
            user_states[message.chat.id] = "selecting_day"
            user_schedule[message.chat.id] = {"day": message.text}
            await bot.send_message(message.chat.id, "Оберіть дію.", reply_markup=admin_schedule_day_edit)


    elif message.chat.type == "supergroup" or message.chat.type == "group":
        # Group commands
        if message.text == "/sw":
            schedule = await get_week_schedule()
            await bot.send_message(message.chat.id, schedule)
        elif message.text == "/s":
            today = datetime.datetime.now().strftime('%A')
            schedule = await get_schedule(today)
            await bot.send_message(message.chat.id, schedule)
        elif message.text == "/clear_markup":
            await bot.send_message(message.chat.id, "Клавіатуру видалено!", reply_markup=ReplyKeyboardRemove())
        else:
            await bot.send_message(message.chat.id, "В групі працюють тільки команди:\n\n/s - розклад на сьогодні\n/sw - розклад на тиждень\n/clear_markup - видалити клавіатуру.")



# START BOT
async def main():
    await bot.polling(none_stop=True)


if __name__ == '__main__':
    asyncio.run(main())