import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import pytz
from datetime import datetime, timedelta
import sqlite3
import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

API_TOKEN = '7609138716:AAEKxcS4QAt0_bCd1fRZui7Dl0EZJGCsPfs'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Form(StatesGroup):
    delete_link = State()
    delete_all_links = State()

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

    await message.answer(f"Добавлено ссылок: {len(valid_urls)}")

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
        await message.answer(f"Удалено ссылок: {deleted_count}")
    else:
        await message.answer("Не удалось найти ссылки с указанными ID. Проверьте правильность ввода.")

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
        await message.answer(f"Ваши ссылки:\n{links_text}")
    else:
        await message.answer("У вас пока нет ссылок. Добавьте их, чтобы я мог отправлять вам ежедневные ссылки!")

# Функция для отправки ежедневных ссылок
async def send_daily_link():
    while True:
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)  # Устанавливаем время отправки на 9:00 утра

        if now >= target_time:
            target_time += timedelta(days=1)  # Устанавливаем следующее время отправки на завтра

        await asyncio.sleep((target_time - now).total_seconds())

        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, url FROM links')
        links = cursor.fetchall()
        conn.close()

        for user_id, url in links:
            await bot.send_message(user_id, f"Ваша ежедневная ссылка: {url}")

# Основная функция для запуска бота
async def main():
    # Запуск задачи для отправки ежедневных ссылок
    asyncio.create_task(send_daily_link())

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

# Тесты
@pytest.mark.asyncio
async def test_cmd_start():
    message = AsyncMock()
    message.from_user.id = 1
    message.text = "/start"

    await cmd_start(message)

    # Проверяем, что таблицы созданы и пользователь добавлен
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = 1')
    user = cursor.fetchone()
    assert user is not None
    conn.close()

@pytest.mark.asyncio
async def test_process_add_link():
    message = AsyncMock()
    message.from_user.id = 1
    message.text = "https://example.com"

    await process_add_link(message)

    # Проверяем, что ссылка добавлена
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM links WHERE user_id = 1')
    link = cursor.fetchone()
    assert link is not None
    conn.close()

@pytest.mark.asyncio
async def test_process_delete_link():
    message = AsyncMock()
    message.from_user.id = 1
    message.text = "Удалить ссылку"

    state = AsyncMock()  # Используем AsyncMock вместо MagicMock
    await process_delete_link(message, state)

    # Проверяем, что состояние установлено
    state.set_state.assert_called_with(Form.delete_link)

@pytest.mark.asyncio
async def test_process_show_links():
    message = AsyncMock()
    message.from_user.id = 1
    message.text = "Показать ссылки"

    # Добавляем тестовую ссылку в базу данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO links (user_id, url) VALUES (?, ?)', (1, "https://example.com"))
    conn.commit()

    await process_show_links(message)

    # Проверяем, что сообщение отправлено
    message.answer.assert_called()

    # Очищаем базу данных
    cursor.execute('DELETE FROM links WHERE user_id = 1')
    conn.commit()
    conn.close()

@pytest.mark.asyncio
async def test_send_daily_link():
    # Мокируем бота и базу данных
    with patch('aiogram.Bot.send_message') as mock_send_message:
        # Добавляем тестовую ссылку в базу данных
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO links (user_id, url) VALUES (?, ?)', (1, "https://example.com"))
        conn.commit()

        # Запускаем функцию отправки ежедневных ссылок
        await send_daily_link()

        # Проверяем, что сообщение было отправлено
        mock_send_message.assert_called_once_with(1, "Ваша ежедневная ссылка: https://example.com")

        # Очищаем базу данных
        cursor.execute('DELETE FROM links WHERE user_id = 1')
        conn.commit()
        conn.close()
