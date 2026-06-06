from pathlib import Path
from fastapi import WebSocket, Request
from fastapi.templating import Jinja2Templates
from services.taskstore import TaskStore
from web.auth import read_session

store = TaskStore()
WEBSOCKET_CLIENTS: set[WebSocket] = set()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def broadcast(message: dict):
    dead = set()
    for ws in WEBSOCKET_CLIENTS:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    WEBSOCKET_CLIENTS -= dead


def get_user_id(request: Request) -> str | None:
    session = request.cookies.get("session")
    if session:
        return read_session(session)
    return None
