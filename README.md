# LightCore

LightCore is an all-in-one Discord server bot built with Python and `discord.py` 2.7.1. It uses hybrid commands, so the same command can be used with the `.` prefix or as a Discord slash command.

## Final feature set

### Core
- `.help` / `/help` — one unified categorized command list
- `.ping` / `/ping`
- `.about` / `/about`
- Prefix: `.`
- Automatic cog loading and slash-command synchronization

### Moderation & AutoMod
- Ban
- Kick
- Timeout/mute
- Warn + warning history
- Persistent moderation action logs in SQLite
- AutoMod blocked-term protection
- Server message edit/delete logging

### Leveling & XP
- XP per server/member
- Configurable XP minimum/maximum
- Configurable XP cooldown
- Level-up message templates
- Level role rewards
- `.rank` visual image rank cards
- `.leaderboard`, `.levels`, `.lb`
- Persistent XP and level rewards

### Tickets
- Ticket panel with persistent button
- Configurable ticket category
- One open ticket per member
- Ticket close command
- Persistent ticket records
- Transcript capture on close
- Optional transcript log channel

### Self Roles
- Button-based self-role panels
- Persistent role-panel records
- Panels restored after bot restart
- Permission and role-hierarchy checks

### Economy
- LightCoins balance
- Daily rewards
- Member-to-member payments
- Wealth leaderboard
- Shop item storage
- Persistent balances and shop data

### Music
- Join / leave voice channels
- Play audio through `yt-dlp`
- Stop playback
- Voice support through `discord.py[voice]`
- Requires FFmpeg installed on the host

### Embeds & Announcements
- Custom embed command
- Announcement embeds

### Server Configuration
- Central admin panel
- GUI feature toggles
- Logging channel settings
- Welcome/goodbye settings
- Ticket settings
- Leveling settings
- Member statistics settings
- Application settings
- Temporary voice settings

### Welcome & Goodbye
- Configurable welcome channel/message
- Configurable goodbye channel/message
- `{user}` and `{server}` placeholders

### Giveaways
- Persistent claim-based giveaways
- Stored giveaway state
- Stored entries and winner
- Giveaway buttons restored after restart

### Custom Commands
- Add custom responses
- Remove custom responses
- List custom commands
- Persistent autoresponders

### Fun
- 8-ball
- Coin flip
- Dice
- Random choice
- Random number
- Random meme fetcher with age-restricted posts skipped

### Games
- Rock-paper-scissors
- Tic-tac-toe
- Number guessing
- Trivia
- Interactive buttons and game sessions

### Server & Member Information
- Server information
- Member/user information
- Member growth statistics
- Join/leave retention estimate
- Message activity statistics
- Persistent member event records

### Applications
- Create application forms
- Up to five questions per form
- Persistent application panels
- Modal submissions
- Persistent staff review buttons
- Accept/deny status tracking
- Applicant notification when reviewed
- Configurable review channel

### Temporary Voice
- Join-to-create voice channel
- Automatic temporary VC creation
- Owner controls: rename, lock, unlock, limit, transfer ownership
- Persistent owner records
- Empty temporary channels are cleaned up
- Active ownership is restored after restart

## Project structure

```text
LightCore/
├── main.py
├── database.py
├── requirements.txt
├── .env.example
├── README.md
└── cogs/
    ├── __init__.py
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
    ├── custom_commands.py
    ├── temp_voice.py
    ├── fun.py
    ├── games.py
    ├── serverinfo.py
    ├── admin.py
    ├── memberstats.py
    └── applications.py
```

## Requirements

- Python **3.10+** recommended
- `discord.py 2.7.1`
- FFmpeg for music playback
- A Discord bot application/token
- Message Content, Server Members and other required intents enabled in the Discord Developer Portal

`discord.py 2.7.1` is the current stable release used by this project. citeturn0search0

## Setup

### 1. Get the repository

Clone/download the repository and open a terminal in the project folder.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_client_id
```

Never paste your real bot token into GitHub, README files, or chat. Never commit `.env`.

### 4. Configure the Discord bot

In the Discord Developer Portal:

- Enable **Message Content Intent**.
- Enable **Server Members Intent**.
- Enable any other privileged intent required by the features you use.
- Invite the bot with the permissions needed for moderation, channels, roles, messages, voice and applications.

### 5. Start LightCore

```bash
python main.py
```

On startup LightCore will:

1. Load `.env`.
2. Validate `BOT_TOKEN` and `CLIENT_ID`.
3. Initialize `lightcore.db` and all persistent tables.
4. Load every cog listed in `main.py`.
5. Register hybrid commands.
6. Connect to Discord.
7. Synchronize slash commands.

## Database

LightCore uses SQLite by default in `lightcore.db`. Persistent areas include:

- Server settings
- Warnings
- Moderation logs
- Server event logs
- XP and level rewards
- Economy balances and shop items
- Self-role panels
- Tickets and transcripts
- Giveaways and entries
- Member events
- Applications, panels and submissions
- Temporary voice channels

The database layer keeps the cog interface separate from storage so it can be migrated to PostgreSQL later.

## Main commands

Use `.help` or `/help` inside Discord for the complete live list. Major commands include:

```text
Moderation: ban, kick, mute, warn, warnings, automod
Levels: rank, leaderboard, levelconfig ...
Tickets: ticketpanel, setticketcategory, setticketlog, close
Roles: selfrole
Economy: balance, daily, pay, rich, shop
Music: join, play, stop, leave
Server: serverinfo, userinfo, memberstats, growth, retention
Fun: 8ball, coinflip, dice, choose, randomnumber, meme
Games: rps, tictactoe, guess, trivia
Configuration: panel, adminpanel, setlog, setwelcome, setgoodbye
Giveaways: giveaway
Applications: applicationcreate, applicationpanel, applicationreviewchannel, applications
Custom commands: customadd, customremove, customlist
Temp Voice: tempvoice_setup
```

## Hosting checklist

Before deploying to a host:

- Use Python 3.10+.
- Run `pip install -r requirements.txt`.
- Add `BOT_TOKEN` and `CLIENT_ID` as environment variables.
- Make sure the host runs `python main.py` as the long-running process.
- Install FFmpeg if music is enabled.
- Keep the SQLite database on persistent storage; otherwise server settings and data can be lost when the instance is recreated.
- Do not expose or commit the bot token.

## Integration status

The repository has been integration-audited around the cog list in `main.py`. The database schema now covers the persistent feature areas, command naming is intentionally unique across cogs, and `.help`/`/help` is the single categorized help entry point.

A real Discord login/synchronization test still requires a valid runtime with the bot credentials supplied through environment variables; credentials should never be placed in source control or chat.

## License

Private project / all rights reserved unless the repository owner chooses another license.
