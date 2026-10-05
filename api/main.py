from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from guangyaclient import FILE_TYPE, FILE_TYPE_NAME, __version__

from .client import PersistentGuangyaClient
from .config import get_settings
from .dependencies import persist_tokens, verify_api_key
from .routers import auth, cloud, files, share
from .token_store import load_tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    tokens = load_tokens(settings)
    client = PersistentGuangyaClient(
        on_change=lambda c: persist_tokens(c, settings),
        access_token=tokens.get("access_token") or settings.access_token or None,
        refresh_token=tokens.get("refresh_token") or settings.refresh_token or None,
        device_id=tokens.get("device_id") or settings.device_id or None,
    )
    if tokens.get("expires_at"):
        try:
            client.token_expires_at = float(tokens["expires_at"])
        except (TypeError, ValueError):
            pass

    app.state.settings = settings
    app.state.client = client
    persist_tokens(client, settings)
    client.sync_snapshot()
    try:
        yield
    finally:
        client.close()


app = FastAPI(
    title="光鸭云盘 API",
    description="基于 guangyaclient 的光鸭云盘文件操作 HTTP 接口",
    version=__version__,
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(cloud.router)
app.include_router(share.router)


@app.get("/", tags=["meta"], summary="服务信息")
def index():
    return {"name": "guangyaclient-api", "version": __version__}


@app.get("/health", tags=["meta"], summary="健康检查")
def health():
    return {"status": "ok"}


@app.get("/meta/file-types", tags=["meta"], summary="文件类型常量")
def file_types():
    return {"type": FILE_TYPE, "name": FILE_TYPE_NAME}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
        log_level=settings.log_level,
    )
