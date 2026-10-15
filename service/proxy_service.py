import time

import httpx
from fastapi import Request
from starlette.responses import Response

from config import ARCGIS_SERVER_URL
from logger import get_logger

logger = get_logger("proxy")

# 需要过滤的响应头：httpx 已自动解压响应体，需移除长度/压缩/连接相关头
EXCLUDE_HEADERS = {"content-length", "transfer-encoding", "connection", "keep-alive", "content-encoding"}


async def forward_request(request: Request) -> Response:
    # Build target URL
    path = request.url.path
    target_url = f"{ARCGIS_SERVER_URL}{path}"

    # Build query params without token
    query_params = dict(request.query_params)
    query_params.pop("token", None)

    # Build headers without sensitive info
    headers = dict(request.headers)
    headers.pop("authorization", None)
    headers.pop("host", None)

    # Get request body
    body = await request.body()

    # Forward request
    start_time = time.monotonic()
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params if query_params else None,
                content=body if body else None,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "代理请求 %s %s -> %s | 状态码: %s | 耗时: %.0fms",
                request.method, path, target_url, response.status_code, elapsed_ms,
            )
            if response.status_code >= 400:
                logger.warning("上游返回错误状态码 %s | 目标: %s", response.status_code, target_url)

            # 过滤上游响应头，避免长度/编码不匹配
            response_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in EXCLUDE_HEADERS
            }

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )
        except httpx.ConnectError:
            logger.error("无法连接 ArcGIS Server: %s", target_url)
            return Response(
                content='{"detail": "Cannot connect to ArcGIS Server"}',
                status_code=502,
                media_type="application/json",
            )
        except httpx.TimeoutException:
            logger.error("请求 ArcGIS Server 超时: %s", target_url)
            return Response(
                content='{"detail": "ArcGIS Server request timeout"}',
                status_code=504,
                media_type="application/json",
            )
        except Exception as e:
            logger.exception("代理请求发生未预期异常: %s", target_url)
            return Response(
                content='{"detail": "Proxy error: internal server error"}',
                status_code=500,
                media_type="application/json",
            )