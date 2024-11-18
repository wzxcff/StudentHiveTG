import os, logging, asyncio, datetime
import platform
import subprocess
import psutil, time
import uuid

from datetime import timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardRemove

# logging setup

logging.basicConfig(filename="logs.log", encoding="utf-8", level=logging.INFO, format="[%(asctime)s][%(name)s]: %(levelname)s - %(message)s", datefmt="%d.%m, %H:%M:%S")

# INITIALIZING VARIABLES
logging.info("Starting bot")

load_dotenv()
bot = AsyncTeleBot(token=os.getenv('TOKEN'))
admins = os.getenv("ADMINS")
devs = str(os.getenv("DEVS")).replace("[", "").replace("]", "").split(", ")
headman = int(os.getenv("HEADMAN"))
group = str(os.getenv("GROUP")).replace("[", "").replace("]", "").split(", ")
group_names = str(os.getenv("GROUP_NAMES")).replace("[", "").replace("]", "").split(", ")
unique = str(os.getenv("UNIQUE")).replace("[", "").replace("]", "").split(", ")
lecturers = str(os.getenv("LECTURERS")).replace("[", "").replace("]", "").split(", ") + ["Повернутись"]

# DB
client = MongoClient("localhost", 27017)
db = client["student_hive_db"]
schedule_collection = db["schedules"]
deadline_collection = db["deadlines"]
group_collection = db["group"]
pending_join_collection = db["pending_joins"]
blacklist_requests = db["blacklist_requests"]
user_settings = db["user_settings"]
deadlines_collection = db["deadlines"]
attendance_collection = db["attendance"]
notification_collection = db["notifications"]

day_weeks = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
user_states = {}
user_schedule = {}
user_deadlines = {}
links_arr = str(os.getenv("LINKS")).replace("[", "").replace("]", "").split(", ")

# if os.path.exists("group.json"):
#     with open("group.json", "r", encoding="utf-8") as f:
#         group_ids = json.load(f)
#         logging.info("Found group json")
# else:
#     logging.info("group json not found, trying to create")
#     try:
#         group_dict = dict(zip(group, group_names))
#         with open("group.json", "w", encoding="UTF-8") as f:
#             json.dump(group_dict, f, indent=6)
#             logging.info("Created group json successfully")
#             group_ids = group_dict
#     except Exception as e:
#         logging.warning(e)

# MARKUPS


async def append_group_json():
    pass


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

main_menu_markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
main_menu_labels = ["Розклад", "Відмітитись на парах", "Дедлайни", "Фідбек старості", "Повідомити про проблему", "Конфідеційність та підтримка"]
build_reply_buttons(main_menu_markup, main_menu_labels)

main_menu_admin = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
main_menu_admin_labels = main_menu_labels[:-1] + ["Оповістки"] + main_menu_labels[-1:]
build_reply_buttons(main_menu_admin, main_menu_admin_labels)

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
admin_schedule_day_labels = ["Додати", "Редагувати", "Видалити пару", "Видалити все", "Повернутись"]
build_reply_buttons(admin_schedule_day_edit, admin_schedule_day_labels)

admin_schedule_numbers = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
admin_schedule_numbers_labels = ["1", "2", "3", "4", "5", "6", "Повернутись"]
build_reply_buttons(admin_schedule_numbers, admin_schedule_numbers_labels)

admin_schedule_time = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
admin_schedule_time_labels = ["10:10 – 11:30", "12:00 – 13:20", "13:40 – 15:00", "15:20 – 16:40", "17:00 – 18:20", "Повернутись"]
build_reply_buttons(admin_schedule_time, admin_schedule_time_labels)

admin_schedule_subjects = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
admin_schedule_subjects_labels = ["Алгоритмізація та програмування", "Вища математика", "Дискретна математика", "Університетські студії та вступ до компʼютерних наук", "Іноземна мова", "Історія України: Цивілізаційний вимір", "Кураторська Година", "Повернутись", " "]
build_reply_buttons(admin_schedule_subjects, admin_schedule_subjects_labels)

subjects_for_links = ["Алгоритмізація Струков", "Алгоритмізація Саділо", "Вища", "Дискретна", "Вступ до фаху лекція", "Вступ до фаху практика", "Іноземна", "Історія лекція", "Історія семінар", "Кураторська"]
links = dict(zip(subjects_for_links, links_arr))

admin_schedule_type = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
admin_schedule_type_labels = ["Лекція", "Практика", "Лабораторна", "Контрольна", "Повернутись", "Екзамен"]
build_reply_buttons(admin_schedule_type, admin_schedule_type_labels)

admin_schedule_links = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
true_links = [link for link in list(links.keys()) if links.get(link) != "-"]
build_reply_buttons(admin_schedule_links, true_links)

admin_schedule_lecturer = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
build_reply_buttons(admin_schedule_lecturer, lecturers)

admin_confirmation = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_confirmation_labels = ["Так, вірно", "Ні, скинути"]
build_reply_buttons(admin_confirmation, admin_confirmation_labels)

admin_schedule_delete = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_schedule_delete_labels = ["Видалити одну пару", "Видалити розклад на день"]
build_reply_buttons(admin_schedule_delete, admin_schedule_delete_labels)

main_mark_markup = types.InlineKeyboardMarkup(row_width=3)
main_mark_labels = ["1", "2", "3", "4", "5", "всіх", "Повернутись"]
build_inline_buttons(main_mark_markup, main_mark_labels)

admin_deadlines_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
admin_deadlines_labels = ["Додати", "Видалити", "Повернутись"]
build_inline_buttons(admin_deadlines_markup, admin_deadlines_labels)

main_deadline_markup = types.InlineKeyboardMarkup(row_width=1)
main_deadline_markup.add(back_button)

main_feedback_markup = types.InlineKeyboardMarkup(row_width=1)
main_feedback_markup.add(back_button)

guest_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=False)
guest_markup.add(types.KeyboardButton("Надіслати запит"))

admin_notif_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=False)
admin_notif_labels = ["Зробити оповістку", "Минулі оповістки", "Очистити оповістки", "Повернутись"]
build_reply_buttons(admin_notif_markup, admin_notif_labels)

