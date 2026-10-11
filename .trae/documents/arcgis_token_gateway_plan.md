# ArcGIS Token Gateway - 实施方案

## 一、项目概述

基于 Python + FastAPI 构建 ArcGIS 地图服务的 Token 认证网关，采用**反向代理模式**，所有外部合作伙伴访问地图服务必须携带有效 JWT Token，Token 中包含该合作伙伴被授权访问的服务列表。

### 核心架构
```
外部合作伙伴请求 --> FastAPI 网关 --> ArcGIS Server
                        │
                        ├─ JWT Token 验证
                        ├─ Token 授权服务列表校验
                        └─ 请求转发 + 响应返回
```

### 使用流程
```
1. 管理员使用命令行工具为合作伙伴生成 Token（指定可访问的服务列表）
2. 将 Token 分发给合作伙伴
3. 合作伙伴在访问地图服务时携带 Token
4. 网关验证 Token 并校验服务权限
5. 通过则转发请求到 ArcGIS Server
```

### 技术决策总结
| 项目 | 决策 |
|------|------|
| 架构模式 | 反向代理模式 |
| Token 机制 | JWT Token（独立颁发，不依赖 ArcGIS 原生 Token） |
| Token ID 格式 | UUID（每个 Token 拥有唯一的 jti 标识） |
| 权限控制粒度 | 服务级别（控制到 MapServer/ImageServer 等） |
| Token 生成方式 | 管理员通过命令行工具手动生成 |
| 全局白名单 | 不需要，以 Token 授权为准 |
| Token 有效期 | 2 小时 |
| Token 记录存储 | JSON 文件（记录生成的 Token 信息，支持查看和删除） |
| 目标用户 | 外部合作伙伴 |
| ArcGIS 当前状态 | 未启用认证 |

---

## 二、当前状态分析

- 项目目录 `d:\ai_work\trae\arcgisToken` 为空
- 需要从零搭建完整的 FastAPI 项目结构
- ArcGIS Server 已部署，地图服务可用，但目前开放访问

---

## 三、项目结构

```
arcgisToken/
├── main.py                 # FastAPI 应用入口
├── config.py               # 配置管理（ArcGIS地址、JWT密钥等）
├── requirements.txt        # Python 依赖
├── generate_token.py       # 管理员命令行工具 - 生成/查看/删除 Token
├── tokens.json             # Token 记录存储文件（自动生成）
├── service/
│   ├── token_service.py    # JWT Token 生成与验证服务
│   ├── token_store.py      # Token 记录存储管理
│   └── proxy_service.py    # 反向代理服务
└── middleware/
    └── auth_middleware.py  # 认证中间件
```

---

## 四、详细实施步骤

### 步骤 1: 配置管理 (`config.py`)

**文件**: `config.py`

**功能**: 集中管理所有配置项

**配置项**:
- `ARCGIS_SERVER_URL`: ArcGIS Server 基础地址，如 `http://192.168.1.100:6080`
- `JWT_SECRET_KEY`: JWT 签名密钥（使用强随机字符串）
- `JWT_ALGORITHM`: 签名算法，固定为 `HS256`
- `JWT_EXPIRE_MINUTES`: Token 过期时间，默认 `120` 分钟

**实现要点**:
- 支持环境变量覆盖配置（生产环境安全）
- 提供配置校验，确保必要配置项存在

---

### 步骤 2: Token 验证服务 (`service/token_service.py`)

**文件**: `service/token_service.py`

**功能**: JWT Token 的生成、验证和权限校验

**核心函数**:

1. **`generate_token(partner: str, services: list[str], expire_minutes: int = JWT_EXPIRE_MINUTES) -> tuple[str, str]`**
   - 生成 JWT Token
   - 生成 UUID 作为 Token 唯一标识（jti）
   - Payload 包含: `exp`(过期时间), `iat`(签发时间), `jti`(UUID), `services`(授权服务列表), `partner`(合作伙伴名称)
   - 返回 (token_string, uuid_string)

2. **`verify_token(token: str) -> dict | None`**
   - 验证 Token 有效性（签名 + 过期时间）
   - 返回解析后的 Payload，无效则返回 None
   - Payload 结构: `{"exp": xxx, "iat": xxx, "jti": "uuid", "services": ["service1", "service2"], "partner": "xxx"}`

3. **`extract_service_from_path(path: str) -> str`**
   - 从请求路径提取服务标识
   - 如 `/ArcGIS/rest/services/TestMap/MapServer/query` → `ArcGIS/rest/services/TestMap/MapServer`

4. **`check_service_permission(payload: dict, requested_service: str) -> bool`**
   - 校验请求的服务是否在 Token 授权的 services 列表中
   - 精确匹配

