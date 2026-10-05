from typing import Any, Dict, List, Optional

_PLACEHOLDERS = {"string", "null", "none", "undefined", "n/a"}


def _is_placeholder(value: str) -> bool:
    text = value.strip()
    return text == "" or text.lower() in _PLACEHOLDERS


def find_url(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data if data.startswith("http") else None
    if isinstance(data, dict):
        for value in data.values():
            found = find_url(value)
            if found:
                return found
    if isinstance(data, (list, tuple)):
        for item in data:
            found = find_url(item)
            if found:
                return found
    return None


def coerce_parent_id(value: Any) -> Any:
    """服务端要求 ID 为字符串；0 表示根目录。"""
    if value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return None if int(value) == 0 else str(int(value))
    if isinstance(value, str):
        if value == "*":
            return value
        if _is_placeholder(value) or value.strip() == "0":
            return None
    return value


def coerce_file_ids(values: Optional[List[Any]]) -> List[Any]:
    """统一把文件 ID 列表里的数字转成字符串，并丢弃 Swagger 占位值。"""
    result: List[Any] = []
    for value in values or []:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            if int(value) == 0:
                continue
            result.append(str(int(value)))
        elif isinstance(value, str):
            if _is_placeholder(value):
                continue
            result.append(value)
    return result


def decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """仅解码 JWT 的 payload（不校验签名），用于读取服务端返回的信息。"""
    import base64
    import json

    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data if isinstance(data, dict) else None
    except (IndexError, ValueError):
        return None
