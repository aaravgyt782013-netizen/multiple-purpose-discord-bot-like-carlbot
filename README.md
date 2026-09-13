# All-in-One Discord Bot

A single Discord bot combining the core style of Carl-bot/R.O.T.I.-type utility bots.

## Included
- Moderation: kick, ban, unban, timeout, warn, warnings, purge, lock, unlock, slowmode, nickname
- Auto moderation: links, Discord invites, caps and basic spam protection
- Logging: member joins/leaves, deleted messages and moderation actions
- Welcome system with `{user}` and `{server}` placeholders
- Autorole
- Server lockdown/unlockdown
- Private support tickets
- Utility: server/user/avatar/role/channel info, invite, stats
- Fun: 8ball, coinflip, dice, choose, poll, say and announce
- Per-server command enable/disable settings
- Persistent JSON configuration in `data/guilds.json`
- Slash-command based, Discord.js v14

## Setup

1. Create a Discord application and bot at the Discord Developer Portal.
2. Put `DISCORD_TOKEN`, `CLIENT_ID`, and optionally `GUILD_ID` in your hosting environment.
3. Install dependencies with `npm install`.
4. Start with `npm start`.

For development, set `GUILD_ID` to a test server so slash commands register there immediately. Without it, commands are registered globally and can take time to propagate.

## Required bot permissions/intents

Enable the **Message Content Intent** and **Server Members Intent** in the Developer Portal. Invite the bot with the permissions needed for the moderation features you want to use.

## Notes

This is the foundation for a larger all-in-one bot. Features are intentionally implemented without copying proprietary source code from Carl-bot, R.O.T.I. or other bots.
