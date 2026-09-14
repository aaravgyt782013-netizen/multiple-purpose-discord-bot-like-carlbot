import sqlite3
from pathlib import Path

DB_PATH = Path("lightcore.db")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def _add_column(db, table, column, definition):
    columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with connect() as db:
        db.executescript(
            """
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
                ticket_config TEXT,
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
                tempvoice_join_channel INTEGER,
                tempvoice_panel_channel INTEGER
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id INTEGER,
                channel_id INTEGER,
                target_id INTEGER,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS xp (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, level)
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
            CREATE TABLE IF NOT EXISTS role_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL UNIQUE,
                role_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ticket_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                transcript TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL UNIQUE,
                prize TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                winner_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (giveaway_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS member_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                form_name TEXT NOT NULL,
                questions TEXT NOT NULL,
                review_channel INTEGER,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS application_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL UNIQUE,
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
            CREATE TABLE IF NOT EXISTS temp_voice_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS pets (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                species TEXT NOT NULL DEFAULT 'fox',
                level INTEGER NOT NULL DEFAULT 1,
                energy INTEGER NOT NULL DEFAULT 100,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS reward_claims (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reward_type TEXT NOT NULL,
                claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, reward_type)
            );
            CREATE TABLE IF NOT EXISTS xp_boosters (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                multiplier REAL NOT NULL DEFAULT 2.0,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS ticket_meta (
                ticket_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL DEFAULT 'general',
                claimed_by INTEGER,
                priority TEXT NOT NULL DEFAULT 'normal',
                auto_close_minutes INTEGER NOT NULL DEFAULT 0,
                last_activity TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS giveaway_bonus_roles (
                giveaway_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                multiplier INTEGER NOT NULL DEFAULT 2,
                PRIMARY KEY (giveaway_id, role_id)
            );
            CREATE TABLE IF NOT EXISTS invite_cache (
                guild_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                inviter_id INTEGER,
                uses INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, code)
            );
            CREATE TABLE IF NOT EXISTS activity_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS activity_buckets (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                bucket_start TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, bucket_start)
            );
            CREATE TABLE IF NOT EXISTS activity_voice_sessions (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS marriages (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                partner_id INTEGER NOT NULL,
                married_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id),
                UNIQUE (guild_id, partner_id)
            );
            CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild_time ON moderation_logs(guild_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_event_logs_guild_time ON event_logs(guild_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_member_events_guild_time ON member_events(guild_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_app_submissions_app ON application_submissions(application_id, status);
            CREATE INDEX IF NOT EXISTS idx_tickets_guild_status ON tickets(guild_id, status);
            CREATE INDEX IF NOT EXISTS idx_giveaways_guild_status ON giveaways(guild_id, status);
            CREATE INDEX IF NOT EXISTS idx_temp_voice_guild_status ON temp_voice_channels(guild_id, status);
            CREATE INDEX IF NOT EXISTS idx_activity_buckets_guild_bucket ON activity_buckets(guild_id, bucket_start);
            CREATE INDEX IF NOT EXISTS idx_activity_buckets_guild_user ON activity_buckets(guild_id, user_id, bucket_start);
            """
        )
        _add_column(db, "giveaway_entries", "weight", "INTEGER NOT NULL DEFAULT 1")
        _add_column(db, "temp_voice_channels", "locked", "INTEGER NOT NULL DEFAULT 0")
        _add_column(db, "temp_voice_channels", "hidden", "INTEGER NOT NULL DEFAULT 0")
        _add_column(db, "temp_voice_channels", "user_limit", "INTEGER NOT NULL DEFAULT 0")
        _add_column(db, "temp_voice_channels", "panel_message_id", "INTEGER")
        _add_column(db, "guild_settings", "ticket_config", "TEXT")
        _add_column(db, "pets", "xp", "INTEGER NOT NULL DEFAULT 0")
        _add_column(db, "shop_items", "role_id", "INTEGER")
        _add_column(db, "shop_items", "stock", "INTEGER NOT NULL DEFAULT -1")


def ensure_guild(guild_id):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))


_ALLOWED_SETTINGS = {
    'prefix', 'log_channel', 'welcome_channel', 'goodbye_channel',
    'welcome_message', 'goodbye_message', 'muted_role', 'ticket_category',
    'ticket_log_channel', 'ticket_config', 'level_enabled', 'currency_enabled', 'automod_enabled',
    'level_xp_min', 'level_xp_max', 'level_cooldown', 'level_message',
    'memberstats_enabled', 'memberstats_channel', 'application_review_channel',
    'tempvoice_category', 'tempvoice_join_channel', 'tempvoice_panel_channel'
}


def get_setting(guild_id, key):
    if key not in _ALLOWED_SETTINGS:
        raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        row = db.execute(f"SELECT {key} FROM guild_settings WHERE guild_id = ?", (guild_id,)).fetchone()
        return row[key] if row else None


def set_setting(guild_id, key, value):
    if key not in _ALLOWED_SETTINGS:
        raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        db.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))
