# ArcGIS Token Gateway

基于 Python + FastAPI 的 ArcGIS 地图服务 Token 认证网关，采用反向代理模式，所有外部合作伙伴访问地图服务必须携带有效 JWT Token。

## 核心架构

```
外部合作伙伴请求 --> FastAPI 网关 --> ArcGIS Server
                        │
                        ├─ JWT Token 验证
                        ├─ 持久化存储中动态校验服务权限
                        ├─ Token 撤销状态检查
                        └─ 请求转发 + 响应返回
```

## 功能特性

- **JWT Token 认证**：使用 HS256 算法签名，Token 包含合作伙伴信息和授权服务列表
- **UUID Token ID**：每个 Token 拥有唯一的 UUID 标识（jti），便于管理和追踪
- **服务级别权限控制**：每个 Token 精确授权可访问的地图服务
- **动态权限管理**：权限从持久化存储（tokens.json）实时读取，支持不重新签发 Token 即可增删服务
- **反向代理**：透明转发请求到 ArcGIS Server，支持 GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS 全部 HTTP 方法
- **路径大小写不敏感**：`/arcgis/`、`/ArcGIS/`、`/ARCGIS/` 等写法均可正常访问
- **响应头规范化**：自动过滤上游 `Content-Length`、`Content-Encoding` 等头，避免客户端解析异常
- **Token 管理**：命令行工具支持生成、查看、删除 Token，以及为已有 Token 增加服务
- **Token 撤销**：支持即时撤销 Token（标记为 revoked），无需等待过期
- **双方式传 Token**：支持 Authorization Header（推荐）和 Query 参数两种方式
- **灵活配置**：支持环境变量配置，易于部署
- **示例脚本**：提供完整的使用示例和自动化测试脚本

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置

复制配置文件并修改：

```bash
copy .env.example .env
```

编辑 `.env` 文件：

```env
# ArcGIS Server 地址
ARCGIS_SERVER_URL=http://localhost:6080

# JWT 密钥（生产环境必须修改）
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars

# JWT 签名算法
JWT_ALGORITHM=HS256

# Token 有效期（分钟）
JWT_EXPIRE_MINUTES=120

# 服务端口
HOST=0.0.0.0
PORT=8000
```

> **默认配置**：若不提供 `.env` 文件，系统将使用内置默认值。`config.py` 中的默认密钥为 `default-secret-key-change-in-production`，默认有效期 120 分钟。生产环境务必通过环境变量覆盖。

### 3. 启动服务

```bash
uvicorn main:app --reload --port 8000
```

### 4. 生成 Token

```bash
# 为合作伙伴生成 Token
python generate_token.py --partner "PartnerA" --services "ArcGIS/rest/services/TestMap/MapServer"

# 查看 Token 列表
python generate_token.py --list

# 删除 Token（即时撤销）
python generate_token.py --delete "token-id"

# 为已有 Token 增加服务（无需重新签发）
python generate_token.py --add-service "token-id" "ArcGIS/rest/services/NewMap/MapServer"
```

## 使用示例

### 合作伙伴访问地图服务

**方式一：Header 传递（推荐）**

```bash
curl http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --data-urlencode "where=1=1" \
  --data-urlencode "f=json"
```

**方式二：Query 参数传递**

```bash
curl "http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query?token=YOUR_TOKEN&where=1=1&f=json"
```

### 前端集成

```javascript
// 使用 Token 访问地图服务
const response = await fetch(
  'http://localhost:8000/ArcGIS/rest/services/TestMap/MapServer/query?where=1=1&f=json',
  {
    headers: {
      'Authorization': 'Bearer YOUR_TOKEN'
    }
  }
);
const data = await response.json();
```

## 示例脚本

项目提供两个示例脚本，帮助您快速上手：

### `examples/usage_example.py` - 完整功能演示

包含 8 个使用场景演示：

- 生成 JWT Token
- 获取图层信息
- 查询地图要素
- 空间查询（矩形范围）
- 统计查询
- Query 参数传递 Token
- 错误处理示例
- 获取字段信息

**运行方式：**

```bash
python examples/usage_example.py
```

### `examples/quick_test.py` - 自动化测试脚本

包含 7 个测试用例：

- 健康检查
- Token 生成
- 无 Token 访问测试
- 无效 Token 测试
- 有效 Token 访问测试
- Query 参数 Token 测试
- 未授权服务访问测试

**运行方式：**

```bash
python examples/quick_test.py
```

## 命令行工具

### 生成 Token

```bash
# 基本用法
python generate_token.py --partner "PartnerA" --services "ArcGIS/rest/services/TestMap/MapServer"

# 多个服务
python generate_token.py --partner "PartnerB" \
  --services "ArcGIS/rest/services/Map1/MapServer" "ArcGIS/rest/services/Map2/MapServer"

# 自定义过期时间（小时）
python generate_token.py --partner "PartnerC" --services "ArcGIS/rest/services/TestMap/MapServer" --hours 4
```

### 查看 Token 列表

```bash
python generate_token.py --list
```

输出示例：

