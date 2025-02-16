import sqlite3
from typing import List, Tuple, Optional

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('bot.db')
    conn.row_factory = sqlite3.Row  # Для доступа к данным по имени столбца
    return conn

# Инициализация базы данных (создание таблиц, если они не существуют)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            timezone TEXT DEFAULT 'UTC'
        )
    ''')

    # Таблица ссылок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            used BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()

# Добавление пользователя
def add_user(user_id: int, timezone: str = 'UTC'):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, timezone) VALUES (?, ?)
    ''', (user_id, timezone))

    conn.commit()
    conn.close()

# Получение часового пояса пользователя
def get_user_timezone(user_id: int) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT timezone FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result['timezone'] if result else None

# Обновление часового пояса пользователя
def update_user_timezone(user_id: int, timezone: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users SET timezone = ? WHERE user_id = ?
    ''', (timezone, user_id))

    conn.commit()
    conn.close()

# Добавление ссылки
def add_link(user_id: int, url: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO links (user_id, url) VALUES (?, ?)
    ''', (user_id, url))

    conn.commit()
    conn.close()

# Удаление ссылки по ID
def delete_link(user_id: int, link_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM links WHERE user_id = ? AND link_id = ?
    ''', (user_id, link_id))

    conn.commit()
    conn.close()

# Получение всех ссылок пользователя
def get_user_links(user_id: int) -> List[Tuple[int, str]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT link_id, url FROM links WHERE user_id = ? AND used = 0
    ''', (user_id,))
    links = cursor.fetchall()

    conn.close()
    return [(link['link_id'], link['url']) for link in links]

# Получение случайной неиспользованной ссылки
def get_random_unused_link(user_id: int) -> Optional[Tuple[int, str]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT link_id, url FROM links 
        WHERE user_id = ? AND used = 0 
        ORDER BY RANDOM() 
        LIMIT 1
    ''', (user_id,))
    link = cursor.fetchone()

    conn.close()
    return (link['link_id'], link['url']) if link else None

# Пометить ссылку как использованную
def mark_link_as_used(link_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE links SET used = 1 WHERE link_id = ?
    ''', (link_id,))

    conn.commit()
    conn.close()

# Удаление всех ссылок пользователя
def delete_all_links(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM links WHERE user_id = ?
    ''', (user_id,))

    conn.commit()
    conn.close()

# Проверка существования пользователя
def user_exists(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result is not None
