import sqlite3
import os

DB_NAME = "./invite_links_v6.db"

TABLE_LINK_INFO_NAME = "LinkInfo"
CREATE_TABLE_LINK_INFO = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_LINK_INFO_NAME} (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER NOT NULL,
        twitch_user_id INTEGER,
        patreon_user_id INTEGER,
        invite_link TEXT NOT NULL
    )
"""
TABLE_USER_SESSION_NAME = "UserSession"
CREATE_TABLE_USER_SESSIONS = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_USER_SESSION_NAME} (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER NOT NULL,
        telegram_chat_from_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        session_id TEXT NOT NULL
    )
"""

# Check if the database exists
def check_or_create_db():
    db_exists = os.path.exists(DB_NAME)
    if not db_exists:
        print(f"Database '{DB_NAME}' not found. Creating a new one...")
        initialize_db()
    else:
        print(f"Database '{DB_NAME}' already exists.")

# Database initialization
def initialize_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_LINK_INFO)
    cursor.execute(CREATE_TABLE_USER_SESSIONS)
    conn.commit()
    conn.close()

# Store an object in the database
def store_link(telegram_user_id, twitch_user_id, patreon_user_id, invite_link):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {TABLE_LINK_INFO_NAME} (telegram_user_id, twitch_user_id, patreon_user_id, invite_link) VALUES (?, ?, ?, ?)", (telegram_user_id, twitch_user_id, patreon_user_id, invite_link))
    conn.commit()
    conn.close()

# Retrieve all objects from the database
def retrieve_all_links():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_LINK_INFO_NAME}")
    records = cursor.fetchall()
    conn.close()
    return records

# Find links by telegram ID (return only the links)
def find_links_by_telegram_id(telegram_user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT invite_link FROM {TABLE_LINK_INFO_NAME} WHERE telegram_user_id = ?", (telegram_user_id,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

# Find links by twitch ID (return only the links)
def find_links_by_twitch_id(twitch_user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT invite_link FROM {TABLE_LINK_INFO_NAME} WHERE twitch_user_id = ?", (twitch_user_id,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

# Find links by patreon ID (return only the links)
def find_links_by_patreon_id(patreon_user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT invite_link FROM {TABLE_LINK_INFO_NAME} WHERE patreon_user_id = ?", (patreon_user_id,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

# Find links by user_id (return only the links)
def user_owns_link(telegram_user_id, invite_link):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_LINK_INFO_NAME} WHERE telegram_user_id = ? AND invite_link = ?", (telegram_user_id, invite_link, ))
    records = len([row[0] for row in cursor.fetchall()])
    conn.close()
    return True if records > 0 else False

# Remove the entry with a used invite link
def remove_link(invite_link):

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {TABLE_LINK_INFO_NAME} WHERE invite_link = ?", (invite_link,))
            conn.commit()
            return True
    except sqlite3.OperationalError as e:
        print(e)
        return False



# Store an object in the database
def store_session(telegram_user_id, telegram_chat_from_id, platform, session_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {TABLE_USER_SESSION_NAME} (telegram_user_id, telegram_chat_from_id, platform, session_id) VALUES (?, ?, ?, ?)", (telegram_user_id, telegram_chat_from_id, platform, session_id))
    conn.commit()
    conn.close()

# Retrieve all objects from the database
def retrieve_all_sessions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_USER_SESSION_NAME}")
    records = cursor.fetchall()
    conn.close()
    return records

# Retrieve all objects from the database
def find_user_info_from_session(session_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT telegram_user_id, telegram_chat_from_id, platform FROM {TABLE_USER_SESSION_NAME} WHERE session_id = ?", (session_id,))
    records = cursor.fetchall()
    conn.close()
    return records[0]

# Remove the entry with a used invite link
def remove_user_session(telegram_user_id):

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {TABLE_USER_SESSION_NAME} WHERE telegram_user_id = ?", (telegram_user_id,))
            conn.commit()
            return True
    except sqlite3.OperationalError as e:
        print(e)
        return False