```
Token 列表:
================================================================================
Token ID: 550e8400-e29b-41d4-a716-446655440000
合作伙伴: PartnerA
授权服务: ArcGIS/rest/services/TestMap/MapServer
创建时间: 2024-10-11 14:00:00
过期时间: 2024-10-11 16:00:00
状态: active

总计: 1 个 Token
```

### 为 Token 增加服务

```bash
python generate_token.py --add-service "550e8400-e29b-41d4-a716-446655440000" "ArcGIS/rest/services/NewMap/MapServer"
```

增加服务后权限立即生效，无需重新签发 Token。

### 删除 Token

```bash
python generate_token.py --delete "550e8400-e29b-41d4-a716-446655440000"
```

删除后 Token 立即失效，访问时返回 401 错误。

## Token 管理

### Token 生命周期

1. **生成**：管理员使用 `generate_token.py` 创建 Token，指定合作伙伴和授权服务
2. **使用**：合作伙伴在请求中携带 Token 访问地图服务
3. **撤销**：管理员可随时删除 Token，立即失效
4. **过期**：Token 超过有效期自动失效

### Token 撤销机制

- 删除 Token 时，标记为 `revoked` 状态
- 认证中间件会检查 Token 状态
- 被撤销的 Token 立即返回 401 错误
- 无需更改全局密钥，不影响其他 Token

## 项目结构

```
ArcGISTokenGateway/
├── main.py                 # FastAPI 应用入口
├── config.py               # 配置管理（环境变量 + 默认值）
├── requirements.txt        # Python 依赖
├── generate_token.py       # Token 管理命令行工具
├── tokens.json             # Token 记录存储（自动生成，已加入 .gitignore）
├── .env.example            # 环境变量配置示例
├── .gitignore              # Git 忽略规则
├── examples/               # 示例脚本
│   ├── usage_example.py    # 完整功能演示（8个场景）
│   └── quick_test.py       # 自动化测试（7个用例）
├── service/
│   ├── __init__.py
│   ├── token_service.py    # JWT Token 生成、验证、权限校验
│   ├── token_store.py      # Token 记录持久化管理（JSON 文件）
│   └── proxy_service.py    # 反向代理（请求转发到 ArcGIS Server）
└── middleware/
    ├── __init__.py
    └── auth_middleware.py  # JWT 认证中间件
```

> **注意**：`.env` 和 `tokens.json` 已被加入 `.gitignore`，不会被提交到版本库。

## API 接口

### 健康检查

```
GET /health
```

响应：

```json
{
  "status": "ok",
  "timestamp": "2024-10-11T14:00:00+00:00"
}
```

### 反向代理

```
GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS /{ArcGIS 服务路径}
```

所有 `/arcgis/` 开头的请求会被代理到 ArcGIS Server（前缀大小写不敏感，`/ArcGIS/`、`/ARCGIS/` 等写法均可），需要经过 Token 验证。请求中的 `token` 参数和 `Authorization` 头不会转发到上游服务。

### 免认证路径

以下路径无需 Token 即可访问：

- `/health` - 健康检查
- `/docs` - Swagger API 文档
- `/redoc` - ReDoc API 文档
- `/openapi.json` - OpenAPI 规范文件

### 错误响应

| 状态码 | 说明                      |
| --- | ----------------------- |
| 401 | Token 无效、过期或被撤销         |
| 403 | Token 未授权访问该服务          |
| 500 | 代理内部错误                  |
| 502 | 无法连接到 ArcGIS Server     |
| 504 | ArcGIS Server 请求超时（60秒） |

## 常见问题排查

| 现象 | 原因 | 解决方法 |
| --- | --- | --- |
| `Invalid or expired token` | Token 已过期，或生成/验证使用的 JWT 密钥不一致 | 重新生成 Token；确认 `.env` 中 `JWT_SECRET_KEY` 未变更 |
| `Service not authorized in token` | Token 未授权该服务 | 使用 `--add-service` 为 Token 授权；服务路径须与授权路径一致（大小写可不同） |
| `Cannot connect to ArcGIS Server` | 网关无法连接 ArcGIS Server | 检查 `.env` 中 `ARCGIS_SERVER_URL` 是否正确、Server 是否可达 |
| 多个合法 Token 同时返回 403 | `tokens.json` 丢失、损坏或记录缺失（fail-closed 策略，拒绝优于放行） | 从备份恢复 `tokens.json`；无法恢复时重新签发 Token |
| 响应内容截断或乱码 | 上游响应头（`Content-Encoding` 等）与代理后响应不匹配 | 已内置响应头过滤，如仍出现请检查是否还有其他中间代理层 |

## 安全建议

1. **JWT 密钥**：生产环境必须使用强随机密钥，并通过环境变量传入
2. **Token 有效期**：根据业务需求设置合理的 Token 有效期
3. **最小权限原则**：为每个合作伙伴仅授权必要的地图服务
4. **Token 撤销**：及时撤销不再需要的 Token，降低安全风险
5. **定期审查**：定期检查 Token 使用情况，清理过期或无效 Token

## 生成强随机密钥

```bash
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

# Python
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 生产部署

### 使用 systemd（Linux）

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

### 使用 Docker

```bash
docker build -t arcgis-gateway .
docker run -p 8000:8000 --env-file .env arcgis-gateway
```

## 许可证

MIT
