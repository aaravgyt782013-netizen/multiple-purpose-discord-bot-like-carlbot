# Zynrax-inspired Discord Bot

A Discord.js multipurpose bot starter with moderation, utility, and security-monitoring commands.

## Setup

1. Install Node.js 20 or newer.
2. Run `npm install`.
3. Copy `.env.example` to `.env` and configure the Discord bot token and application ID.
4. Register slash commands with `npm run deploy-commands`.
5. Start with `npm start`.

Review permissions and configure each module before using the bot in a live server. The anti-nuke module records and logs selected events; it does not automatically punish users.
