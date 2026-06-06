from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from web.state import get_user_id
from web.auth import discord_login_url, exchange_code, get_user_info, create_session

router = APIRouter()


@router.get("/auth/discord")
async def auth_discord():
    return RedirectResponse(url=discord_login_url())


@router.get("/auth/callback")
async def auth_callback(code: str, request: Request):
    token_data = await exchange_code(code)
    if token_data is None:
        raise HTTPException(status_code=400, detail="Failed to exchange code")
    user = await get_user_info(token_data.get("access_token", ""))
    if user is None:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    user_id = user["id"]
    session_token = create_session(user_id)
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="session",
        value=session_token,
        max_age=86400,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        key="user_name",
        value=user.get("global_name") or user.get("username", "Unknown"),
        max_age=86400,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/auth/me")
async def auth_me(request: Request):
    user_id = get_user_id(request)
    if not user_id:
        return JSONResponse(content={"authenticated": False}, status_code=401)
    return JSONResponse(
        content={
            "authenticated": True,
            "user_id": user_id,
            "user_name": request.cookies.get("user_name"),
        }
    )


@router.get("/auth/logout")
async def auth_logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("session")
    response.delete_cookie("user_name")
    return response
