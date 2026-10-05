from typing import Callable, Optional

from guangyaclient import GuangyaClient


class PersistentGuangyaClient(GuangyaClient):
    """在 token 发生变化时（登录/刷新/401 自动刷新）自动回调持久化。"""

    def __init__(self, on_change: Callable[["PersistentGuangyaClient"], None], **kwargs):
        super().__init__(**kwargs)
        self._on_change = on_change
        self._snapshot = self._state()

    def _state(self):
        return (
            self.token,
            self.refresh_token_value,
            self.device_id,
            self.token_expires_at,
        )

    def _persist_if_changed(self):
        state = self._state()
        if state != self._snapshot:
            self._snapshot = state
            self._on_change(self)

    def sync_snapshot(self):
        self._snapshot = self._state()

    def set_credentials(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        """用 access_token / refresh_token 直接登录（覆盖当前凭据并持久化）。"""
        self.token = access_token or ""
        self._client.headers["authorization"] = f"Bearer {self.token}"
        if refresh_token is not None:
            self.refresh_token_value = refresh_token or None
        if device_id:
            self.device_id = device_id
            self._client.headers["did"] = device_id
        self.token_expires_at = None
        self._persist_if_changed()

    def request(self, *args, **kwargs):
        try:
            return super().request(*args, **kwargs)
        finally:
            self._persist_if_changed()

    def refresh_token(self, refresh_token: Optional[str] = None):
        try:
            return super().refresh_token(refresh_token)
        finally:
            self._persist_if_changed()

    def login_sms_signin(self, *args, **kwargs):
        try:
            return super().login_sms_signin(*args, **kwargs)
        finally:
            self._persist_if_changed()