**依赖**: `pyjwt`, `uuid`

---

### 步骤 3: Token 存储服务 (`service/token_store.py`)

**文件**: `service/token_store.py`

**功能**: Token 记录的 JSON 文件存储管理

**核心函数**:

1. **`save_token_record(token_id: str, token: str, partner: str, services: list[str], expire_at: str) -> None`**
   - 将 Token 记录保存到 tokens.json 文件
   - 记录包含: token_id, partner, services, created_at, expire_at, status(active/revoked)
   - 如果文件不存在则自动创建

2. **`list_tokens() -> list[dict]`**
   - 读取并返回所有 Token 记录列表
   - 包含每个 Token 的基本信息、状态、过期时间

3. **`delete_token(token_id: str) -> bool`**
   - 根据 Token ID 删除记录（标记为 revoked）
   - 返回操作是否成功

4. **`get_token(token_id: str) -> dict | None`**
   - 根据 Token ID 获取单条记录

**JSON 文件格式**:
```json
{
  "tokens": [
    {
      "token_id": "550e8400-e29b-41d4-a716-446655440000",
      "partner": "PartnerA",
      "services": ["ArcGIS/rest/services/TestMap/MapServer"],
      "created_at": "2024-10-11T14:00:00",
      "expire_at": "2024-10-11T16:00:00",
      "status": "active"
    }
  ]
}
```

---

### 步骤 4: 认证中间件 (`middleware/auth_middleware.py`)

**文件**: `middleware/auth_middleware.py`

**功能**: 请求级别的 Token 验证和服务权限校验

**处理流程**:
```
1. 检查请求路径是否以 /ArcGIS/ 开头
2. 如果是，则进行 Token 验证
3. 从请求中提取 Token（优先 Header Authorization: Bearer xxx，其次 Query ?token=xxx）
4. 验证 Token 有效性
5. 校验请求的服务在 Token 授权范围内
6. 通过则放行，失败返回 401/403
```

**豁免路径**（不需要 Token）:
- `/generate_token` (命令行工具使用的接口)
- `/docs`, `/redoc`, `/openapi.json` (API 文档)
- `/health` (健康检查)

**错误响应**:
- 401: Token 无效或过期 `{"detail": "Invalid or expired token"}`
- 403: 无权访问该服务 `{"detail": "Service not authorized in token"}`

---

### 步骤 6: 反向代理服务 (`service/proxy_service.py`)

**文件**: `service/proxy_service.py`

**功能**: 将验证通过的请求转发到 ArcGIS Server

**核心实现**:

1. **`forward_request(request: Request) -> Response`**
   - 使用 `httpx.AsyncClient` 异步转发请求
   - 保留原始请求的所有属性:
     - HTTP 方法 (GET/POST)
     - Headers (移除 Host、Authorization，更新为目标服务器)
     - Query 参数 (移除 token 参数)
     - Request Body
   - 返回 ArcGIS Server 的原始响应（保持状态码和 Content-Type）

2. **请求转换逻辑**:
   ```
   原始请求: /ArcGIS/rest/services/xx/MapServer/query?f=json
   转发请求: http://arcgis-server:6080/ArcGIS/rest/services/xx/MapServer/query?f=json
   ```

**实现要点**:
- 使用 `httpx` 异步客户端，保持高性能
- 超时设置: 60 秒（地图查询、导出可能较慢）
- 错误处理: 网络异常、超时、5xx 错误统一处理
- 清除敏感 Header（Authorization、token 参数），避免泄露

---

### 步骤 5: Token 生成与管理工具 (`generate_token.py`)

**文件**: `generate_token.py`

**功能**: 管理员命令行工具，用于生成、查看、删除 Token

**使用方式**:

```bash
# 生成 Token（基本用法）
python generate_token.py --partner "PartnerA" --services "ArcGIS/rest/services/TestMap/MapServer"

# 为多个服务生成 Token
python generate_token.py --partner "PartnerB" --services "ArcGIS/rest/services/Map1/MapServer" "ArcGIS/rest/services/Map2/MapServer"

# 自定义过期时间（小时）
python generate_token.py --partner "PartnerC" --services "ArcGIS/rest/services/TestMap/MapServer" --hours 4

# 查看已生成的 Token 列表
python generate_token.py --list

# 删除指定 Token
python generate_token.py --delete "550e8400-e29b-41d4-a716-446655440000"
```

**核心实现**:

1. **生成 Token**
   - 调用 `token_service.generate_token()` 生成 JWT Token
   - 自动生成 UUID 作为 Token ID
   - 调用 `token_store.save_token_record()` 保存记录到 tokens.json
   - 输出 Token、Token ID、过期时间等信息

