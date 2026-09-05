from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from accountflow.api.routes.auth import router as auth_router
from accountflow.api.routes.health import router as health_router
from accountflow.api.routes.integrations import router as integrations_router
from accountflow.api.routes.me import router as me_router
from accountflow.api.routes.runs import router as runs_router
from accountflow.api.routes.sows import router as sows_router
from accountflow.core.config import get_settings
from accountflow.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.require_auth_secrets()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AccountFlow OS API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(runs_router)
    app.include_router(sows_router)
    app.include_router(integrations_router)
    return app


app = create_app()
