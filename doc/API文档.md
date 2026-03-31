# YourWork API 文档 (HTTP REST API)

> **⚠️ 重要说明**
>
> YourWork 提供 **两套完全独立的 API 接口**，分别用于不同的使用场景：
>
> | API 类型 | 文档位置 | 适用场景 |
> |----------|---------|---------|
> | **HTTP REST API** | 📄 本文档 | 传统Web界面、HTTP客户端、一次性数据操作 |
> | **WebSocket API** | 📄 [WebSocket-API开发文档.md](./WebSocket-API开发文档.md) | 实时通信、事件推送、长连接场景 |
>
> **两套 API 访问相同的数据，但是完全独立的系统入口，不能混用。**
>
> - 使用 **HTTP API** 进行页面加载、表单提交、文件上传下载
> - 使用 **WebSocket API** 进行实时消息推送、协作编辑、即时通讯
>
> 请根据您的应用场景选择合适的 API 文档。

---

## 基础信息

- **协议**: HTTP/1.1
- **基础 URL**: `/api/v1`
- **数据格式**: JSON
- **字符编码**: UTF-8
- **认证方式**: Cookie (session_token)
- **会话管理**: 支持会话创建、验证、撤销和过期清理

### 认证机制

系统使用基于会话令牌的认证机制：

1. **登录获取会话令牌**：调用登录接口后，服务器生成随机会话令牌并设置到 Cookie
2. **会话验证**：每次请求时验证会话令牌的有效性、过期状态和撤销状态
3. **会话续期**：每次验证时自动更新会话的最后使用时间
4. **会话撤销**：登出时将会话标记为已撤销
5. **会话清理**：后台任务定期清理过期和已撤销的会话

**会话配置**：
- 会话令牌长度：64字符（随机生成）
- 默认有效期：24小时
- 清理间隔：60分钟
- 令牌存储：数据库 sessions 表

## 响应格式

所有 API 响应遵循统一格式：

```json
{
    "code": 0,           // 状态码：0 表示成功，其他表示失败
    "message": "成功",    // 消息描述
    "data": {}           // 返回的数据
}
```

### 常见状态码

| Code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未登录或登录过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 认证模块

### 用户登录

```
POST /api/v1/auth/login
```

**请求参数：**
```json
{
    "username": "admin",
    "password": "admin123"
}
```

**响应示例：**
```json
{
    "code": 0,
    "message": "登录成功",
    "data": {
        "id": "user-uuid",
        "username": "admin",
        "display_name": "系统管理员",
        "email": "admin@example.com",
        "session_token": "64字符随机令牌",
        "expires_at": "2024-03-26T10:30:00"
    }
}
```

**说明：**
- 登录成功后，服务器会生成随机会话令牌并设置到 Cookie
- 会话令牌同时也在响应数据中返回，方便客户端保存使用
- 会话默认有效期为24小时，可在配置中调整
- 每次请求时会自动更新会话的最后使用时间

### 用户注册

```
POST /api/v1/auth/register
```

**请求参数：**
```json
{
    "username": "newuser",
    "password": "password123",
    "display_name": "新用户",
    "email": "user@example.com"
}
```

### 用户登出

```
POST /api/v1/auth/logout
```

**响应示例：**
```json
{
    "code": 0,
    "message": "登出成功"
}
```

**说明：**
- 登出时会撤销当前会话令牌
- 服务器会清除 Cookie 中的令牌
- 已撤销的令牌无法继续使用
- 建议客户端登出后清除本地存储的令牌

### 获取当前用户信息

```
GET /api/v1/auth/profile
```

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "id": "user-uuid",
        "username": "admin",
        "display_name": "系统管理员",
        "roles": [
            {
                "code": "SYSTEM_ADMIN",
                "name": "系统管理员"
            }
        ]
    }
}
```

---

## 用户管理

### 获取用户列表

```
GET /api/v1/users
```

**权限要求：** 系统管理员

**响应示例：**
```json
{
    "code": 0,
    "data": [
        {
            "id": "user-uuid",
            "username": "admin",
            "display_name": "系统管理员",
            "email": "admin@example.com",
            "is_active": 1,
            "created_at": "2024-01-01T00:00:00"
        }
    ]
}
```

### 更新用户角色

```
PUT /api/v1/users/{user_id}/roles
```

**权限要求：** 系统管理员

**请求参数：**
```json
{
    "roles": ["ADMIN", "WORKER"]
}
```

---

## 项目管理

### 获取项目列表

```
GET /api/v1/projects
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选：in_progress, completed, ignored |
| keyword | string | 否 | 搜索关键词（项目名称或编号） |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "items": [
            {
                "id": "project-uuid",
                "project_no": "PRJ-20240101-abc12345",
                "name": "示例项目",
                "description": "项目描述",
                "status": "in_progress",
                "created_at": "2024-01-01T00:00:00"
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20
    }
}
```

### 创建项目

```
POST /api/v1/projects
```

**权限要求：** 管理员

**请求参数：**
```json
{
    "name": "新项目",
    "description": "项目描述"
}
```

### 获取项目详情

```
GET /api/v1/projects/{project_id}
```

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "project": {
            "id": "project-uuid",
            "project_no": "PRJ-20240101-abc12345",
            "name": "示例项目",
            "description": "项目描述",
            "status": "in_progress"
        },
        "milestones": [],
        "members": [],
        "deliverables": []
    }
}
```

