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
        db.executescript("""
        CREATE TABLE IF NOT EXISTS guild_settings (guild_id INTEGER PRIMARY KEY,prefix TEXT NOT NULL DEFAULT '.',log_channel INTEGER,welcome_channel INTEGER,goodbye_channel INTEGER,welcome_message TEXT,goodbye_message TEXT,muted_role INTEGER,ticket_category INTEGER,ticket_log_channel INTEGER,ticket_config TEXT,level_enabled INTEGER NOT NULL DEFAULT 1,currency_enabled INTEGER NOT NULL DEFAULT 1,automod_enabled INTEGER NOT NULL DEFAULT 0,level_xp_min INTEGER NOT NULL DEFAULT 15,level_xp_max INTEGER NOT NULL DEFAULT 25,level_cooldown INTEGER NOT NULL DEFAULT 60,level_message TEXT DEFAULT 'GG {user}! You reached level {level}.',memberstats_enabled INTEGER NOT NULL DEFAULT 1,memberstats_channel INTEGER,application_review_channel INTEGER,tempvoice_category INTEGER,tempvoice_join_channel INTEGER,tempvoice_panel_channel INTEGER);
        CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,moderator_id INTEGER NOT NULL,reason TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS moderation_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,action TEXT NOT NULL,target_id INTEGER,moderator_id INTEGER,reason TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS event_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,event_type TEXT NOT NULL,actor_id INTEGER,channel_id INTEGER,target_id INTEGER,details TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS xp (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,xp INTEGER NOT NULL DEFAULT 0,level INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS level_rewards (guild_id INTEGER NOT NULL,level INTEGER NOT NULL,role_id INTEGER NOT NULL,PRIMARY KEY(guild_id,level));
        CREATE TABLE IF NOT EXISTS balances (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,balance INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS custom_commands (guild_id INTEGER NOT NULL,name TEXT NOT NULL,response TEXT NOT NULL,PRIMARY KEY(guild_id,name));
        CREATE TABLE IF NOT EXISTS shop_items (guild_id INTEGER NOT NULL,name TEXT NOT NULL,price INTEGER NOT NULL,description TEXT,PRIMARY KEY(guild_id,name));
        CREATE TABLE IF NOT EXISTS role_panels (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,channel_id INTEGER NOT NULL,message_id INTEGER NOT NULL UNIQUE,role_id INTEGER NOT NULL,label TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ticket_systems (guild_id INTEGER PRIMARY KEY,panel_channel_id INTEGER,panel_message_id INTEGER,log_channel_id INTEGER,transcript_enabled INTEGER NOT NULL DEFAULT 1,auto_close_minutes INTEGER NOT NULL DEFAULT 1440,title TEXT NOT NULL DEFAULT 'Support Tickets',description TEXT NOT NULL DEFAULT 'Choose a ticket type below to contact our support team.',color INTEGER NOT NULL DEFAULT 5793266,enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS ticket_types (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,name TEXT NOT NULL,emoji TEXT NOT NULL DEFAULT '🎫',description TEXT NOT NULL DEFAULT 'Open a support ticket.',support_role_id INTEGER,category_channel_id INTEGER,enabled INTEGER NOT NULL DEFAULT 1,UNIQUE(guild_id,name));
        CREATE TABLE IF NOT EXISTS ticket_instances (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,channel_id INTEGER NOT NULL UNIQUE,opener_id INTEGER NOT NULL,type_id INTEGER NOT NULL,claimed_by INTEGER,priority TEXT NOT NULL DEFAULT 'normal',status TEXT NOT NULL DEFAULT 'open',last_activity TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,closed_at TEXT,closed_by INTEGER);
        CREATE TABLE IF NOT EXISTS ticket_participants (ticket_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(ticket_id,user_id));
        CREATE TABLE IF NOT EXISTS ticket_transcript_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id INTEGER NOT NULL,guild_id INTEGER NOT NULL,channel_id INTEGER NOT NULL,closed_by INTEGER,content TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS app_forms_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT 'Complete the form below.',review_channel_id INTEGER,cooldown_minutes INTEGER NOT NULL DEFAULT 1440,reapply_mode TEXT NOT NULL DEFAULT 'after_denial',enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS app_questions_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,form_id INTEGER NOT NULL,position INTEGER NOT NULL,question TEXT NOT NULL,required INTEGER NOT NULL DEFAULT 1,max_length INTEGER NOT NULL DEFAULT 1000,UNIQUE(form_id,position));
        CREATE TABLE IF NOT EXISTS app_submissions_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,form_id INTEGER NOT NULL,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,answers TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',reviewer_id INTEGER,reviewed_at TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS app_panels_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,form_id INTEGER NOT NULL,guild_id INTEGER NOT NULL,channel_id INTEGER NOT NULL,message_id INTEGER NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS giveaway_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,channel_id INTEGER NOT NULL,message_id INTEGER NOT NULL UNIQUE,host_id INTEGER NOT NULL,prize TEXT NOT NULL,winners INTEGER NOT NULL DEFAULT 1,ends_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active',requirement_role_id INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,ended_at TEXT);
        CREATE TABLE IF NOT EXISTS giveaway_entries_v2 (giveaway_id INTEGER NOT NULL,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,weight INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(giveaway_id,user_id));
        CREATE TABLE IF NOT EXISTS giveaway_bonus_roles_v2 (giveaway_id INTEGER NOT NULL,role_id INTEGER NOT NULL,multiplier INTEGER NOT NULL DEFAULT 2,PRIMARY KEY(giveaway_id,role_id));
        CREATE TABLE IF NOT EXISTS temp_voice_channels (channel_id INTEGER PRIMARY KEY,guild_id INTEGER NOT NULL,owner_id INTEGER NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,status TEXT NOT NULL DEFAULT 'active');
        CREATE TABLE IF NOT EXISTS pets (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,name TEXT NOT NULL,species TEXT NOT NULL DEFAULT 'fox',level INTEGER NOT NULL DEFAULT 1,energy INTEGER NOT NULL DEFAULT 100,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS reward_claims (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,reward_type TEXT NOT NULL,claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(guild_id,user_id,reward_type));
        CREATE TABLE IF NOT EXISTS xp_boosters (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,multiplier REAL NOT NULL DEFAULT 2.0,expires_at TEXT NOT NULL,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS invite_cache (guild_id INTEGER NOT NULL,code TEXT NOT NULL,inviter_id INTEGER,uses INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(guild_id,code));
        CREATE TABLE IF NOT EXISTS activity_stats (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,message_count INTEGER NOT NULL DEFAULT 0,voice_seconds INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS activity_buckets (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,bucket_start TEXT NOT NULL,message_count INTEGER NOT NULL DEFAULT 0,voice_seconds INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(guild_id,user_id,bucket_start));
        CREATE TABLE IF NOT EXISTS activity_voice_sessions (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,joined_at TEXT NOT NULL,channel_id INTEGER,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS marriages (guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,partner_id INTEGER NOT NULL,married_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(guild_id,user_id),UNIQUE(guild_id,partner_id));
        CREATE INDEX IF NOT EXISTS idx_tickets_v2_guild_status ON ticket_instances(guild_id,status);
        CREATE INDEX IF NOT EXISTS idx_apps_v2_form_status ON app_submissions_v2(form_id,status);
        CREATE INDEX IF NOT EXISTS idx_giveaways_v2_status ON giveaway_v2(guild_id,status);
        """)
        _add_column(db,"ticket_types","log_channel_id","INTEGER")
        _add_column(db,"ticket_types","transcript_channel_id","INTEGER")
        _add_column(db,"ticket_types","discord_category_id","INTEGER")
        _add_column(db,"temp_voice_channels","locked","INTEGER NOT NULL DEFAULT 0")
        _add_column(db,"temp_voice_channels","hidden","INTEGER NOT NULL DEFAULT 0")
        _add_column(db,"temp_voice_channels","user_limit","INTEGER NOT NULL DEFAULT 0")
        _add_column(db,"temp_voice_channels","panel_message_id","INTEGER")
        _add_column(db,"pets","xp","INTEGER NOT NULL DEFAULT 0")
        _add_column(db,"shop_items","role_id","INTEGER")
        _add_column(db,"shop_items","stock","INTEGER NOT NULL DEFAULT -1")


def ensure_guild(guild_id):
    with connect() as db: db.execute("INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)",(guild_id,))

_ALLOWED_SETTINGS={'prefix','log_channel','welcome_channel','goodbye_channel','welcome_message','goodbye_message','muted_role','ticket_category','ticket_log_channel','ticket_config','level_enabled','currency_enabled','automod_enabled','level_xp_min','level_xp_max','level_cooldown','level_message','memberstats_enabled','memberstats_channel','application_review_channel','tempvoice_category','tempvoice_join_channel','tempvoice_panel_channel'}

def get_setting(guild_id,key):
    if key not in _ALLOWED_SETTINGS: raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db:
        row=db.execute(f"SELECT {key} FROM guild_settings WHERE guild_id=?",(guild_id,)).fetchone(); return row[key] if row else None

def set_setting(guild_id,key,value):
    if key not in _ALLOWED_SETTINGS: raise KeyError(key)
    ensure_guild(guild_id)
    with connect() as db: db.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?",(value,guild_id))