2. **查看 Token 列表**
   - 调用 `token_store.list_tokens()` 读取所有 Token 记录
   - 格式化输出：Token ID、合作伙伴、授权服务、创建时间、过期时间、状态

3. **删除 Token**
   - 调用 `token_store.delete_token(token_id)` 标记为 revoked
   - 删除后 Token 立即失效

4. **命令行参数解析**:
   - `--partner`: 合作伙伴名称（生成 Token 时必填）
   - `--services`: 授权服务列表（生成 Token 时必填，可多个）
   - `--hours`: 过期时间，默认 2 小时
   - `--list`: 查看所有 Token 记录
   - `--delete`: 删除指定 Token（需传入 Token ID）

**列表输出示例**:
```
Token 列表:
================================================================================
Token ID: 550e8400-e29b-41d4-a716-446655440000
合作伙伴: PartnerA
授权服务: ArcGIS/rest/services/TestMap/MapServer
创建时间: 2024-10-11 14:00:00
过期时间: 2024-10-11 16:00:00
状态: active

Token ID: 660e8400-e29b-41d4-a716-446655440001
合作伙伴: PartnerB
授权服务: ArcGIS/rest/services/Map1/MapServer, ArcGIS/rest/services/Map2/MapServer
创建时间: 2024-10-11 15:00:00
过期时间: 2024-10-11 17:00:00
状态: revoked
================================================================================
总计: 2 个 Token
```

---

### 步骤 6: 应用入口 (`main.py`)

**文件**: `main.py`

**功能**: FastAPI 应用组装、路由定义、中间件注册

**路由定义**:

1. **`GET /health`** - 健康检查
   - Response: `{"status": "ok", "timestamp": "..."}`

2. **`/ArcGIS/**`** - 反向代理捕获路由
   - 所有匹配 `/ArcGIS/` 开头的请求进入代理逻辑
   - 自动经过认证中间件
   - 验证通过后转发到 ArcGIS Server

**中间件注册**:
- 注册 `auth_middleware` 为全局中间件

**启动配置**:
- uvicorn 启动，支持 host/port 配置
- 默认端口: 8000

---

### 步骤 7: 依赖管理 (`requirements.txt`)

**文件**: `requirements.txt`

**依赖列表**:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pyjwt>=2.8.0
httpx>=0.25.0
python-multipart>=0.0.6
pydantic>=2.5.0
```

---

## 五、安全考量

1. **JWT 密钥管理**
   - 生产环境必须通过环境变量传入 `JWT_SECRET_KEY`
   - 使用 256 位随机字符串作为密钥
   - 密钥不得提交到代码仓库
   - 定期轮换密钥

2. **Token 安全**
   - Token 设置 2 小时过期（可配置）
   - Token 中包含授权服务列表，实现最小权限原则
   - 转发请求时清除 Token，避免泄露到 ArcGIS Server
   - 不支持 Token 刷新机制（过期由管理员重新生成）

3. **权限控制**
   - Token 中明确指定可访问的服务列表
   - 精确匹配服务路径，不支持通配符（避免过度授权）
   - 每个合作伙伴独立 Token，便于追踪和管理

4. **请求安全**
   - 限制请求体大小（防止大请求攻击）
   - 设置合理的超时时间
   - 记录访问日志用于审计（合作伙伴、访问的服务、时间）

---

## 六、使用示例

### 1. 管理员生成 Token

**为 PartnerA 生成 Token，授权访问 TestMap 服务**:
```bash
python generate_token.py --partner "PartnerA" --services "ArcGIS/rest/services/TestMap/MapServer"
```

**为 PartnerB 生成 Token，授权访问多个服务**:
```bash
python generate_token.py --partner "PartnerB" \
  --services "ArcGIS/rest/services/Map1/MapServer" "ArcGIS/rest/services/Image1/ImageServer"
```

**输出**:
```
Token 生成成功!
合作伙伴: PartnerA
授权服务: ArcGIS/rest/services/TestMap/MapServer
过期时间: 2024-10-11 16:00:00

Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. 合作伙伴使用 Token 访问地图服务

**方式一: Header 传递（推荐）**
```bash
curl http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  --data-urlencode "where=1=1" \
  --data-urlencode "f=json"
```

**方式二: Query 参数传递（兼容 ArcGIS API）**
```bash
curl "http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query?token=eyJhbGciOiJIUzI1NiIs...&where=1=1&f=json"
```

### 3. 前端集成示例

