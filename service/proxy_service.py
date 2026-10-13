import httpx
from fastapi import Request
from starlette.responses import Response

from config import ARCGIS_SERVER_URL

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
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params if query_params else None,
                content=body if body else None,
            )

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
            return Response(
                content='{"detail": "Cannot connect to ArcGIS Server"}',
                status_code=502,
                media_type="application/json",
            )
        except httpx.TimeoutException:
            return Response(
                content='{"detail": "ArcGIS Server request timeout"}',
                status_code=504,
                media_type="application/json",
            )
        except Exception as e:
            return Response(
                content='{"detail": "Proxy error: internal server error"}',
                status_code=500,
                media_type="application/json",
            )