from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from guangyaclient import GuangyaClient

from .config import Settings, get_settings
from .token_store import save_tokens


def get_client(request: Request) -> GuangyaClient:
    return request.app.state.client


def get_app_settings() -> Settings:
    return get_settings()


def verify_api_key(
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


def persist_tokens(client: GuangyaClient, settings: Settings) -> None:
    save_tokens(
        settings,
        {
            "access_token": client.token,
            "refresh_token": client.refresh_token_value,
            "device_id": client.device_id,
            "expires_at": client.token_expires_at,
        },
    )


ClientDep = Annotated[GuangyaClient, Depends(get_client)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
