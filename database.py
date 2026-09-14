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
            automod_enabled INTEGER NOT NULL DEFAULT 0,
            level_xp_min INTEGER NOT NULL DEFAULT 15,
            level_xp_max INTEGER NOT NULL DEFAULT 25,
            level_cooldown INTEGER NOT NULL DEFAULT 60,
            level_message TEXT DEFAULT 'GG {user}! You reached level {level}.',
            memberstats_enabled INTEGER NOT NULL DEFAULT 1,
            memberstats_channel INTEGER,
            application_review_channel INTEGER,
            tempvoice_category INTEGER,
            tempvoice_join_channel INTEGER
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
        CREATE TABLE IF NOT EXISTS member_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_member_events_guild_time ON member_events(guild_id, created_at);
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            form_name TEXT NOT NULL,
            questions TEXT NOT NULL,
            review_channel INTEGER,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS application_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answers TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewer_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_app_submissions_app ON application_submissions(application_id, status);
        ''')


def ensure_guild(guild_id):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))


def get_setting(guild_id, key):
    allowed = {
        'prefix', 'log_channel', 'welcome_channel', 'goodbye_channel',
        'welcome_message', 'goodbye_message', 'muted_role', 'ticket_category',
        'ticket_log_channel', 'level_enabled', 'currency_enabled', 'automod_enabled',
        'level_xp_min', 'level_xp_max', 'level_cooldown', 'level_message',
        'memberstats_enabled', 'memberstats_channel', 'application_review_channel',
        'tempvoice_category', 'tempvoice_join_channel'
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
        'ticket_log_channel', 'level_enabled', 'currency_enabled', 'automod_enabled',
        'level_xp_min', 'level_xp_max', 'level_cooldown', 'level_message',
        'memberstats_enabled', 'memberstats_channel', 'application_review_channel',
        'tempvoice_category', 'tempvoice_join_channel'
    }
    if key not in allowed:
        raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        db.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))
