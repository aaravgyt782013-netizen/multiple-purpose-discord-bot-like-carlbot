# Aarav All-In-One Discord Bot v3

A modern Discord.js v14 multipurpose bot foundation inspired by the feature categories of Carl-bot, MEE6, R.O.T.I and Saphire. It is original code and does not copy their proprietary source.

## Included
- 100 slash-command registrations
- 220 prefix/client command names
- Moderation: kick, ban, timeout, warn, purge, lock and slowmode
- Utility: help, info, avatar, server info, calculator, dice, coinflip, 8ball
- Economy: balance, daily, work
- Community/XP: level, rank, leaderboard registry
- SQLite persistence
- Development guild command registration
- Environment-based secrets; never commit your bot token

## Setup
1. `cd v3`
2. `npm install`
3. Copy `.env.example` to `.env`
4. Put your Discord **bot token** in `DISCORD_TOKEN`.
5. Put the application/client ID in `CLIENT_ID`.
6. Optional: set `DEV_GUILD_ID` for instant development command updates.
7. Enable **Message Content Intent** and **Server Members Intent** in the Discord Developer Portal when using the prefix/welcome features.
8. Run `npm start`.

The remaining feature families are intentionally organized behind the same command router so they can be expanded module-by-module without replacing the bot architecture.
