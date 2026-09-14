# LightCore

LightCore is an all-in-one Discord server bot built from scratch with Python and `discord.py`.

## Features

- Hybrid commands: `.` prefix + slash commands
- Moderation: ban, kick, timeout/mute, warnings
- AutoMod and server logging
- XP leveling and leaderboards
- Rank cards using member avatars/embeds
- Button-based ticket panels and ticket categories
- Self-roles with buttons
- LightCoins virtual currency, daily rewards, transfers, shop and leaderboard
- Voice music playback through FFmpeg/yt-dlp
- Embed and announcement builder commands
- Interactive configuration panel
- Welcome and goodbye messages
- Claim-based giveaways
- Custom commands and autoresponders

## Setup

1. Install Python 3.10+.
2. Install FFmpeg and make sure it is available on PATH for music playback.
3. Copy `.env.example` to `.env`.
4. Set `BOT_TOKEN` and `CLIENT_ID` in `.env`.
5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Start the bot:

```bash
python main.py
```

Never commit `.env` or a real Discord token.

## Structure

```text
LightCore/
├── main.py
├── config.py
├── database.py
├── requirements.txt
├── .env.example
├── README.md
└── cogs/
    ├── core.py
    ├── moderation.py
    ├── automod.py
    ├── logging.py
    ├── leveling.py
    ├── tickets.py
    ├── roles.py
    ├── currency.py
    ├── music.py
    ├── embeds.py
    ├── panels.py
    ├── welcome.py
    ├── giveaways.py
    └── custom_commands.py
```

## Configuration

Server settings are stored in SQLite (`lightcore.db`) and are intended to be migrated to PostgreSQL later without changing the cog interface. Administrators configure features through LightCore commands and interactive panels instead of editing Python files.

## Discord permissions/intents

Enable the intents LightCore uses in the Discord Developer Portal, especially Message Content, Server Members and Presence where applicable. Give the bot only the permissions required by the features you enable.

## Branding

The bot name, status, command help and embed footers use **LightCore**.

## License

Private project / all rights reserved unless the repository owner chooses another license.
