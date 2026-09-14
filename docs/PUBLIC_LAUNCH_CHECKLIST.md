# LightCore Public Launch Checklist

## Required environment variables

```text
BOT_TOKEN=
CLIENT_ID=
LAVALINK_URI=
LAVALINK_PASSWORD=
LAVALINK_NAME=primary
SUPPORT_SERVER_URL=
PRIVACY_POLICY_URL=
TERMS_URL=
INVITE_URL=
```

## Music hosting

LightCore now uses Wavelink 3 + Lavalink v4. The Discord bot service and Lavalink service should be treated as separate services in production. The bot connects to Lavalink at startup and logs a clear failure if the node cannot be reached.

The bot host checks for an FFmpeg binary in PATH for diagnostics. Local FFmpeg is not used for Lavalink playback; decoding is performed by the Lavalink server.

## Render

Keep LightCore as the Render Web Service. Start it with `python main.py`. The existing health server listens on `0.0.0.0:$PORT` and exposes `/health`.

Run Lavalink as a separate Java 17+ service/container and set `LAVALINK_URI` and `LAVALINK_PASSWORD` on the LightCore service.

## Public application settings

In Discord Developer Portal, enable the bot as public and configure the install link. Discord's application object supports Terms of Service and Privacy Policy URLs, but those application metadata values are not automatically changed by a GitHub code commit. Set them manually to the public URLs for `docs/PRIVACY_POLICY.md` and `docs/TERMS_OF_SERVICE.md` (preferably hosted on a stable HTTPS documentation site).

Also add the final support server URL and invite URL to the environment variables so `/about` and `/invite` can display them.

## Verification / scale

Discord currently requires app verification to scale beyond 100 servers. Apps can begin the verification process from 76 servers. Privileged intents have their own application/review requirements at scale. Plan verification before LightCore approaches that threshold.

## Current limitation

The repository can be statically validated and CI can check Python syntax, imports, dependencies, database initialization, and FFmpeg availability. A real `.play` end-to-end audio test still requires a running Lavalink v4 node, valid bot credentials, a Discord voice channel, and a live server. Do not mark music as end-to-end verified until that live test succeeds.
