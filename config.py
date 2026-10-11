# 简化配置，使用默认值
# 生产环境建议通过环境变量覆盖

import os

ARCGIS_SERVER_URL = os.getenv("ARCGIS_SERVER_URL", "http://localhost:6080")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 120  # 默认 2 小时

HOST = "0.0.0.0"
PORT = 8000