delete_notifs_confirmation = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
delete_notifs_labels = ["Так", "Ні"]
build_reply_buttons(delete_notifs_confirmation, delete_notifs_labels)

logging.info("Built buttons")
# DB HANDLERS


async def schedule_entry(data_dict: dict):
    day, mode, number, time, subject, type_l, lecturer, link, number_edit = list(data_dict.values())
    entry = {
        "day": day,
        "number": number,
        "type": type_l,
        "time": time,
        "subject": subject,
        "lecturer": lecturer,
        "link": link,
    }
    current_entries = list(schedule_collection.find({"day": day}))
    if mode == "add":
        current_entries.append(entry)
        sorted_entries = sorted(current_entries, key=lambda x: x["number"])
        schedule_collection.delete_many({"day": day})
        schedule_collection.insert_many(sorted_entries)
    elif mode == "edit":
        for i, current_entry in enumerate(current_entries):
            if current_entry["number"] == number_edit:
                current_entries[i] = entry
                break
        sorted_entries = sorted(current_entries, key=lambda x: x["number"])
        schedule_collection.delete_many({"day": day})
        if sorted_entries:
            schedule_collection.insert_many(sorted_entries)
    elif mode == "delete":
        for i, current_entry in enumerate(current_entries):
            if current_entry["number"] == number_edit:
                current_entries.pop(i)
                break
        sorted_entries = sorted(current_entries, key=lambda x: x["number"])
        schedule_collection.delete_many({"day": day})
        if sorted_entries:
            schedule_collection.insert_many(sorted_entries)


async def get_schedule(day):
    entries = schedule_collection.find({"day": day})
    schedule_list = []
    for entry in entries:
        schedule_list.append(f"<b>Пара {entry['number']}:</b>\n<b>Дисципліна:</b> {entry['subject']}\n<b>Тип:</b> {entry['type']}\n<b>Викладач:</b> {entry['lecturer']}\n<b>Час:</b> {entry['time']}\n<b>Посилання:</b> {entry['link']}\n")
    return "\n".join(schedule_list) if schedule_list else f"Сьогодні немає пар. ({day})"


async def show_lessons_for_attendance(message):
    day = datetime.datetime.now().strftime("%d.%m")
    day_to_find = datetime.datetime.now().strftime("%A")
    lessons = list(schedule_collection.find({"day": day_to_find}))

    if not lessons:
        await bot.send_message(message.chat.id, "Сьогодні немає пар.")
        if str(message.from_user.id) not in admins:
            return
    markup = types.InlineKeyboardMarkup()
    for lesson in lessons:
        lesson_number = lesson["number"]
        subject = lesson["subject"]
        button = types.InlineKeyboardButton(f"Пара {lesson_number}: {subject}", callback_data=f"mark_{day}_{lesson_number}")
        markup.add(button)
    markup.add(types.InlineKeyboardButton("Скасувати відмітки", callback_data=f"mark_{day}_clear"))
    if str(message.from_user.id) in admins:
        markup.add(types.InlineKeyboardButton("Подивитись відмічених", callback_data=f"view_marked"))
    await bot.send_message(message.chat.id, await get_schedule(day_to_find) + f"\n\n<b>Поставте відмітку на яких парах плануєте бути.</b>", reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)


async def view_attendance(message, day):
    day_to_find = datetime.datetime.strptime(day + f".{datetime.datetime.now().year}", "%d.%m.%Y").strftime("%A")
    lesson_attendance = attendance_collection.find({"day": day}).sort("lesson", 1)

    response = f"Відвідуваність за <b>{day}</b>.\n\n"
    lessons_dict = {}

    for record in lesson_attendance:
        lesson = record["lesson"]
        attendees = record["attendees"]
        subject = record.get("subject", "Невідома дисципліна")

        lesson_info = schedule_collection.find_one({"day": day_to_find, "number": str(lesson)})

        if lesson not in lessons_dict:
            lessons_dict[lesson] = {
                "subject": subject,
                "attendees": []
            }

        for user in attendees:
            if user is None:
                logging.warning("Found None user_id in attendees.")
                continue
            lessons_dict[lesson]["attendees"].append(user)

    # Construct the response message
    for lesson, info in lessons_dict.items():
        response += f"\nПара {lesson} – {info['subject']}:\n"
        for user in info["attendees"]:
            if user is None:
                continue
            try:
                response += f" – {user[1]} {user[2] or ''} (@{user[0] or ''})\n"
            except Exception as e:
                response += f" – Error occurred, can't find info about user. See logs for details."
                logging.warning(f"Failed to get user info for {user}: {e}")

    if response == f"Відвідуваність за <b>{day}</b>.\n\n":
        response += "Відміток немає"

    markup = types.InlineKeyboardMarkup()
    for i in range(7, 0, -1):
        delta_day = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%d.%m")
        markup.add(types.InlineKeyboardButton(delta_day, callback_data=f"history_{delta_day}"))
    markup.add(types.InlineKeyboardButton(datetime.datetime.now().strftime("%d.%m"), callback_data=f"history_{datetime.datetime.now().strftime("%d.%m")}"))

    await bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="HTML")


async def get_week_schedule():
    day_schedules = []  # List to store each day's schedule as a separate message

    for day in day_weeks:
        schedule = schedule_collection.find({"day": day})
        day_message = f"———————————————————\n\n{day}\n\n"

        has_entries = False
        for entry in schedule:
            has_entries = True
            day_message += (f"<b>Пара {entry['number']}:</b>\n"
                            f"<b>Дисципліна:</b> {entry['subject']}\n"
                            f"<b>Тип:</b> {entry['type']}\n"
                            f"<b>Викладач:</b> {entry['lecturer']}\n"
                            f"<b>Час:</b> {entry['time']}\n"
                            f"<b>Посилання:</b> {entry['link']}\n\n")
        if not has_entries:
            day_message += "Пар немає.\n\n"

        day_message += "———————————————————"
        day_schedules.append(day_message)  # Add the day's message to the list

    return day_schedules


