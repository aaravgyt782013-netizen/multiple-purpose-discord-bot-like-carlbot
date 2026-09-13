# All-in-One Discord Bot

A large, original all-in-one Discord bot inspired by the feature categories of popular server-management bots.

## Feature modules
- 🛡️ **Moderation:** kick, ban, unban, timeout, warn, warning history, purge, lock/unlock, slowmode, nickname, lockdown
- 📜 **Server logging:** joins, leaves, deleted/edited messages, channels, roles, bans and moderation actions
- 📈 **Leveling:** XP from chat, level-up messages, leaderboard and admin XP control
- 💰 **Economy:** balance, daily, work, bank deposit/withdraw, pay and rob
- 🎨 **Embeds:** custom title/description embeds, announcements and polls
- 🎫 **Tickets:** private ticket creation, ticket category setup and close button
- 🛠️ **Utility:** server/user/avatar/role/channel information, invite and bot stats
- 🎉 **Fun:** 8ball, coinflip, dice, choose and polls
- 👋 **Welcome:** configurable channel/message with `{user}` and `{server}` placeholders
- 🤖 **Autorole:** automatically assign a configured role to new members
- 📝 **Applications:** configurable review channel and application settings
- 🎵 **Music:** play URL, queue, skip, stop and leave voice
- 🤖 **AutoMod:** invite, link, caps and basic spam protection
- ⚙️ **Server settings:** per-server configuration and command enable/disable
- 💾 **Persistence:** local JSON database that is created automatically

## Setup

1. Create a Discord application and bot in the Discord Developer Portal.
2. Set `DISCORD_TOKEN` and `CLIENT_ID` in your host environment.
3. Optionally set `GUILD_ID` for instant command registration in a test server.
4. Run `npm install` and then `npm start`.

## Environment variables

```env
DISCORD_TOKEN=your_bot_token
CLIENT_ID=your_application_id
GUILD_ID=optional_test_server_id
PREFIX=!
OWNER_ID=your_discord_user_id
```

## Required intents

Enable **Message Content**, **Server Members**, and **Voice State** intents in the Discord Developer Portal. Give the bot the permissions required by the features you enable.

> This project uses its own implementation and does not copy proprietary source code from Carl-bot, R.O.T.I. or other bots.
