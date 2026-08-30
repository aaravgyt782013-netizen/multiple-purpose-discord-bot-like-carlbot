# Aarav All-In-One Discord Bot

A modular Discord.js v14 bot designed as an original all-in-one community, moderation, support, applications, logging, leveling, utility, announcement, embed, TTS and music-control platform.

## Core modules
- Moderation and AutoMod
- Configurable event logging
- Multi-category tickets with staff roles, claims, intake questions and HTML transcripts
- Configurable applications with modal questions and accept/deny/hold workflow
- Interactive embed creator
- Interactive help/category navigation
- Announcements with selected channel and selected mention target
- XP/leveling and leaderboards
- Economy/community utilities
- Music queue/control architecture
- TTS command architecture
- Giveaways and community events architecture
- Custom commands and server settings

## Render
This service exposes `/health` and binds to `0.0.0.0:$PORT`, which is compatible with Render web services. Set secrets in Render Environment Variables rather than committing them. Render's default filesystem is ephemeral, so production deployments should use PostgreSQL (DATABASE_URL) or a persistent disk for state/transcripts. See Render's docs for environment variables and persistent storage.

Required:
- DISCORD_TOKEN
- CLIENT_ID
- PREFIX (optional, defaults to .)
- DEV_GUILD_ID (optional)
- DATABASE_URL (recommended for production)

Never commit `.env` or a bot token.

## Important
Feature families are implemented as original modules. The project does not copy proprietary source code from other bots.
