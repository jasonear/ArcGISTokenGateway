from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from middleware.auth_middleware import AuthMiddleware
from service.proxy_service import forward_request
from config import HOST, PORT
from logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArcGIS Token Gateway 启动完成，监听 %s:%s", HOST, PORT)
    yield
    logger.info("ArcGIS Token Gateway 已停止")


app = FastAPI(
    title="ArcGIS Token Gateway",
    description="JWT Token authentication gateway for ArcGIS map services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health_check():
    logger.debug("健康检查请求")
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def arcgis_proxy(request: Request, path: str):
    # Catch-all 路由，仅处理以 /arcgis 开头的路径（大小写不敏感）
    if not path.lower().startswith("arcgis"):
        logger.warning("访问了未知路径 /%s，返回 404，来源: %s", path, request.client.host if request.client else "unknown")
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )
    return await forward_request(request)


if __name__ == "__main__":
    import os
    import uvicorn
    from logger import make_uvicorn_log_config
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        # 默认开启热重载便于开发；生产环境通过环境变量 RELOAD=false 关闭
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_config=make_uvicorn_log_config(),  # 让 uvicorn 日志同步写入 log/ 文件夹
    )