async def replace_actual_username(message):
    user_id = message.from_user.id
    username_now = message.from_user.username
    user_db_profile = group_collection.find_one({"_id": str(user_id)})
    logging.info(f"Checking user {user_db_profile.get('username')} username!")
    if user_db_profile:
        if user_db_profile.get("username") != username_now:
            group_collection.update_one({"_id": str(user_id)}, {"$set": {"username": username_now}})
            logging.info(f"Changed old username ({user_db_profile.get('username')}) to {username_now})")
    else:
        logging.warning("When trying to change actual username, error occurred")


async def get_server_status():
    uptime = subprocess.check_output("uptime -p", shell=True).decode().strip()

    cpu_usage = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()
    memory_usage = memory.percent

    disk = psutil.disk_usage('/')
    disk_usage = disk.percent

    os_info = platform.system() + " " + platform.release()
    status_message = (
        f"Server Status:\n"
        f"OS: {os_info}\n"
        f"Uptime: {uptime}\n"
        f"CPU Usage: {cpu_usage}%\n"
        f"Memory Usage: {memory_usage}%\n"
        f"Disk Usage: {disk_usage}%\n"
    )
    return status_message


async def clear_old_attendance():
    today = datetime.datetime.now()
    clear_date = (today - datetime.timedelta(days=9)).strftime("%d.%m")

    attendance_collection.delete_many({"day": clear_date})
    logging.info("Cleared old attendances!")


async def send_daily_notifications():
    while True:
        now = datetime.datetime.now()
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        logging.info(f"Sleeping for {wait_seconds} seconds until 9 AM.")

        await asyncio.sleep(wait_seconds)

        past_deadlines = deadlines_collection.find({"date": {"$lt": now}})
        past_deadline_titles = [deadline["title"] for deadline in past_deadlines]

        if past_deadline_titles:
            deadlines_collection.delete_many({"title": {"$in": past_deadline_titles}})
            logging.info(f"Deleted past deadlines: {past_deadline_titles}")

        users = [user["_id"] for user in group_collection.find()]
        next_day = (now + timedelta(days=1)).strftime("%d.%m")

        deadlines_next_day = list(deadlines_collection.find().sort("date", 1))

        if deadlines_next_day:
            for user_id in users:
                try:
                    if user_settings.find_one({"_id": str(user_id), "deadline_reminder": True}):
                        if str(user_id) in unique:
                            message = f"Доброго ранку, мій солоденький. Нагадую тобі щодо дедлайнів на завтра <3.\n\n<b>{next_day}</b>\n\n"
                        else:
                            message = f"Доброго ранку, нагадую щодо дедлайнів на завтра.\n\n<b>{next_day}</b>\n\n"
                        for deadline in deadlines_next_day:
                            if deadline["date"].strftime("%d.%m") == next_day:
                                message += f"{deadline["date"].strftime("%H.%M")} – {deadline['title']}\n"
                        await bot.send_message(int(user_id), message, parse_mode="HTML")
                    else:
                        logging.info(f"User {user_id} has turned off deadline reminders.")
                except Exception as e:
                    logging.warning(f"Failed to send message to {user_id}: {e}")
            logging.info("Reminders about deadlines were sent successfully!")
        else:
            logging.info("No deadlines found for the next day, skipping reminders.")
        await clear_old_attendance()

        await asyncio.sleep(86400)


async def make_group_notification(message):
    notification_id = str(uuid.uuid4())

    notification_entry = {
        "_id": notification_id,
        "message": message.text,
        "timestamp": datetime.datetime.now(),
        "reactions": {}
    }
    notification_collection.insert_one(notification_entry)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅", callback_data=f"notif_yes_{notification_id}"), types.InlineKeyboardButton("❌", callback_data=f"notif_no_{notification_id}"))

    users = group_collection.find()
    logging.info("Started group notification")
    for user in users:
        try:
            await bot.send_message(int(user["_id"]), f"Оповістка:\n\n{message.text}", reply_markup=markup)
            logging.info(f"Successfully sent notification to {user["_id"]}, {user["username"]}")
        except Exception as e:
            logging.warning(f"Failed to send message to {user["_id"]}, {user["username"]}: {e}")


async def view_notifications(message):
    found = False
    notifs = notification_collection.find()
    group_data = group_collection.find()
    user_id_to_username = {str(user["_id"]): user["username"] for user in group_data}
    for notif in notifs:
        reactions = notif.get("reactions", {})
        usernames_yes = []
        usernames_no = []

        for user_id, reaction in reactions.items():
            if reaction == "yes" and user_id in user_id_to_username:
                usernames_yes.append(f"@{user_id_to_username[user_id]}")
            elif reaction == "no" and user_id in user_id_to_username:
                usernames_no.append(f"@{user_id_to_username[user_id]}")

        formatted_message = (
            f"<b>ID:</b> {notif['_id']}\n"
            f"<b>Дата та час:</b> {notif['timestamp'].strftime('%d.%m %H:%M:%S')}\n\n"
            f"<b>Повідомлення:</b>\n{notif['message']}\n\n"
            f"<b>Реакції ✅:</b> {', '.join(usernames_yes) if usernames_yes else 'Немає'}\n"
            f"<b>Реакції ❌:</b> {', '.join(usernames_no) if usernames_no else 'Немає'}"
        )
        found = True
        await bot.send_message(message.chat.id, formatted_message, parse_mode="HTML")
    if not found:
        await bot.send_message(message.chat.id, "Історії оповісток не існує, зробіть оповістку щоб тут щось зʼявилось")


# BOT HANDLERS

# Using different handlers for feedback, because we don't need to log it.


# Not being logged
@bot.message_handler(content_types=["text"], func=lambda message: message.text == "Фідбек старості")
async def handle_feedback(message):
    await bot.send_message(message.chat.id, "Анонімний фідбек.\nВи можете надіслати фідбек старості, в повідомлені не будуть передані ваші особисті дані, також ці дані не доступні розробнику.\nУведіть текст повідомлення.", reply_markup=back_keyboard)
    user_states[message.chat.id] = "awaiting_feedback"


