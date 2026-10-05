import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from .config import Settings

_lock = Lock()


def load_tokens(settings: Settings) -> Dict[str, Any]:
    path = Path(settings.token_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_tokens(settings: Settings, tokens: Dict[str, Any]) -> None:
    cleaned = {k: v for k, v in tokens.items() if v not in (None, "")}
    if not cleaned:
        return
    path = Path(settings.token_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        existing = load_tokens(settings)
        existing.update(cleaned)
        path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
