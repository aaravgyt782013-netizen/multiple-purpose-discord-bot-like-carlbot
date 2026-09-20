# Minecraft Status Discord Bot

A Discord.js bot for checking and monitoring Minecraft Java servers.

## Environment variables

```env
BOT_TOKEN=your_discord_bot_token
CLIENT_ID=your_discord_application_client_id
BOT_NAME=LightCore
MC_STATUS_INTERVAL_SECONDS=60
```

- `BOT_TOKEN`: Discord bot token.
- `CLIENT_ID`: Discord application/client ID.
- `BOT_NAME`: bot username to use when the bot starts. Leave empty to keep the current Discord username.
- `MC_STATUS_INTERVAL_SECONDS`: monitor refresh interval; values below 30 seconds are raised to 30 seconds.

## Commands

- `/mcstatus server:host:port`
- `/mcplayers server:host:port`
- `/mcip server:host:port`
- `/mcmonitor server:host:port`
- `/mcunmonitor server:host:port`
- `/mcmonitors`

Monitor management requires Manage Server permission.

The bot reports public DNS/IP information and does not attempt to bypass proxies, firewalls, or private backend protections. Player names are limited to the sample returned by the Minecraft server.

## Start

```bash
npm install
npm start
```
