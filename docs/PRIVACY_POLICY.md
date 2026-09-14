# LightCore Privacy Policy

**Effective date: 2026-09-14**

LightCore is a Discord bot operated by its developer. This policy explains what LightCore stores and why.

## Data LightCore may store

Depending on the features enabled by a server, LightCore may store:

- Discord user, guild, channel, role, and message identifiers needed to operate configured features.
- Economy balances, shop items, pets, rewards, and progression data.
- XP, levels, milestone-role configuration, and temporary XP boosters.
- Moderation warnings and moderation log records, including moderator ID, target ID, reason, and timestamp.
- Ticket metadata and ticket transcripts when ticket features are used.
- Giveaway configuration and entry records.
- Application forms and submitted answers when a server enables applications.
- Temporary voice-channel ownership metadata.
- Server-specific configuration such as log, welcome, ticket, level, and moderation settings.

LightCore is designed to keep these records isolated by Discord guild ID. Data from one guild is not intentionally used as another guild's configuration.

## How data is used

Data is used only to provide the bot features requested by a server, maintain feature state across restarts, prevent abuse, and diagnose failures.

LightCore does not intentionally sell user data or use stored Discord IDs for advertising profiles.

## Retention and deletion

Server administrators can request deletion of LightCore's stored data for their server from the bot operator. Individual users can also ask a server administrator to request removal of user-specific LightCore records. Some Discord audit/log information may remain in Discord itself and is outside LightCore's database.

## Third parties

LightCore connects to Discord to provide bot functionality. Music requests may be processed by the configured Lavalink server and its configured media-source plugins. Do not configure LightCore with a Lavalink provider you do not trust.

## Security

Bot tokens, Lavalink passwords, and other secrets must never be placed in source code or GitHub. They belong in the host's private environment variables.

## Changes

This policy may be updated when LightCore's stored data or features materially change.

## Contact

For privacy questions, contact the LightCore operator through the configured support server.
