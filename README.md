# **Shh! Bot**

## **Summary**

Python version: 3.14.5

This is a bot made for Discord using Discord.py.

Discord bot with voice transcription, LLM task extraction, and a real-time Kanban board.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy `src/.env` and fill in at minimum `BOT_TOKEN`, `WEB_SECRET_KEY`.

### API Keys

| Service | Env Var | Required for |
|---------|---------|-------------|
| Discord Bot | `BOT_TOKEN` | Core |
| Discord OAuth2 | `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` | Kanban login |
| Giphy | `GIF_API_KEY` | GIF commands |
| YouTube | `YOUTUBE_API_KEY` | YouTube commands |
| Spotify | `SPOTIFY_ID`, `SPOTIFY_SECRET` | Spotify commands |
| Gemini | `GEMINI_API_KEY` | LLM fallback (optional) |

## Running

### 1. Web Server (Kanban board)
```bash
python src/web/run.py      # http://localhost:8080
```

### 2. Bot
```bash
python src/bot.py
```

### 3. Ollama (local LLM for task extraction)
```bash
ollama serve                # must be running before starting the bot
ollama pull qwen2.5:7b-instruct-q4_K_M
```

## Usage

- Join VC → `/record` → speak → `/stop`
- Open `http://localhost:8080` to see tasks on the Kanban board
- Tasks sync in real-time via WebSocket

## Commands

| Command | Description |
|---------|-------------|
| `/record` | Start recording voice channel audio |
| `/stop` | Stop, transcribe, and extract tasks |
| `/board` | Show board URL |
| `/tasks` | List stored tasks |
| `/task-add <title>` | Quick-add a task |

## Key Files

| File | What it does |
|------|-------------|
| `src/bot.py` | Bot entry point |
| `src/web/run.py` | Web server entry point |
| `src/services/voice/recorder.py` | Recording, transcription, task extraction pipeline |
| `src/services/api/ollama.py` | Ollama client (task extraction) |
| `src/services/taskstore.py` | JSON-backed task CRUD |
| `src/web/app.py` | FastAPI server (REST + WebSocket) |
| `src/web/static/kanban.js` | Board frontend |
| `data/tasks.json` | Persistent task storage |
| `src/.env` | Config |

## **Music Bot**

If you want the music bot to work you must have [ffmpeg](https://ffmpeg.org/download.html#build-windows) installed on your machine.

You can put the bin files inside this project and direct the bot to it or have it in your system path.

``` python
self.FFMPEG_EXE_PATH = PATH TO FFMPEG
```

## **Resources**

- [Discord.py Docs](https://discordpy.readthedocs.io/en/stable/)
- [Discord.py GitHub](https://github.com/Rapptz/discord.py)
- [Discord Developer Portal](https://discord.com/developers/applications)

## Cloudflared (for Discord Embedded Activity)

```bash
yay -S cloudflared
cloudflared tunnel --url http://localhost:8080
```

Add the generated URL to `DISCORD_REDIRECT_URI` in `.env` and the Discord Developer Portal.
