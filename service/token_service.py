import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


def generate_token(partner: str, services: list[str], expire_minutes: int = JWT_EXPIRE_MINUTES) -> Tuple[str, str]:
    token_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "jti": token_id,
        "partner": partner,
        "services": services,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, token_id


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def extract_service_from_path(path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) >= 5:
        service_path = "/".join(parts[:5])
        return service_path
    return path.strip("/")


def check_service_permission(payload: dict, requested_service: str) -> bool:
    authorized_services = payload.get("services", [])
    return requested_service in authorized_services