# Not being logged
@bot.message_handler(content_types=["text"], func=lambda message:user_states.get(message.chat.id) == "awaiting_feedback")
async def send_feedback(message):
    if user_states.get(message.chat.id) == "awaiting_feedback":
        if message.text == "Повернутись":
            if str(message.from_user.id) in admins:
                await bot.send_message(message.chat.id, "Скасував відправку фідбеку.", reply_markup=main_menu_admin)
            else:
                await bot.send_message(message.chat.id, "Скасував відправку фідбеку.", reply_markup=main_menu_markup)
            user_states.pop(message.chat.id, None)
        else:
            feedback_message = f"<b>Анонімний фідбек:</b>\n\n{message.text}"
            await bot.send_message(headman, feedback_message, parse_mode="HTML")
            if str(message.from_user.id) in admins:
                await bot.send_message(message.chat.id, "Ваш фідбек надіслано, дякую!", reply_markup=main_menu_admin)
            else:
                await bot.send_message(message.chat.id, "Ваш фідбек надіслано, дякую!", reply_markup=main_menu_markup)
            user_states.pop(message.chat.id, None)


# Main message handler which being logged
@bot.message_handler(content_types=['text'])
async def message_handler(message):
    global user_states
    if group_collection.find_one({"_id": str(message.from_user.id)}):
        # Chat type checking
        if message.chat.type == "private":
            # States checking
            user_state = user_states.get(message.chat.id)
            if user_state == "selecting_day":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                elif message.text in admin_schedule_day_labels:
                    if message.text == "Додати":
                        user_states[message.chat.id] = "selecting_number"
                        user_schedule[message.chat.id]["mode"] = "add"
                        await bot.send_message(message.chat.id, "Оберіть номер пари.", reply_markup=admin_schedule_numbers)
                    elif message.text == "Редагувати":
                        user_states[message.chat.id] = "selecting_number"
                        user_schedule[message.chat.id]["mode"] = "edit"
                        await bot.send_message(message.chat.id, "Оберіть номер пари (яку ви хочете додати).", reply_markup=admin_schedule_numbers)
                    elif message.text == "Видалити пару":
                        user_states[message.chat.id] = "selecting_to_delete"
                        user_schedule[message.chat.id]["mode"] = "delete"
                        await bot.send_message(message.chat.id, "Оберіть пару для видалення.", reply_markup=admin_schedule_numbers)
                    elif message.text == "Видалити все":
                        schedule_collection.delete_many({"day": user_schedule[message.chat.id]["day"]})
                        user_states.pop(message.chat.id, None)
                        user_schedule.pop(message.chat.id, None)
                        await bot.send_message(message.chat.id, "Розклад на день було видалено!", reply_markup=admin_schedule_edit)
            elif user_state == "selecting_to_delete":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    keys = ["number", "time", "subject", "type", "lecturer", "link"]
                    for key in keys:
                        user_schedule[message.chat.id][key] = None
                    user_schedule[message.chat.id]["number_edit"] = message.text
                    await schedule_entry(user_schedule[message.chat.id])
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                    await bot.send_message(message.chat.id, "Розклад змінено!", reply_markup=main_menu_admin)
            elif user_state == "selecting_number":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "selecting_time"
                    user_schedule[message.chat.id]["number"] = message.text
                    await bot.send_message(message.chat.id, "Оберіть час.", reply_markup=admin_schedule_time)
            elif user_state == "selecting_time":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "selecting_subject"
                    user_schedule[message.chat.id]["time"] = message.text
                    await bot.send_message(message.chat.id, "Оберіть дисципліну.", reply_markup=admin_schedule_subjects)
            elif user_state == "selecting_subject":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "selecting_type"
                    user_schedule[message.chat.id]["subject"] = message.text
                    await bot.send_message(message.chat.id, "Оберіть тип пари.", reply_markup=admin_schedule_type)
            elif user_state == "selecting_type":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "selecting_lecturer"
                    user_schedule[message.chat.id]["type"] = message.text
                    await bot.send_message(message.chat.id, "Оберіть викладача.", reply_markup=admin_schedule_lecturer)
            elif user_state == "selecting_lecturer":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "selecting_link"
                    user_schedule[message.chat.id]["lecturer"] = message.text
                    await bot.send_message(message.chat.id, "Оберіть посилання зі збережених, або надішліть своє.", reply_markup=admin_schedule_links)
            elif user_state == "selecting_link":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    if message.text in links.keys():
                        user_schedule[message.chat.id]["link"] = links[message.text]
                    else:
                        user_schedule[message.chat.id]["link"] = message.text
                    if user_schedule[message.chat.id]["mode"] == "edit":
                        user_states[message.chat.id] = "selecting_number_to_edit"
                        await bot.send_message(message.chat.id, "Оберіть пару яку ви редагували (замість якої буде ця пара).", reply_markup=admin_schedule_numbers)
                    else:
                        user_schedule[message.chat.id]["number_edit"] = None
                        user_states[message.chat.id] = "confirmation"
                        await bot.send_message(message.chat.id,f"<b>Перевірте інформацію</b>\n\nДень тижня: {user_schedule[message.chat.id]['day']}\nДисципліна: {user_schedule[message.chat.id]['subject']}\nТип: {user_schedule[message.chat.id]['type']}\nВикладач: {user_schedule[message.chat.id]['lecturer']}\nЧас: {user_schedule[message.chat.id]['time']}\nПосилання: {user_schedule[message.chat.id]['link']}\n\nЦе вірно?", parse_mode="HTML", reply_markup=admin_confirmation, disable_web_page_preview=True)
            elif user_state == "selecting_number_to_edit":
                if message.text == "Повернутись":
                    await bot.send_message(message.chat.id, "Скасував зміну розкладу.", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                else:
                    user_states[message.chat.id] = "confirmation"
                    user_schedule[message.chat.id]["number_edit"] = message.text
                    await bot.send_message(message.chat.id, f"<b>Перевірте інформацію</b>\n\nДень тижня: {user_schedule[message.chat.id]['day']}\nДисципліна: {user_schedule[message.chat.id]['subject']}\nТип: {user_schedule[message.chat.id]['type']}\nВикладач: {user_schedule[message.chat.id]['lecturer']}\nЧас: {user_schedule[message.chat.id]['time']}\nПосилання: {user_schedule[message.chat.id]['link']}\n\nЦе вірно?", parse_mode="HTML", reply_markup=admin_confirmation, disable_web_page_preview=True)
            elif user_state == "confirmation":
                if message.text == "Так, вірно":
                    await schedule_entry(user_schedule[message.chat.id])
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                    await bot.send_message(message.chat.id, "Зміни збережено!", reply_markup=main_menu_admin)
                elif message.text == "Ні, скинути":
                    user_states.pop(message.chat.id, None)
                    user_schedule.pop(message.chat.id, None)
                    await bot.send_message(message.chat.id, "Зміни скинуто!", reply_markup=main_menu_admin)
            # Default commands
            elif message.text == "/start":
                welcome_message = f"👋 Привіт, <b>{message.from_user.first_name}</b>!\n Мене було створено спеціально для групи <b>КС-11</b>, щоб допомагати вам зі всіма організаційними питаннями.\n\n 💼 Я можу показати розклад пар, допомогти вам відмітитися на парах і навіть нагадати про важливі події та дедлайни.\n\n ❓ Якщо вам потрібна допомога або ви хочете дізнатися про мої можливості, просто натисніть -> <b>/help</b>.\n\n 📢 Для останніх оновлень, статусу бота та багфіксів підписуйтесь на наш канал: [оновлення бота](https://t.me/+oh-WlmlOuyI4ODEy).\n\n Залишайтеся продуктивними та успіхів у навчанні! 🎓"
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu_admin, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    await bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu_markup, parse_mode="HTML", disable_web_page_preview=True)
            elif message.text == "/help":
                help_message = ("<b>Розклад</b> — можливість ознайомитись з розкладом на сьогодні або на тиждень.\n\n"
                                "<b>Відмітитись на парах</b> — відмічайтеся на яких парах плануєте бути, це значно полегшить життя старості.\n\n"
                                "<b>Дедлайни</b> — подивитись найближчі дедлайни, але не переймайтеся, я нагадаю Вам про дедлайн за день до дати.\n\n"
                                "<b>Фідбек старості</b> — надішліть анонімний фідбек старості, це може бути будь що. Це працює <b>ПОВНІСТЮ</b> анонімно, навіть розробник не зможе побачити хто відправив повідомлення.\n\n"
                                "<b>Повідомити про проблему</b> — звʼязок з розробником щодо багів в боті.\n\n"
                                "/settings – тут можна включити нагадування щодо дедлайнів.\n\n"
                                "\nДопомога адміністраторам -> /admin_help")
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, help_message, reply_markup=main_menu_admin, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    await bot.send_message(message.chat.id, "Немає доступу.", reply_markup=main_menu_markup, parse_mode="HTML", disable_web_page_preview=True)
            elif message.text == "/admin_help" or message.text == "/adminhelp":
                if str(message.from_user.id) in admins:
                    admin_help_message = ("Адміністратори можуть трішки більше ніж звичайний користувач.\n\n\n"
                                          "1. <b>Розклад</b> -> Редагувати\n"
                                          "1.1 Обираєте день для редагування.\n"
                                          "1.2 Обираєте дію:\nДодати — додати пару.\nРедагувати — редагувати якусь окрему пару.\nВидалити пару — видалити якусь окрему пару.\nВидалити все — видалити всі пари на цей день.\n"
                                          "Надалі слідкуєте за інструкціями бота :)\n\n"
                                          "2. <b>Відмітитись на парах</b> -> Подивитись відмічених\n"
                                          "2.1 Це надасть вам історію відміток за сьогодні, та можливість побачити історію відміток за останній тиждень.\n\n"
                                          "3. <b>Дедлайни</b> -> Додати\n"
                                          "3.1 Вкажіть заголовок дедлайну (текст дедлайну), можете вказати будь що.\n"
                                          "3.2 Вкажіть дату дедлайну у спецільному форматі, важливо щоб дата відповідала зазначеному формату.\n"
                                          "3.3 За день до дедлайну, о 9 годині ранку, я надішлю нагадування всім користовучам які не відключили сповіщення в налаштуваннях (/settings)\n\n"
                                          "4. <b>Оповістки</b>\n"
                                          "4.1 Ну тут думаю все зрозуміло, робіть оповістки для всіх користувачів боту та дивіться історію реакцій.")
                    await bot.send_message(message.chat.id, admin_help_message, reply_markup=main_menu_admin, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    await bot.send_message(message.chat.id, "Нажаль, у вас немає доступу.", reply_markup=main_menu_markup)
            elif message.text == "/settings":
                user_config = user_settings.find_one({"_id": str(message.from_user.id)})
                if not user_config:
                    user_settings.insert_one({"_id": str(message.from_user.id), "deadline_reminder": False})
                    await bot.send_message(message.chat.id,"Ваш ID не було знайдено, тому я створив вам новий профіль налаштувань.\nТут Ви можете вимкнути нагадування про дедлайни, та я не буду надсилати вам повідомлення зранку.")
                user_config = user_settings.find_one({"_id": str(message.from_user.id)})
                deadline_reminder_value = user_config["deadline_reminder"]
                deadline_reminder_status = "Вимкнено" if not deadline_reminder_value else "Увімкнено"
                message_text = f"<b>Ваші налаштування:</b>\n\nНагадування про дедлайни: {deadline_reminder_status}"

                markup = types.InlineKeyboardMarkup()
                toggle_deadline_reminder_btn = types.InlineKeyboardButton("Перемкнути нагадування про дедлайни", callback_data="toggle_deadline_reminder")
                markup.add(toggle_deadline_reminder_btn)

                await bot.send_message(message.chat.id, message_text, reply_markup=markup, parse_mode="HTML")
            elif message.text == "/keyboard":
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, "Надаю клавіатуру.", reply_markup=main_menu_admin)
                else:
                    await bot.send_message(message.chat.id, "Надаю клавіатуру.", reply_markup=main_menu_markup)
            elif message.text == "/log" and str(message.from_user.id) in devs:
                try:
                    with open("logs.log", encoding="UTF-8") as f:
                        await bot.send_document(message.chat.id, f, caption=f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
                except FileNotFoundError:
                    await bot.send_message(message.chat.id, "Не знайшов .log файлу!")
            elif message.text == "/clear_log" and str(message.from_user.id) in devs:
                try:
                    open("logs.log", "w").close()
                    await bot.send_message(message.chat.id, "Логи видалено.")
                except FileNotFoundError:
                    await bot.send_message(message.chat.id, "Не вдалося видалити файл, його не існує.")
            elif message.text == "/system_status" and str(message.from_user.id) in devs:
                await bot.send_message(message.chat.id, await get_server_status())
            # Navigation
            elif message.text == "Конфідеційність та підтримка":
                privacy_and_support_message = "<b>Щодо використання ваших даних</b>\n\nРозробник ніяк не може отримати доступ до вашого акаунту, паролів або особистих повідомлень. Бот зберігає лише ваш <b>ID, юзернейм, ім’я та прізвище</b> для забезпечення коректної роботи сервісу в межах університетської групи.\n\nВаші дані залишаються конфіденційними та використовуються виключно для покращення взаємодії з ботом. Жодна інформація не передається третім сторонам або використовується для інших цілей.\n\nЯкщо у вас є питання стосовно збереження даних або ви хочете видалити вашу інформацію, будь ласка, звертайтеся до мене напряму — <b>@wzxcff</b>. Я завжди на зв'язку і готовий допомогти.\n\n\n<b>Дякую за вашу фінансову підтримку цього бота!</b> Ваша допомога надзвичайно важлива для мене і дозволяє продовжувати покращувати сервіс. \n\nhttps://send.monobank.ua/jar/7yZdwvmNRf"
                await bot.send_message(message.chat.id, privacy_and_support_message, disable_web_page_preview=True, parse_mode="HTML")
            elif message.text == "Повернутись":
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, "Надав головне меню.", reply_markup=main_menu_admin)
                else:
                    await bot.send_message(message.chat.id, "Надав головне меню.", reply_markup=main_menu_markup)
            elif message.text == "Розклад":
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, "Оберіть режим", reply_markup=admin_schedule_markup)
                else:
                    await bot.send_message(message.chat.id, "Оберіть режим", reply_markup=main_schedule_markup)
                await replace_actual_username(message)
            elif message.text == "Сьогодні":
                today = datetime.datetime.now().strftime('%A')
                schedule = await get_schedule(today)
                await bot.send_message(message.chat.id, schedule, parse_mode="HTML", disable_web_page_preview=True)
            elif message.text == "Тиждень":
                schedule = await get_week_schedule()
                for el in schedule:
                    await bot.send_message(message.chat.id, el, parse_mode="HTML", disable_web_page_preview=True)
            elif message.text == "Редагувати":
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, "Оберіть день.", reply_markup=admin_schedule_edit)
                else:
                    await bot.send_message(message.chat.id, "Немає доступу.")
            elif message.text in day_weeks and str(message.from_user.id) in admins:
                user_states[message.chat.id] = "selecting_day"
                user_schedule[message.chat.id] = {"day": message.text}
                await bot.send_message(message.chat.id, "Оберіть дію.", reply_markup=admin_schedule_day_edit)
            elif message.text == "Дедлайни":
                sorted_entries = list(deadlines_collection.find().sort("date", 1))
                if sorted_entries:
                    result = "<b>Найближчі дедлайни:</b>\n\n"
                    current_date = None

                    for entry in sorted_entries:
                        entry_date = entry["date"].strftime("%d.%m")
                        entry_time = entry["date"].strftime("%H:%M")

                        if current_date != entry_date:
                            result += f"\n<b>{entry_date}</b>\n"
                            current_date = entry_date

                        result += f"{entry_time} – {entry['title']}\n"
                else:
                    result = "Дедлайнів немає."
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, result, parse_mode="HTML", reply_markup=admin_deadlines_markup)
                else:
                    await bot.send_message(message.chat.id, result, parse_mode="HTML")
            elif message.text == "Відмітитись на парах":
                if str(message.from_user.id) in admins:
                    await show_lessons_for_attendance(message)
                else:
                    await show_lessons_for_attendance(message)
                await replace_actual_username(message)
            elif message.text == "Додати" and str(message.from_user.id) in admins:
                user_states[message.chat.id] = "adding_deadline"
                await bot.send_message(message.chat.id, "Надішліть мені заголовок дедлайну.")
            elif message.text == "Оповістки" and str(message.from_user.id) in admins:
                await bot.send_message(message.chat.id, "Меню оповісток.", reply_markup=admin_notif_markup)
            elif message.text == "Зробити оповістку" and str(message.from_user.id) in admins:
                user_states[message.chat.id] = "making_notif"
                await bot.send_message(message.chat.id, "Чекаю на текст оповістки:", reply_markup=back_keyboard)
            elif message.text == "Очистити оповістки" and str(message.from_user.id) in admins:
                user_states[message.chat.id] = "notifs_deletion_confirm"
                await bot.send_message(message.chat.id, "Ви впевнені що хочете очистити історію оповісток? Ця дія видалить їх назавжди", reply_markup=delete_notifs_confirmation)
            elif message.text == "Минулі оповістки" and str(message.from_user.id) in admins:
                await view_notifications(message)
            elif message.text == "Повідомити про проблему":
                user_states[message.chat.id] = "sending_bug"
                await bot.send_message(message.chat.id, "Знайшли проблему або щось працює не так, як заплановано?\n\nОсь форма повідомлення:", reply_markup=back_keyboard)
                await bot.send_message(message.chat.id, "<b>Стислий опис багу:</b>\n\n<b>Кроки які Ви зробили щоб побачити баг:</b>\n\n<b>Коментар:</b>\n\n", parse_mode="HTML")
            elif user_state == "sending_bug":
                user_states.pop(message.chat.id, None)
                if message.text == "Повернутись":
                    return
                await bot.send_message(int(devs[0]), f"Вам прийшло нове повідомлення про баг.\nВід @{message.from_user.username}\n\n<b>Повідомлення:</b>\n\n{message.text}", parse_mode="HTML")
                if str(message.from_user.id) in admins:
                    await bot.send_message(message.chat.id, "Ваше повідомлення було надіслано розробнику, дякую Вам за фідбек!", reply_markup=main_menu_admin)
                else:
                    await bot.send_message(message.chat.id, "Ваше повідомлення було надіслано розробнику, дякую Вам за фідбек!", reply_markup=main_menu_markup)
            elif user_state == "notifs_deletion_confirm":
                if message.text == "Ні":
                    await bot.send_message(message.chat.id, "Скасував дію", reply_markup=main_menu_admin)
                    return
                notification_collection.delete_many({})
                await bot.send_message(message.chat.id, "Всю історію оповісток було видалено", reply_markup=main_menu_admin)
            elif user_state == "making_notif":
                user_states.pop(message.chat.id, None)
                if message.text == "Повернутись":
                    return
                await make_group_notification(message)
                await bot.send_message(message.chat.id, "Оповістку надіслано", reply_markup=main_menu_admin)
            elif user_state == "adding_deadline":
                user_states[message.chat.id] = "choosing_time"
                user_deadlines[message.chat.id] = {"title": message.text}
                await bot.send_message(message.chat.id, "Тепер надішліть дату та час.\nФормат: DD.MM HH:MM")
            elif user_state == "choosing_time":
                try:
                    deadline_date = datetime.datetime.strptime(message.text, "%d.%m %H:%M")
                    deadlines_collection.insert_one({"title": user_deadlines[message.chat.id]["title"], "date": deadline_date})
                    await bot.send_message(message.chat.id, "Дедлайн успішно додано!", reply_markup=main_menu_admin)
                    user_states.pop(message.chat.id, None)
                    user_deadlines.pop(message.chat.id, None)
                    logging.info(f"[DEADLINE] [{message.from_user.username}] - Added new deadline")
                except ValueError:
                    await bot.send_message(message.chat.id, "Будь ласка, введіть дату у форматі Day.Monh Hours:Minutes (01.09 13:00)")
            elif message.text == "Видалити" and str(message.from_user.id) in admins:
                user_states[message.chat.id] = "deleting_deadline"
                await bot.send_message(message.chat.id, "Надішліть мені заголовок дедлайну для видалення, він повинен повністю співпадати.")
            elif user_state == "deleting_deadline":
                user_states.pop(message.chat.id, None)
                deadlines = list(deadlines_collection.find())
                for entry in deadlines:
                    if entry["title"] == message.text:
                        deadlines_collection.delete_one({"title": message.text})
                        await bot.send_message(message.chat.id, "Дедлайн було видалено!")
                        logging.info(f"[DEADLINE] [{message.from_user.username}] - Removed deadline")
                        break
                else:
                    await bot.send_message(message.chat.id, "Йой! Не знайшов такого дедлайну.")

            logging.info(f"[MESSAGE] [{message.from_user.first_name} {message.from_user.last_name}] - {message.text}")
        elif str(message.text)[0] == "!":
            if message.chat.type == "supergroup" or message.chat.type == "group":
                bot_info = await bot.get_me()
                bot_member = await bot.get_chat_member(message.chat.id, bot_info.id)
                # Group commands
                if message.text == "!s":
                    today = datetime.datetime.now().strftime('%A')
                    schedule = await get_schedule(today)
                    sent_message = await bot.send_message(message.chat.id, schedule, parse_mode="HTML")
                    if bot_member.status in ["administrator", "creator"]:
                        # await bot.delete_message(message.chat.id, message.message_id)
                        # chat = await bot.get_chat(message.chat.id)
                        # if chat.pinned_message:
                        #     await bot.unpin_chat_message(message.chat.id, chat.pinned_message.message_id)
                        await bot.pin_chat_message(message.chat.id, sent_message.message_id)
                elif message.text == "!st":
                    day = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%A')
                    schedule = await get_schedule(day)
                    sent_message = await bot.send_message(message.chat.id, f"<b>{day}</b>\n\n\n{schedule}", parse_mode="HTML")
                    if bot_member.status in ["administrator", "creator"]:
                        # await bot.delete_message(message.chat.id, message.message_id)
                        # chat = await bot.get_chat(message.chat.id)
                        # if chat.pinned_message:
                        #     await bot.unpin_chat_message(message.chat.id, chat.pinned_message.message_id)
                        await bot.pin_chat_message(message.chat.id, sent_message.message_id)
                elif message.text == "!clear_markup":
                    await bot.send_message(message.chat.id, "Клавіатуру видалено!", reply_markup=ReplyKeyboardRemove())
                else:
                    await bot.send_message(message.chat.id, "В групі працюють тільки команди:\n\n!s (schedule) - розклад на сьогодні\n!st (schedule tomorrow) - розклад на завтра\n!clear_markup - видалити клавіатуру.")
    else:
        info_arr = [message.from_user.username, message.from_user.first_name, message.from_user.last_name]
        if message.text == "Надіслати запит":
            if pending_join_collection.find_one({"info": info_arr}):
                await bot.send_message(message.chat.id,"Ваш запит на доступ вже надіслано. Староста також людина яка відпочиває, дякую за розуміння.\nНе переймайтеся, Ваш запит обовʼязково переглянуть.")
            elif group_collection.find_one({"_id": str(message.from_user.id)}):
                await bot.send_message(message.chat.id, "Вам вже надано доступ!", reply_markup=main_menu_markup)
            elif blacklist_requests.find_one({"_id": str(message.from_user.id)}):
                await bot.send_message(message.chat.id, "Ваш ID в чорному списку, звʼязок неможливий.", reply_markup=ReplyKeyboardRemove())
            else:
                user_states[message.chat.id] = "want_to_use"
                await bot.send_message(message.chat.id, "Напишіть коротеньке повідомлення чому Вам потрібен доступ. \nПояснення значно полегшить життя, дякую за розуміння! :)")
        elif user_states.get(message.chat.id) == "want_to_use":
            if message.text != "Надіслати запит":
                user_states.pop(message.chat.id, None)
                if message.from_user.last_name:
                    user_info = f"@{message.from_user.username}, {message.from_user.first_name} {message.from_user.last_name}"
                else:
                    user_info = f"@{message.from_user.username}, {message.from_user.first_name}"
                entry = {
                    "_id": message.from_user.id,
                    "info": info_arr,
                    "text": message.text,
                    "date": str(datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')),
                }

                pending_join_collection.insert_one(entry)

                keyboard = types.InlineKeyboardMarkup()
                approve = types.InlineKeyboardButton("Схвалити", callback_data=f"approve_{message.from_user.id}")
                decline = types.InlineKeyboardButton("Відхилити", callback_data=f"decline_{message.from_user.id}")
                blacklist = types.InlineKeyboardButton("Чорний список", callback_data=f"blacklist_{message.from_user.id}")
                keyboard.add(approve, decline, blacklist)

                await bot.send_message(int(headman), f"<b>Новий запит на використовування боту!</b>\n\n\nВід {user_info}.\n\nТекст повідомлення:\n{message.text}", parse_mode="HTML", reply_markup=keyboard)
                await bot.send_message(message.chat.id, "Ваш запит було надіслано, чекайте на відповідь.")
                logging.info(f"[REQUEST] [{message.from_user.username}] - Sent request to access bot!")
        else:
            logging.info(f"[REQUEST] [{message.from_user.username}] - Someone tried to access bot! ")
            await bot.send_message(message.chat.id, "Після оновлення бот став з обмеженим доступом, якщо Ви бачете це повідмолення, вас не було занесено до вайт лісту.\n\nЯкщо вважаєте що це було помилково, або вам потрібен доступ - звʼязок зі старостою за кнопкою нижче.", reply_markup=guest_markup)


# Handle callback query
@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data.startswith("approve_") or call.data.startswith("decline_") or call.data.startswith("blacklist_"):
        user_id = call.data.split("_")[1]
        entry = pending_join_collection.find({"_id": int(user_id)})
        if call.data.startswith("approve_"):
            info = list(entry)[0]

            pending_join_collection.delete_one({"_id": int(user_id)})
            group_collection.insert_one({"_id": user_id, "username": info["info"][0]})
            await bot.send_message(user_id, "Вітаю, Ваш запит на доступ було ухвалено!\nПриємного користування <3", reply_markup=main_menu_markup)
            logging.info(f"[REQUEST] [{call.message.from_user.username}] - Request was approved!")
        elif call.data.startswith("decline_"):
            pending_join_collection.delete_one({"_id": int(user_id)})
            await bot.send_message(user_id, "Нажаль Ваш запит на доступ було відхилено.")
            logging.info(f"[REQUEST] [{call.message.from_user.username}] - Request was denied")
        elif call.data.startswith("blacklist_"):
            info = list(entry)[0]

            pending_join_collection.delete_one({"_id": int(user_id)})
            blacklist_requests.insert_one({"_id": user_id, "username": info["info"][0]})
            await bot.send_message(user_id, "Вас було занесено до чорного списку, запити від вас більше надходити не будуть.")
            logging.info(f"[REQUEST] [{call.message.from_user.username}] - User blacklisted from now.")
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.id)
    elif call.data.startswith("mark_"):
        _, day, lesson_number = call.data.split("_")
        day_to_find = datetime.datetime.strptime(f"{day}.{datetime.datetime.now().year}", "%d.%m.%Y").strftime("%A")
        user_id = call.from_user.id
        username = call.from_user.username or "N/A"
        first_name = call.from_user.first_name or ""
        last_name = call.from_user.last_name or ""

        if lesson_number == "clear":
            attendance_collection.delete_many({"userid": user_id})
            await bot.answer_callback_query(call.id, "Відмітки скасовано.")
        else:
            lesson_number = int(lesson_number)

            lesson_info = schedule_collection.find_one({"day": day_to_find, "number": str(lesson_number)})
            subject = lesson_info["subject"] if lesson_info else "Невідома дисципліна"

            attendance_record = attendance_collection.find_one({"userid": user_id, "day": day, "lesson": lesson_number})

            if attendance_record:
                await bot.answer_callback_query(call.id, f"Ви вже відмічені на {lesson_number} парі.")
            else:
                attendance_collection.update_one(
                    {"userid": user_id, "day": day, "lesson": lesson_number},
                    {
                        "$addToSet": {"attendees": [call.from_user.username, call.from_user.first_name, call.from_user.last_name]},
                        "$set": {"subject": subject}
                    },
                    upsert=True
                )
                await bot.answer_callback_query(call.id, f"Вас відмічено на {lesson_number} парі!")
    elif call.data == "view_marked":
        day = datetime.datetime.now().strftime("%d.%m")
        await view_attendance(call.message, day)
    elif call.data.startswith("history_"):
        _, day = call.data.split("_")
        await view_attendance(call.message, day)
        await bot.answer_callback_query(call.id, f"Надаю історію відміток за {day}!")
    elif call.data == "toggle_deadline_reminder":
        logging.info(f"Callback data receives: {call.data}")
        user_id = str(call.from_user.id)
        user_config = user_settings.find_one({"_id": user_id})

        new_value = not user_config["deadline_reminder"]
        user_settings.update_one({"_id": user_id}, {"$set": {"deadline_reminder": new_value}})

        status_text = "Увімкнено" if new_value else "Вимкнено"
        await bot.answer_callback_query(call.id, f"Нагадування про дедлайни {status_text}!")

        message_text = f"<b>Ваші налаштування:</b>\n\nНагадування про дедлайни: {status_text}"
        markup = types.InlineKeyboardMarkup()
        toggle_reminder_button = types.InlineKeyboardButton("Перемкнути нагадування про дедлайни", callback_data="toggle_deadline_reminder")
        markup.add(toggle_reminder_button)
        await bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data.startswith("notif_"):
        _, reaction, notification_id = call.data.split("_")

        notification = notification_collection.find_one({"_id": str(notification_id)})
        if not notification:
            await bot.answer_callback_query(call.id, "Оповістку не знайдено!")
            return

        current_reactions = notification.get("reactions", {})
        if call.from_user.id in current_reactions:
            if current_reactions[call.from_user.id] == reaction:
                await bot.answer_callback_query(call.id, "Ви вже відреагували.")
                return
            else:
                notification_collection.update_one({"_id": notification_id}, {"$set": {f"reactions.{call.from_user.id}": reaction}})
                await bot.answer_callback_query(call.id, "Вашу реакцію записано!")
        else:
            notification_collection.update_one({"_id": notification_id}, {"$set": {f"reactions.{call.from_user.id}": reaction}})
            await bot.answer_callback_query(call.id, "Вашу реакцію записано!")


# START BOT
async def main():
    asyncio.create_task(send_daily_notifications())
    await bot.send_message(int(devs[0]), "Bot started successfully!")
    await bot.polling(none_stop=True)

logging.info("Started successfully!")

if __name__ == '__main__':
    asyncio.run(main())
