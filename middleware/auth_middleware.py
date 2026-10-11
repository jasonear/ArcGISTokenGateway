from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from service.token_service import verify_token, extract_service_from_path, check_service_permission
from service.token_store import get_token


BYPASS_PATHS = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/generate_token",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Check if request needs authentication
        if self._should_bypass(path):
            return await call_next(request)

        if path.startswith("/ArcGIS/"):
            token = self._extract_token(request)

            if not token:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token is required"}
                )

            payload = verify_token(token)
            if not payload:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token"}
                )

            # Check if token has been revoked
            token_id = payload.get("jti")
            if token_id:
                token_record = get_token(token_id)
                if token_record and token_record.get("status") == "revoked":
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token has been revoked"}
                    )

            requested_service = extract_service_from_path(path)
            if not check_service_permission(payload, requested_service):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Service not authorized in token"}
                )

        response = await call_next(request)
        return response

    def _should_bypass(self, path: str) -> bool:
        return path in BYPASS_PATHS

    def _extract_token(self, request: Request) -> str | None:
        # Try Authorization header first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        # Try query parameter
        token = request.query_params.get("token")
        if token:
            return token

        return None