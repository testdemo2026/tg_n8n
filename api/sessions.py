from dataclasses import dataclass
from secrets import token_hex
from threading import Lock
from time import time
from typing import Dict, Optional

TTL_SECONDS = 600

_sessions: Dict[str, "SmsSession"] = {}
_lock = Lock()


@dataclass
class SmsSession:
    phone_number: str
    captcha_token: str
    verification_id: str
    target: str
    created_at: float


def _purge() -> None:
    now = time()
    expired = [k for k, s in _sessions.items() if now - s.created_at > TTL_SECONDS]
    for key in expired:
        _sessions.pop(key, None)


def create_session(
    phone_number: str, captcha_token: str, verification_id: str, target: str
) -> str:
    session_id = token_hex(8)
    with _lock:
        _purge()
        _sessions[session_id] = SmsSession(
            phone_number=phone_number,
            captcha_token=captcha_token,
            verification_id=verification_id,
            target=target,
            created_at=time(),
        )
    return session_id


def pop_session(session_id: str) -> Optional[SmsSession]:
    with _lock:
        _purge()
        return _sessions.pop(session_id, None)


def get_session(session_id: str) -> Optional[SmsSession]:
    with _lock:
        _purge()
        return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def sessions_for_phone(phone_number: str) -> list:
    with _lock:
        _purge()
        return [
            (sid, s) for sid, s in _sessions.items() if s.phone_number == phone_number
        ]


def delete_sessions_for_phone(phone_number: str) -> None:
    with _lock:
        for sid in [
            sid for sid, s in _sessions.items() if s.phone_number == phone_number
        ]:
            _sessions.pop(sid, None)
