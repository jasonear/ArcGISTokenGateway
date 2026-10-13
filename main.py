from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from middleware.auth_middleware import AuthMiddleware
from service.proxy_service import forward_request
from config import HOST, PORT

app = FastAPI(
    title="ArcGIS Token Gateway",
    description="JWT Token authentication gateway for ArcGIS map services",
    version="1.0.0",
)

app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def arcgis_proxy(request: Request, path: str):
    # Catch-all 路由，仅处理以 /arcgis 开头的路径（大小写不敏感）
    if not path.lower().startswith("arcgis"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )
    return await forward_request(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)