### 更新项目信息

```
PUT /api/v1/projects/{project_id}
```

**权限要求：** 管理员

**请求参数：**
```json
{
    "name": "更新后的项目名称",
    "description": "更新后的描述"
}
```

### 更新项目状态

```
PUT /api/v1/projects/{project_id}/status
```

**权限要求：** 管理员

**请求参数：**
```json
{
    "status": "completed"
}
```

**状态值：**
- `in_progress` - 进行中
- `completed` - 已完成
- `ignored` - 已挂起

---

## 项目成员

### 添加项目成员

```
POST /api/v1/projects/{project_id}/members
```

**权限要求：** 管理员

**请求参数：**
```json
{
    "user_id": "user-uuid",
    "display_name": "成员名称",
    "roles": ["开发者"]
}
```

### 移除项目成员

```
DELETE /api/v1/projects/{project_id}/members/{user_id}
```

**权限要求：** 管理员

---

## 里程碑管理

### 获取项目里程碑列表

```
GET /api/v1/projects/{project_id}/milestones
```

**响应示例：**
```json
{
    "code": 0,
    "data": [
        {
            "id": "milestone-uuid",
            "type": "milestone",
            "name": "需求分析",
            "description": "完成需求文档",
            "status": "created",
            "deadline": "2024-12-31T23:59:59",
            "created_at": "2024-01-01T00:00:00"
        }
    ]
}
```

### 创建里程碑

```
POST /api/v1/milestones
```

**请求参数：**
```json
{
    "project_id": "project-uuid",
    "name": "里程碑名称",
    "description": "里程碑描述",
    "type": "milestone",
    "deadline": "2024-12-31T23:59:59"
}
```

**类型值：**
- `milestone` - 里程碑
- `acceptance` - 验收目标

### 获取里程碑详情

```
GET /api/v1/milestones/{milestone_id}
```

### 更新里程碑

```
PUT /api/v1/milestones/{milestone_id}
```

**请求参数：**
```json
{
    "name": "更新后的名称",
    "description": "更新后的描述",
    "status": "completed"
}
```

**状态值：**
- `created` - 已创建
- `waiting` - 等待中
- `paused` - 已暂停
- `completed` - 已完成

### 获取里程碑操作日志

```
GET /api/v1/milestones/{milestone_id}/logs
```

**响应示例：**
```json
{
    "code": 0,
    "data": [
        {
            "id": "log-uuid",
            "action": "创建里程碑",
            "description": "创建需求分析里程碑",
            "username": "admin",
            "created_at": "2024-01-01T00:00:00"
        }
    ]
}
```

### 添加里程碑操作日志

```
POST /api/v1/milestones/{milestone_id}/logs
```

**请求参数：**
```json
{
    "action": "更新状态",
    "description": "状态改为已完成"
}
```

---

## 产出物管理

### 获取项目产出物列表

```
GET /api/v1/projects/{project_id}/deliverables
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| milestone_id | string | 否 | 限定特定里程碑的产出物 |

**响应示例：**
```json
{
    "code": 0,
    "data": [
        {
            "id": "file-uuid",
            "name": "stored_name.pdf",
            "original_name": "需求文档.pdf",
            "file_size": 1048576,
            "file_type": "application/pdf",
            "created_at": "2024-01-01T00:00:00"
        }
    ]
}
```

### 上传产出物

```
POST /api/v1/projects/{project_id}/deliverables/upload
```

**请求类型：** multipart/form-data

**表单参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 上传的文件 |
| milestone_id | string | 否 | 关联的里程碑 ID |

### 下载产出物

```
GET /api/v1/deliverables/{deliverable_id}/download
```

**响应类型：** 文件流

---

## 消息管理

### 获取消息列表

```
GET /api/v1/messages
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_read | int | 否 | 0=未读, 1=已读 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "items": [
            {
                "id": "msg-uuid",
                "title": "项目状态更新",
                "content": "项目状态已更新为进行中",
                "type": "project",
                "is_read": 0,
                "created_at": "2024-01-01T00:00:00"
            }
        ],
        "total": 10,
        "unread_count": 5,
        "page": 1,
        "page_size": 20
    }
}
```

### 获取未读消息数量

```
GET /api/v1/messages/unread-count
```

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "unread_count": 5
    }
}
```

### 标记消息为已读

```
PUT /api/v1/messages/{message_id}/read
```

### 全部标记为已读

