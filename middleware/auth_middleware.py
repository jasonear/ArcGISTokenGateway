from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from service.token_service import verify_token, extract_service_from_path
from service.token_store import get_token, get_token_services


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
        path_lower = path.lower()

        # Check if request needs authentication
        if self._should_bypass(path):
            return await call_next(request)

        # 支持大小写不敏感的路径匹配
        if path_lower.startswith("/arcgis/"):
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

            # Check if token has been revoked & get services from store
            token_id = payload.get("jti")
            if token_id:
                token_record = get_token(token_id)
                if token_record and token_record.get("status") == "revoked":
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token has been revoked"}
                    )

            # 小写化后对比，兼容 arcgis/ArcGIS 等写法
            requested_service = extract_service_from_path(path_lower)
            # 从持久化存储中读取服务权限，支持动态增删
            authorized_services = get_token_services(token_id) if token_id else payload.get("services", [])
            authorized_lower = [s.lower() for s in authorized_services]
            if requested_service not in authorized_lower:
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