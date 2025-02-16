import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import pytz
from datetime import datetime
import sqlite3
import re
import random

API_TOKEN = '7609138716:AAEKxcS4QAt0_bCd1fRZui7Dl0EZJGCsPfs'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Form(StatesGroup):
    delete_link = State()
    delete_all_links = State()
    send_all_users = State()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Создаем таблицу users, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            timezone TEXT DEFAULT 'Europe/Moscow'
        )
    ''')
    # Создаем таблицу links, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    # Добавляем пользователя, если его нет
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

    # Анимация с текстом
    await message.answer("🎉 Добро пожаловать! 🎉")
    await asyncio.sleep(1)
    await message.answer("🔄 Загружаю информацию...")
    await asyncio.sleep(1)
    await message.answer("✅ Готово!")

    # Сообщение с инструкцией и примерами
    instruction_text = (
        "Привет! Это бот для ежедневной отправки ссылок.\n\n"
        "Чтобы добавить ссылки, просто отправь их мне. Ты можешь отправить одну ссылку или несколько через запятую или с новой строки.\n\n"
        "Примеры:\n"
        "1. Одна ссылка:\n"
        "https://example.com\n\n"
        "2. Несколько ссылок через запятую:\n"
        "https://example.com, https://anotherexample.com\n\n"
        "3. Несколько ссылок с новой строки:\n"
        "https://example.com\n"
        "https://anotherexample.com\n\n"
        "Используй /menu для доступа к меню."
    )

    await message.answer(instruction_text)

# Обработчик команды /menu
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Удалить ссылку")],
        [KeyboardButton(text="Удалить все ссылки")],
        [KeyboardButton(text="Показать ссылки")]
    ], resize_keyboard=True)

    await message.answer("Меню:", reply_markup=keyboard)

# Обработчик команды /send_all_users
@dp.message(Command("send_all_users"))
async def cmd_send_all_users(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username

    # Проверяем, имеет ли пользователь право на выполнение команды
    if username == "vagabdsgn":
        await message.answer("О чем вы хотите оповестить пользователей? Напишите сообщение:")
        await state.set_state(Form.send_all_users)
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

# Обработчик состояния для рассылки сообщений всем пользователям
@dp.message(Form.send_all_users)
async def process_send_all_users(message: types.Message, state: FSMContext):
    notification_text = message.text

    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()

    for user in users:
        user_id = user[0]
        await bot.send_message(user_id, notification_text)

    conn.close()
    await state.clear()
    await message.answer("✅ Сообщение успешно отправлено всем пользователям.")

# Обработчик для добавления ссылок
@dp.message(lambda message: re.match(r'https?://\S+', message.text))
async def process_add_link(message: types.Message):
    user_id = message.from_user.id
    urls_text = message.text

    # Заменяем переносы строк и пробелы на запятые
    urls_text = urls_text.replace('\n', ',').replace(' ', ',')

    # Разделяем текст на отдельные ссылки
    urls = [url.strip() for url in urls_text.split(',') if url.strip()]

    # Валидация ссылок
    invalid_urls = []
    valid_urls = []
    for url in urls:
        if re.match(r'https?://\S+', url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)

    if invalid_urls:
        await message.answer(f"Некоторые ссылки некорректны и не были добавлены:\n{', '.join(invalid_urls)}\n\n"
                            f"Убедитесь, что ссылки начинаются с 'http://' или 'https://' и не содержат лишних символов.")
    if not valid_urls:
        return

    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Добавляем каждую валидную ссылку в базу данных
    for url in valid_urls:
        cursor.execute('INSERT INTO links (user_id, url) VALUES (?, ?)', (user_id, url))

    conn.commit()
    conn.close()

    # Анимация добавления ссылок
    await message.answer("🔗 Добавляю ссылки...")
    await asyncio.sleep(1)
    await message.answer(f"✅ Добавлено ссылок: {len(valid_urls)}")

# Обработчик команды "Удалить ссылку"
@dp.message(lambda message: message.text == "Удалить ссылку")
async def process_delete_link(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Проверяем, есть ли ссылки у пользователя
    cursor.execute('SELECT link_id FROM links WHERE user_id = ?', (user_id,))
    links = cursor.fetchall()
    conn.close()

    if not links:
        await message.answer("У вас пока нет ссылок. Удалять нечего.")
        return

    await message.answer("Введите ID ссылки для удаления (или несколько ID через запятую):")
    await state.set_state(Form.delete_link)

# Обработчик состояния для удаления ссылки
@dp.message(Form.delete_link)
async def process_delete_link_state(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    link_ids = message.text

    # Разделяем ID ссылок на отдельные значения
    link_ids = [link_id.strip() for link_id in link_ids.split(',') if link_id.strip()]

    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Удаляем каждую ссылку по ID
    deleted_count = 0
    for link_id in link_ids:
        cursor.execute('DELETE FROM links WHERE user_id = ? AND link_id = ?', (user_id, link_id))
        if cursor.rowcount > 0:
            deleted_count += 1

    conn.commit()
    conn.close()

    await state.clear()
    if deleted_count > 0:
        await message.answer(f"🗑️ Удалено ссылок: {deleted_count}")
    else:
        await message.answer("❌ Не удалось найти ссылки с указанными ID. Проверьте правильность ввода.")

# Обработчик команды "Удалить все ссылки"
@dp.message(lambda message: message.text == "Удалить все ссылки")
async def process_delete_all_links(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Проверяем, есть ли ссылки у пользователя
    cursor.execute('SELECT link_id FROM links WHERE user_id = ?', (user_id,))
    links = cursor.fetchall()
    conn.close()

    if not links:
        await message.answer("У вас пока нет ссылок. Удалять нечего.")
        return

    await message.answer("Вы уверены, что хотите удалить все ссылки? (да/нет)")
    await state.set_state(Form.delete_all_links)

# Обработчик состояния для удаления всех ссылок
@dp.message(Form.delete_all_links)
async def process_delete_all_links_state(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    confirmation = message.text.lower()

    if confirmation == 'да':
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        cursor.execute('DELETE FROM links WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await state.clear()
        await message.answer("🗑️ Все ссылки удалены.")
    else:
        await state.clear()
        await message.answer("❌ Удаление отменено.")

# Обработчик команды "Показать ссылки"
@dp.message(lambda message: message.text == "Показать ссылки")
async def process_show_links(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT link_id, url FROM links WHERE user_id = ?', (user_id,))
    links = cursor.fetchall()
    conn.close()

    if links:
        links_text = "\n".join([f"ID: {link[0]}, Ссылка: {link[1]}" for link in links])
        await message.answer(f"📜 Ваши ссылки:\n{links_text}")
    else:
        await message.answer("📭 У вас пока нет ссылок. Добавьте их, чтобы я мог отправлять вам ежедневные ссылки!")

# Функция для отправки ежедневных ссылок
async def send_daily_link():
    while True:
        now = datetime.now(pytz.utc)
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, timezone FROM users')
        users = cursor.fetchall()

        for user in users:
            user_id, timezone = user
            try:
                user_time = now.astimezone(pytz.timezone(timezone))

                if user_time.hour == 17 and user_time.minute == 30:
                    cursor.execute(
                        'SELECT link_id, url FROM links WHERE user_id = ? ORDER BY RANDOM() LIMIT 1',
                        (user_id,))
                    link = cursor.fetchone()

                    if link:
                        link_id, url = link
                        await bot.send_message(user_id, f"🎁 Ваша ссылка на сегодня: {url}")
                        cursor.execute('DELETE FROM links WHERE link_id = ?', (link_id,))
                        conn.commit()
                    else:
                        await bot.send_message(user_id, "📭 У вас закончились ссылки. Пожалуйста, добавьте новые ссылки, чтобы я мог продолжать отправлять их вам ежедневно!")
            except pytz.exceptions.UnknownTimeZoneError:
                # Если временная зона некорректная, пропускаем пользователя
                continue

        conn.close()
        await asyncio.sleep(60)

# Основная функция для запуска бота
async def main():
    # Запуск задачи для отправки ежедневных ссылок
    asyncio.create_task(send_daily_link())

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