**ArcGIS API for JavaScript**:
```javascript
// 设置 Token
esriConfig.tokenService.urlTemplates.arcgis = false;

const session = new Session({
  token: "eyJhbGciOiJIUzI1NiIs..."  // 从后端获取的 Token
});

// 创建地图服务图层
const layer = new MapImageLayer({
  url: "http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer",
  authentication: session
});
```

**通用 Fetch 示例**:
```javascript
// 使用 Token 访问地图服务
const response = await fetch(
  'http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query?where=1=1&f=json',
  {
    headers: {
      'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIs...'
    }
  }
);
const data = await response.json();
```

### 4. 错误响应示例

**无 Token**:
```json
{"detail": "Token is required"}
```

**Token 过期**:
```json
{"detail": "Invalid or expired token"}
```

**无权访问该服务**:
```json
{"detail": "Service not authorized in token"}
```

---

## 七、配置示例

### `.env` 文件 (生产环境)
```env
# ArcGIS Server 配置
ARCGIS_SERVER_URL=http://192.168.1.100:6080

# JWT 配置
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 生成强随机密钥
```bash
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

# Python
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 八、部署指南

### 开发环境
```bash
# 1. 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建 .env 配置文件
copy .env.example .env
# 编辑 .env 填入配置

# 4. 启动服务
uvicorn main:app --reload --port 8000
```

### 生产环境 (推荐)

**使用 systemd (Linux)**:
```ini
# /etc/systemd/system/arcgis-gateway.service
[Unit]
Description=ArcGIS Token Gateway
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/arcgis-gateway
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/arcgis-gateway/.env
ExecStart=/opt/arcgis-gateway/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

**使用 Docker**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 九、验证与测试

### 验证步骤

1. **启动服务**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **测试 Token 生成**
   ```bash
   python generate_token.py --partner "TestPartner" --services "ArcGIS/rest/services/TestMap/MapServer"
   ```

3. **测试无 Token 访问**
   ```bash
   # 应返回 401
   curl http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer
   ```

4. **测试有效 Token 访问**
   ```bash
   # 应成功返回地图服务信息
   curl http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

5. **测试 Token 访问未授权服务**
   ```bash
   # 应返回 403
   curl http://localhost:8000/ArcGIS/rest/services/OtherMap/MapServer \
     -H "Authorization: Bearer YOUR_TOKEN"  # Token 只授权了 TestMap
   ```

6. **测试 Token 过期**
   - 生成一个 1 分钟过期的 Token
   - 等待过期后访问，应返回 401

7. **测试 Query 参数 Token**
   ```bash
   # 应成功返回地图服务信息
   curl "http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer?token=YOUR_TOKEN"
   ```

---

## 十、合作伙伴管理流程

### Token 生命周期管理

1. **新合作伙伴接入**
   - 确定需要访问的服务列表
   - 运行 `generate_token.py` 生成 Token
   - 通过安全渠道将 Token 发给合作伙伴
   - 记录 Token 的合作伙伴、授权服务、生成时间

2. **Token 续期**
   - Token 过期后，合作伙伴无法访问
   - 管理员重新运行 `generate_token.py` 生成新 Token
   - 通知合作伙伴更新 Token

3. **权限变更**
   - 需要修改授权服务时，生成新的 Token
   - 旧 Token 在过期前仍然有效（原有权限）
   - 建议旧 Token 到期后立即失效

4. **Token 撤销**
   - 如需立即撤销，更改 JWT_SECRET_KEY（会影响所有 Token）
   - 或者等待 Token 自然过期
   - （可选）后续可扩展 Token 黑名单机制

---

## 十一、后续扩展建议

1. **Token 黑名单** - 支持主动撤销 Token，不需等待过期
2. **Token 刷新** - 实现 refresh token，减少管理员工作量
3. **访问日志** - 记录所有访问日志，按合作伙伴统计
4. **速率限制** - 防止单个 Token 过度请求
5. **管理 API** - 提供 API 管理 Token，而非命令行
6. **监控告警** - Token 即将过期提醒、异常访问告警
7. **缓存层** - 对高频查询结果缓存，减少 ArcGIS Server 压力

---

## 十二、文件清单

| 文件路径 | 功能 | 状态 |
|---------|------|------|
| `main.py` | FastAPI 应用入口、路由定义 | 待实现 |
| `config.py` | 配置管理 | 待实现 |
| `generate_token.py` | 管理员命令行工具 - 生成 Token | 待实现 |
| `service/token_service.py` | JWT Token 验证服务 | 待实现 |
| `service/proxy_service.py` | 反向代理服务 | 待实现 |
| `middleware/auth_middleware.py` | 认证中间件 | 待实现 |
| `requirements.txt` | Python 依赖 | 待实现 |
| `.env.example` | 配置示例文件 | 待实现 |