import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from web.state import store, BASE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.list_all()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("WEB_SECRET_KEY", "dev-secret-change-in-production"),
)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

from web.routes.pages import router as pages_router
from web.routes.tasks import router as tasks_router
from web.routes.auth_routes import router as auth_router

app.include_router(pages_router)
app.include_router(tasks_router)
app.include_router(auth_router)