```
PUT /api/v1/messages/read-all
```

### 删除消息

```
DELETE /api/v1/messages/{message_id}
```

---

## 数据模型

### 用户 (User)

```json
{
    "id": "string",
    "username": "string",
    "password": "string",  // 哈希值，不返回给前端
    "display_name": "string",
    "email": "string",
    "avatar": "string",
    "is_active": "integer",
    "created_at": "string",  // ISO 8601 格式
    "updated_at": "string"
}
```

### 项目 (Project)

```json
{
    "id": "string",
    "project_no": "string",  // 格式: PRJ-YYYYMMDD-xxxxxxxx
    "name": "string",
    "description": "string",
    "status": "string",      // in_progress, completed, ignored
    "resources": "string",   // JSON 字符串
    "created_at": "string",
    "updated_at": "string"
}
```

### 里程碑 (Milestone)

```json
{
    "id": "string",
    "project_id": "string",
    "type": "string",        // milestone, acceptance
    "name": "string",
    "description": "string",
    "deliverables": "string",// JSON 数组
    "deadline": "string",
    "status": "string",      // created, waiting, paused, completed
    "document": "string",
    "parent_id": "string",
    "execution_result": "string",
    "created_at": "string",
    "updated_at": "string"
}
```

### 产出物 (Deliverable)

```json
{
    "id": "string",
    "name": "string",        // 存储文件名
    "original_name": "string", // 原始文件名
    "file_path": "string",
    "file_size": "integer",
    "file_type": "string",   // MIME 类型
    "project_id": "string",
    "milestone_id": "string",
    "created_by": "string",
    "created_at": "string"
}
```

### 消息 (Message)

```json
{
    "id": "string",
    "user_id": "string",
    "title": "string",
    "content": "string",
    "type": "string",        // system, project, milestone, reminder
    "is_read": "integer",
    "related_id": "string",
    "created_at": "string"
}
```

---

## 错误处理

所有错误响应遵循统一格式：

```json
{
    "code": 400,
    "message": "错误描述"
}
```

### 常见错误

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误或验证失败 |
| 401 | 未登录，需要先登录 |
| 403 | 无权限访问该资源 |
| 404 | 请求的资源不存在 |
| 500 | 服务器内部错误 |

---

## 交互式 API 文档

启动服务后，访问以下地址查看交互式 API 文档（Swagger UI）：

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

在交互式文档中可以直接测试 API 接口。

---

## 附录：如何选择合适的 API？

### HTTP REST API vs WebSocket API 对比

| 对比项 | HTTP REST API | WebSocket API |
|--------|--------------|---------------|
| **通信协议** | HTTP/1.1 | WebSocket |
| **连接模式** | 短连接（请求-响应） | 长连接（持久连接） |
| **数据流向** | 客户端主动请求 | 双向通信 |
| **会话管理** | Cookie 自动管理 | 需要手动传递会话令牌 |
| **适用场景** | 页面加载、CRUD操作、文件上传 | 实时通知、协作编辑、即时通讯 |
| **文档位置** | 📄 本文档 | 📄 [WebSocket-API开发文档.md](./WebSocket-API开发文档.md) |

### 典型使用场景

**使用 HTTP REST API 的场景**：
- ✅ 传统 Web 界面（表单提交、页面跳转）
- ✅ 移动应用的数据同步
- ✅ 文件上传和下载
- ✅ 第三方系统集成（Webhook、回调）
- ✅ 定时任务和批处理

**使用 WebSocket API 的场景**：
- ✅ 实时消息推送
- ✅ 多用户协作编辑
- ✅ 实时数据大屏
- ✅ 即时聊天功能
- ✅ 进度监控和日志流式输出

### 能否同时使用两种 API？

**可以，但需要注意**：
- HTTP API 和 WebSocket API 使用 **相同的会话令牌机制**
- 通过 HTTP API 登录获取的会话令牌，可以用于 WebSocket 连接
- 通过 WebSocket API 登录获取的会话令牌，可以用于 HTTP 请求
- 两种 API **完全独立**，可以同时使用，互不干扰

**示例流程**：
```python
# 1. 通过 HTTP API 登录
response = requests.post('http://localhost:8001/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})
session_token = response.json()['data']['session_token']

# 2. 使用会话令牌建立 WebSocket 连接
ws = websockets.connect(f'ws://localhost:8001/ws?token={session_token}')

# 3. 同时继续使用 HTTP API 进行其他操作
headers = {'Cookie': f'token={session_token}'}
projects = requests.get('http://localhost:8001/api/v1/projects', headers=headers)
```

### 文档导航

- 📄 **继续阅读本文档**：了解 HTTP REST API 的所有接口
- 📄 [查看 WebSocket API 文档](./WebSocket-API开发文档.md)：了解实时通信接口
- 📄 [查看 WebSocket API 测试方案](./WebSocket-API测试方案.md)：了解如何测试 WebSocket 接口
