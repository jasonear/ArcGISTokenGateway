from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from service.token_service import verify_token, extract_service_from_path
from service.token_store import get_token, get_token_services
from logger import get_logger

logger = get_logger("auth")

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
        client_ip = request.client.host if request.client else "unknown"

        # Check if request needs authentication
        if self._should_bypass(path):
            return await call_next(request)

        # 支持大小写不敏感的路径匹配
        if path_lower.startswith("/arcgis/"):
            token = self._extract_token(request)

            if not token:
                logger.warning("认证失败: 缺少 Token | 路径: %s | 来源: %s", path, client_ip)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token is required"}
                )

            payload = verify_token(token)
            if not payload:
                logger.warning("认证失败: Token 无效或已过期 | 路径: %s | 来源: %s", path, client_ip)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token"}
                )

            # Check if token has been revoked & get services from store
            token_id = payload.get("jti")
            partner = payload.get("partner", "unknown")
            if token_id:
                token_record = get_token(token_id)
                if token_record and token_record.get("status") == "revoked":
                    logger.warning("认证失败: Token 已撤销 | Token ID: %s | 路径: %s | 来源: %s", token_id, path, client_ip)
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
                logger.warning(
                    "授权失败: 服务未在 Token 授权范围 | Token ID: %s | 请求服务: %s | 路径: %s | 来源: %s",
                    token_id, requested_service, path, client_ip,
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Service not authorized in token"}
                )

            logger.info("认证通过 | 合作方: %s | Token ID: %s | %s %s | 来源: %s", partner, token_id, request.method, path, client_ip)

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