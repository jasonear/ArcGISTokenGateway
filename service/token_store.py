import json
import os
from datetime import datetime, timezone
from typing import Optional

TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tokens.json")


def _load_tokens() -> dict:
    if not os.path.exists(TOKENS_FILE):
        return {"tokens": []}
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"tokens": []}


def _save_tokens(data: dict) -> None:
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_token_record(token_id: str, partner: str, services: list[str], expire_at: str) -> None:
    data = _load_tokens()
    record = {
        "token_id": token_id,
        "partner": partner,
        "services": services,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expire_at": expire_at,
        "status": "active",
    }
    data["tokens"].append(record)
    _save_tokens(data)


def list_tokens() -> list[dict]:
    data = _load_tokens()
    return data.get("tokens", [])


def get_token(token_id: str) -> Optional[dict]:
    data = _load_tokens()
    for token in data.get("tokens", []):
        if token["token_id"] == token_id:
            return token
    return None


def delete_token(token_id: str) -> bool:
    data = _load_tokens()
    for token in data.get("tokens", []):
        if token["token_id"] == token_id:
            token["status"] = "revoked"
            _save_tokens(data)
            return True
    return False


def add_service_to_token(token_id: str, service: str) -> dict | None:
    """为指定 Token 增加可访问的服务，返回更新后的记录"""
    data = _load_tokens()
    for token in data.get("tokens", []):
        if token["token_id"] == token_id:
            if service not in token.get("services", []):
                token.setdefault("services", []).append(service)
            _save_tokens(data)
            return token
    return None


def get_token_services(token_id: str) -> list[str]:
    """从持久化存储中获取 Token 授权的服务列表"""
    token = get_token(token_id)
    if not token:
        return []
    return token.get("services", [])