import sqlite3
from pathlib import Path

DB_PATH = Path("lightcore.db")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT NOT NULL DEFAULT '.',
            log_channel INTEGER,
            welcome_channel INTEGER,
            goodbye_channel INTEGER,
            welcome_message TEXT,
            goodbye_message TEXT,
            muted_role INTEGER,
            ticket_category INTEGER,
            ticket_log_channel INTEGER,
            level_enabled INTEGER NOT NULL DEFAULT 1,
            currency_enabled INTEGER NOT NULL DEFAULT 1,
            automod_enabled INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS xp (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS balances (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS custom_commands (
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            response TEXT NOT NULL,
            PRIMARY KEY (guild_id, name)
        );
        CREATE TABLE IF NOT EXISTS shop_items (
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            PRIMARY KEY (guild_id, name)
        );
        ''')


def ensure_guild(guild_id):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))


def get_setting(guild_id, key):
    allowed = {
        'prefix', 'log_channel', 'welcome_channel', 'goodbye_channel',
        'welcome_message', 'goodbye_message', 'muted_role', 'ticket_category',
        'ticket_log_channel', 'level_enabled', 'currency_enabled', 'automod_enabled'
    }
    if key not in allowed:
        raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        row = db.execute(f"SELECT {key} FROM guild_settings WHERE guild_id = ?", (guild_id,)).fetchone()
        return row[key] if row else None


def set_setting(guild_id, key, value):
    allowed = {
        'prefix', 'log_channel', 'welcome_channel', 'goodbye_channel',
        'welcome_message', 'goodbye_message', 'muted_role', 'ticket_category',
        'ticket_log_channel', 'level_enabled', 'currency_enabled', 'automod_enabled'
    }
    if key not in allowed:
        raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        db.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))
