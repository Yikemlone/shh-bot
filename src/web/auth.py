import os
import httpx
from itsdangerous import URLSafeTimedSerializer

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "")
APP_URL = os.getenv("APP_URL", "http://localhost:8080")
SECRET_KEY = os.getenv("WEB_SECRET_KEY", "dev-secret-change-in-production")

if not DISCORD_REDIRECT_URI:
    DISCORD_REDIRECT_URI = f"{APP_URL}/auth/callback"

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="discord-auth")

DISCORD_API = "https://discord.com/api/v10"
SCOPE = "identify guilds"


def create_session(user_id: str) -> str:
    return serializer.dumps({"user_id": user_id})


def read_session(token: str, max_age: int = 86400) -> str | None:
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("user_id")
    except Exception:
        return None


def discord_login_url() -> str:
    params = (
        f"client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPE}"
    )
    return f"{DISCORD_API}/oauth2/authorize?{params}"


async def exchange_code(code: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            return None
        return resp.json()


async def get_user_info(access_token: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return None
        return resp.json()
