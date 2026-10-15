# 简化配置，使用默认值
# 生产环境建议通过环境变量覆盖

import os
from dotenv import load_dotenv

load_dotenv()

ARCGIS_SERVER_URL = os.getenv("ARCGIS_SERVER_URL", "http://localhost:6080")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = float(os.getenv("JWT_EXPIRE_HOURS", "2"))  # Token 有效期，单位小时
JWT_EXPIRE_MINUTES = int(JWT_EXPIRE_HOURS * 60)  # 下游签发逻辑使用分钟

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))