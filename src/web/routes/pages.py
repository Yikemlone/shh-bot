import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from web.state import templates, broadcast, WEBSOCKET_CLIENTS, get_user_id
from web.auth import APP_URL

router = APIRouter()


@router.get("/")
async def kanban_page(request: Request):
    user_id = get_user_id(request)
    user_name = None
    if user_id:
        user_name = request.cookies.get("user_name")
    return templates.TemplateResponse(
        request, "kanban.html",
        {
            "request": request,
            "user_id": user_id,
            "user_name": user_name,
            "app_url": APP_URL,
        },
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    WEBSOCKET_CLIENTS.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        WEBSOCKET_CLIENTS.discard(websocket)
