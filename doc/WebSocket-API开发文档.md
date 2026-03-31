# YourWork WebSocket API 开发文档

> **⚠️ 重要说明**
>
> YourWork 提供 **两套完全独立的 API 接口**，分别用于不同的使用场景：
>
> | API 类型 | 文档位置 | 适用场景 |
> |----------|---------|---------|
> | **HTTP REST API** | 📄 [API文档.md](./API文档.md) | 传统Web界面、HTTP客户端、一次性数据操作 |
> | **WebSocket API** | 📄 本文档 | 实时通信、事件推送、长连接场景 |
>
> **两套 API 访问相同的数据，但是完全独立的系统入口，不能混用。**
>
> - 使用 **HTTP API** 进行页面加载、表单提交、文件上传下载
> - 使用 **WebSocket API** 进行实时消息推送、协作编辑、即时通讯
>
> 请根据您的应用场景选择合适的 API 文档。

---

## 一、概述

本文档描述 YourWork 企业项目管理系统的 WebSocket API 接口，供外部系统通过 WebSocket 协议进行实时通信。

### 1.1 技术规格

| 项目 | 说明 |
|------|------|
| 协议 | WebSocket |
| 连接地址 | `ws://host:8001/ws?token={session_token}` |
| 消息格式 | JSON |
| 字符编码 | UTF-8 |
| 会话超时 | 15分钟无操作自动断开 |
| 会话有效期 | 24小时（默认） |
| 会话管理 | 支持会话创建、验证、撤销和过期清理 |

### 1.2 设计原则

YourWork 遵循最小依赖原则，WebSocket 实现采用：
- **纯 FastAPI WebSocket**：不使用额外的 WebSocket 库
- **原生 SQLite**：数据库操作使用 sqlite3
- **同步代码**：保持代码简洁可追踪（必要时可转为异步）
- **统一风格**：与现有 HTTP API 数据格式保持一致（但通信机制完全不同）

### 1.3 文件结构

```
YourWork/
├── main.py                      # 主入口（添加 WebSocket 端点）
├── websocket/
│   ├── __init__.py
│   ├── manager.py              # WebSocket 连接管理器
│   ├── schemas.py              # 消息模型定义
│   ├── handlers.py             # 接口处理器（统一文件，简化结构）
│   └── auth.py                 # Token 鉴权中间件
├── data/
│   └── yourwork.db             # SQLite 数据库（新增 ws_logs 表）
└── doc/
    └── WebSocket-API开发文档.md # 本文档
```

---

## 二、连接与鉴权

### 2.1 配置项

在 `main.py` 中定义 WebSocket 配置：

```python
# WebSocket 配置
WS_SESSION_TIMEOUT: int = 900      # 会话超时时间（秒），默认15分钟
WS_MAX_CONNECTIONS: int = 1000     # 最大连接数
WS_HEARTBEAT_INTERVAL: int = 30    # 心跳检测间隔（秒）
```

### 2.2 鉴权流程

1. 客户端调用 HTTP 登录接口或 WebSocket 登录接口获取会话令牌
   ```bash
   # HTTP 登录
   POST /api/v1/auth/login
   {"username": "admin", "password": "password123"}
   # 响应中返回 session_token

   # 或 WebSocket 登录
   {"action": "system.login", "data": {"username": "admin", "password": "password123"}}
   # 响应中返回 session_token
   ```

2. 建立 WebSocket 连接时携带会话令牌
   ```
   ws://host:8001/ws?token={session_token}
   ```

3. 服务端验证会话令牌有效性
   - 查询 sessions 表验证令牌存在且未撤销
   - 检查令牌未过期（expires_at > 当前时间）
   - 关联查询用户信息（users 表）
   - 更新会话的最后使用时间（last_used_at）

4. 验证通过后建立连接，加入用户连接池

5. 每次请求时更新最后活跃时间，超过 15 分钟无操作则断开连接

6. 会话过期或撤销后，需重新登录获取新令牌

### 2.2.1 会话管理

系统实现了完整的会话管理机制：

| 功能 | 说明 |
|------|------|
| 会话创建 | 登录时生成随机64字符令牌，有效期24小时 |
| 会话验证 | 每次请求验证令牌有效性、过期状态和撤销状态 |
| 会话撤销 | 登出时将会话标记为已撤销 |
| 会话清理 | 后台任务每小时清理一次过期和已撤销的会话 |
| 会话续期 | 每次验证时自动更新 last_used_at 时间戳 |

**会话表结构**：
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2.3 会话超时处理

- 每次收到请求时，更新连接的 `last_active_time`
- 处理请求前检查 `当前时间 - last_active_time > 900 秒`
- 超时则断开连接并返回错误

超时响应示例：
```json
{
  "action": "project.list",
  "request_id": "req_001",
  "code": 401,
  "message": "未登录：会话已过期，请重新登录",
  "data": null
}
```

---

## 三、消息格式

### 3.1 请求格式

```json
{
  "action": "操作名称",
  "request_id": "请求唯一标识",
  "data": {
    // 参数键值对
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 要执行的操作名称 |
| request_id | string | 是 | 请求唯一标识，用于匹配响应 |
| data | object | 否 | 操作参数，具体内容取决于 action |

### 3.2 响应格式

```json
{
  "action": "操作名称",
  "request_id": "请求唯一标识",
  "code": 0,
  "message": "success",
  "data": {
    // 返回数据
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| action | string | 与请求中的 action 相同 |
| request_id | string | 与请求中的 request_id 相同 |
| code | int | 响应码，0 表示成功 |
| message | string | 响应消息 |
| data | any | 返回数据，具体内容取决于 action |

### 3.3 服务器主动推送格式

```json
{
  "type": "notification",
  "event": "事件类型",
  "data": {
    // 事件数据
  },
  "timestamp": "2024-03-25T10:30:00"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 固定值 "notification" |
| event | string | 事件类型：message、milestone、project 等 |
| data | object | 事件数据 |
| timestamp | string | 事件时间戳 |

### 3.4 错误码定义

| Code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未登录/会话过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 四、接口列表

### 4.1 系统接口

#### 4.1.1 登录 `system.login`

**说明**: 用户登录（WebSocket 专用登录接口）

**权限**: 无需鉴权

**请求参数**:
```json
{
  "action": "system.login",
  "request_id": "req_001",
  "data": {
    "username": "admin",
    "password": "password123"
  }
}
```

**响应数据**:
```json
{
  "action": "system.login",
  "request_id": "req_001",
  "code": 0,
  "message": "登录成功",
  "data": {
    "session_token": "64字符随机令牌",
    "expires_at": "2024-03-26T10:30:00",
    "session_timeout_hours": 24,
    "user": {
      "id": "user_id",
      "username": "admin",
      "display_name": "管理员",
      "email": "admin@example.com",
      "roles": ["ADMIN"]
    },
    "capabilities": [
      {
        "action": "project.create",
        "description": "创建项目",
        "params": {
          "name": "string - 项目名称",
          "description": "string - 项目描述（可选）"
        }
      }
    ]
  }
}
```

#### 4.1.2 获取可用接口 `system.capabilities`

**说明**: 获取当前用户可使用的接口列表

**权限**: 已登录

**请求参数**:
```json
{
  "action": "system.capabilities",
  "request_id": "req_002",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "system.capabilities",
  "request_id": "req_002",
  "code": 0,
  "message": "success",
  "data": {
    "session_timeout": 900,
    "capabilities": [
      {
        "action": "project.create",
        "description": "创建项目",
        "params": {
          "name": "string - 项目名称",
          "description": "string - 项目描述（可选）"
        }
      },
      {
        "action": "milestone.create",
        "description": "创建里程碑",
        "params": {
          "project_id": "string - 项目ID",
          "name": "string - 里程碑名称",
          "description": "string - 里程碑描述（可选）",
          "deadline": "string - 截止日期（可选）"
        }
      }
    ]
  }
}
```

#### 4.1.3 心跳检测 `system.ping`

**说明**: 保持连接活跃，防止会话超时

**权限**: 已登录

**请求参数**:
```json
{
  "action": "system.ping",
  "request_id": "req_003",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "system.ping",
  "request_id": "req_003",
  "code": 0,
  "message": "pong",
  "data": {
    "server_time": "2024-03-25T10:30:00"
  }
}
```

#### 4.1.4 用户登出 `system.logout`

**说明**: 用户登出并撤销当前会话令牌

**权限**: 已登录

**请求参数**:
```json
{
  "action": "system.logout",
  "request_id": "req_004",
  "data": {
    "session_token": "当前会话令牌"
  }
}
```

**响应数据**:
```json
{
  "action": "system.logout",
  "request_id": "req_004",
  "code": 0,
  "message": "登出成功",
  "data": {
    "message": "会话已撤销，请关闭连接"
  }
}
```

**注意**:
- 登出成功后，会话令牌将被撤销，无法继续使用
- 客户端应在收到成功响应后主动关闭 WebSocket 连接
- 已撤销的令牌无法用于新的连接或请求

---

### 4.2 项目管理接口

#### 4.2.1 创建项目 `project.create`

**权限**: ADMIN, SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "project.create",
  "request_id": "req_004",
  "data": {
    "name": "新项目名称",
    "description": "项目描述"
  }
}
```

**响应数据**:
```json
{
  "action": "project.create",
  "request_id": "req_004",
  "code": 0,
  "message": "项目创建成功",
  "data": {
    "id": "project_id",
    "project_no": "PRJ-20240325-abc12345",
    "name": "新项目名称",
    "description": "项目描述",
    "status": "in_progress",
    "created_at": "2024-03-25T10:30:00"
  }
}
```

#### 4.2.2 获取项目列表 `project.list`

**权限**: 所有登录用户（仅看到自己参与的项目，管理员可看全部）

**请求参数**:
```json
{
  "action": "project.list",
  "request_id": "req_005",
  "data": {
    "status": "in_progress",
    "keyword": "搜索关键词",
    "page": 1,
    "page_size": 20
  }
}
```

**响应数据**:
```json
{
  "action": "project.list",
  "request_id": "req_005",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "project_id",
        "project_no": "PRJ-20240325-abc12345",
        "name": "项目名称",
        "description": "项目描述",
        "status": "in_progress",
        "created_at": "2024-03-25T10:30:00"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### 4.2.3 获取项目详情 `project.get`

**权限**: 所有登录用户（需是项目成员或管理员）

**请求参数**:
```json
{
  "action": "project.get",
  "request_id": "req_006",
  "data": {
    "project_id": "project_id"
  }
}
```

**响应数据**:
```json
{
  "action": "project.get",
  "request_id": "req_006",
  "code": 0,
  "message": "success",
  "data": {
    "project": {
      "id": "project_id",
      "project_no": "PRJ-20240325-abc12345",
      "name": "项目名称",
      "description": "项目描述",
      "status": "in_progress",
      "created_at": "2024-03-25T10:30:00",
      "updated_at": "2024-03-25T10:30:00"
    },
    "milestones": [],
    "members": [],
    "deliverables": []
  }
}
```

#### 4.2.4 更新项目 `project.update`

**权限**: ADMIN, SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "project.update",
  "request_id": "req_007",
  "data": {
    "project_id": "project_id",
    "name": "更新后的名称",
    "description": "更新后的描述"
  }
}
```

**响应数据**:
```json
{
  "action": "project.update",
  "request_id": "req_007",
  "code": 0,
  "message": "项目更新成功",
  "data": {
    "id": "project_id",
    "project_no": "PRJ-20240325-abc12345",
    "name": "更新后的名称",
    "description": "更新后的描述",
    "status": "in_progress",
    "updated_at": "2024-03-25T11:00:00"
  }
}
```

#### 4.2.5 更新项目状态 `project.update_status`

**权限**: ADMIN, SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "project.update_status",
  "request_id": "req_008",
  "data": {
    "project_id": "project_id",
    "status": "completed"
  }
}
```

**状态值**: `in_progress` | `completed` | `ignored`

**响应数据**:
```json
{
  "action": "project.update_status",
  "request_id": "req_008",
  "code": 0,
  "message": "状态更新成功",
  "data": {
    "id": "project_id",
    "status": "completed",
    "updated_at": "2024-03-25T12:00:00"
  }
}
```

---

### 4.3 里程碑接口

#### 4.3.1 创建里程碑 `milestone.create`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.create",
  "request_id": "req_009",
  "data": {
    "project_id": "project_id",
    "name": "里程碑名称",
    "description": "里程碑描述",
    "type": "milestone",
    "deadline": "2024-12-31"
  }
}
```

**类型**: `milestone` | `phase` | `acceptance`

**响应数据**:
```json
{
  "action": "milestone.create",
  "request_id": "req_009",
  "code": 0,
  "message": "里程碑创建成功",
  "data": {
    "id": "milestone_id",
    "project_id": "project_id",
    "type": "milestone",
    "name": "里程碑名称",
    "description": "里程碑描述",
    "deadline": "2024-12-31",
    "status": "created",
    "created_at": "2024-03-25T10:30:00"
  }
}
```

#### 4.3.2 获取里程碑列表 `milestone.list`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.list",
  "request_id": "req_010",
  "data": {
    "project_id": "project_id"
  }
}
```

**响应数据**:
```json
{
  "action": "milestone.list",
  "request_id": "req_010",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "milestone_id",
        "project_id": "project_id",
        "type": "milestone",
        "name": "里程碑名称",
        "description": "里程碑描述",
        "deadline": "2024-12-31",
        "status": "created",
        "created_at": "2024-03-25T10:30:00"
      }
    ],
    "total": 1
  }
}
```

#### 4.3.3 获取里程碑详情 `milestone.get`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.get",
  "request_id": "req_011",
  "data": {
    "milestone_id": "milestone_id"
  }
}
```

**响应数据**:
```json
{
  "action": "milestone.get",
  "request_id": "req_011",
  "code": 0,
  "message": "success",
  "data": {
    "id": "milestone_id",
    "project_id": "project_id",
    "type": "milestone",
    "name": "里程碑名称",
    "description": "里程碑描述",
    "deadline": "2024-12-31",
    "status": "created",
    "created_at": "2024-03-25T10:30:00",
    "updated_at": "2024-03-25T10:30:00"
  }
}
```

#### 4.3.4 更新里程碑 `milestone.update`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.update",
  "request_id": "req_012",
  "data": {
    "milestone_id": "milestone_id",
    "name": "新名称",
    "description": "新描述",
    "status": "in_progress"
  }
}
```

**状态值**: `created` | `in_progress` | `paused` | `completed`

**响应数据**:
```json
{
  "action": "milestone.update",
  "request_id": "req_012",
  "code": 0,
  "message": "里程碑更新成功",
  "data": {
    "id": "milestone_id",
    "name": "新名称",
    "description": "新描述",
    "status": "in_progress",
    "updated_at": "2024-03-25T11:00:00"
  }
}
```

#### 4.3.5 获取里程碑日志 `milestone.logs`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.logs",
  "request_id": "req_013",
  "data": {
    "milestone_id": "milestone_id"
  }
}
```

**响应数据**:
```json
{
  "action": "milestone.logs",
  "request_id": "req_013",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "log_id",
        "milestone_id": "milestone_id",
        "user_id": "user_id",
        "username": "admin",
        "action": "创建里程碑",
        "description": "",
        "created_at": "2024-03-25T10:30:00"
      }
    ],
    "total": 1
  }
}
```

#### 4.3.6 添加里程碑日志 `milestone.add_log`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "milestone.add_log",
  "request_id": "req_014",
  "data": {
    "milestone_id": "milestone_id",
    "action": "更新状态",
    "description": "状态改为进行中"
  }
}
```

**响应数据**:
```json
{
  "action": "milestone.add_log",
  "request_id": "req_014",
  "code": 0,
  "message": "日志添加成功",
  "data": {
    "id": "log_id",
    "milestone_id": "milestone_id",
    "action": "更新状态",
    "description": "状态改为进行中",
    "created_at": "2024-03-25T11:00:00"
  }
}
```

---

### 4.4 产出物接口

#### 4.4.1 关联产出物 `deliverable.upload`

**说明**: 将已上传的文件关联到项目/里程碑

**权限**: 所有登录用户

**步骤 1**: 通过 HTTP 上传文件
```
POST /api/v1/projects/{project_id}/deliverables/upload
Content-Type: multipart/form-data

file: <文件>
milestone_id: <里程碑ID（可选）>
```

**步骤 2**: 通过 WebSocket 关联
```json
{
  "action": "deliverable.upload",
  "request_id": "req_015",
  "data": {
    "project_id": "project_id",
    "milestone_id": "milestone_id",
    "deliverable_id": "已上传的产出物ID"
  }
}
```

**响应数据**:
```json
{
  "action": "deliverable.upload",
  "request_id": "req_015",
  "code": 0,
  "message": "产出物关联成功",
  "data": {
    "id": "deliverable_id",
    "name": "stored_name.pdf",
    "original_name": "原始名称.pdf",
    "file_size": 1024000,
    "file_type": "application/pdf",
    "project_id": "project_id",
    "milestone_id": "milestone_id",
    "created_by": "user_id",
    "created_at": "2024-03-25T10:30:00"
  }
}
```

#### 4.4.2 获取产出物列表 `deliverable.list`

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "deliverable.list",
  "request_id": "req_016",
  "data": {
    "project_id": "project_id",
    "milestone_id": "milestone_id"
  }
}
```

**响应数据**:
```json
{
  "action": "deliverable.list",
  "request_id": "req_016",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "deliverable_id",
        "name": "stored_name.pdf",
        "original_name": "原始名称.pdf",
        "file_size": 1024000,
        "file_type": "application/pdf",
        "project_id": "project_id",
        "milestone_id": "milestone_id",
        "created_by": "user_id",
        "created_at": "2024-03-25T10:30:00"
      }
    ],
    "total": 1
  }
}
```

#### 4.4.3 获取下载信息 `deliverable.download`

**说明**: 获取产出物下载信息（实际下载通过 HTTP）

**权限**: 所有登录用户

**请求参数**:
```json
{
  "action": "deliverable.download",
  "request_id": "req_017",
  "data": {
    "deliverable_id": "deliverable_id"
  }
}
```

**响应数据**:
```json
{
  "action": "deliverable.download",
  "request_id": "req_017",
  "code": 0,
  "message": "success",
  "data": {
    "deliverable_id": "deliverable_id",
    "original_name": "原始名称.pdf",
    "download_url": "/api/v1/deliverables/deliverable_id/download"
  }
}
```

---

### 4.5 项目成员接口

#### 4.5.1 添加项目成员 `project.add_member`

**权限**: ADMIN, SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "project.add_member",
  "request_id": "req_018",
  "data": {
    "project_id": "project_id",
    "user_id": "user_id",
    "display_name": "张三",
    "roles": ["开发", "测试"]
  }
}
```

**响应数据**:
```json
{
  "action": "project.add_member",
  "request_id": "req_018",
  "code": 0,
  "message": "成员添加成功",
  "data": {
    "id": "member_id",
    "project_id": "project_id",
    "user_id": "user_id",
    "display_name": "张三",
    "roles": ["开发", "测试"]
  }
}
```

#### 4.5.2 移除项目成员 `project.remove_member`

**权限**: ADMIN, SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "project.remove_member",
  "request_id": "req_019",
  "data": {
    "project_id": "project_id",
    "user_id": "user_id"
  }
}
```

**响应数据**:
```json
{
  "action": "project.remove_member",
  "request_id": "req_019",
  "code": 0,
  "message": "成员移除成功",
  "data": null
}
```

---

### 4.6 用户接口

#### 4.6.1 获取用户信息 `user.profile`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "user.profile",
  "request_id": "req_020",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "user.profile",
  "request_id": "req_020",
  "code": 0,
  "message": "success",
  "data": {
    "id": "user_id",
    "username": "username",
    "display_name": "显示名称",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-03-25T10:00:00",
    "roles": [
      {
        "code": "ADMIN",
        "name": "管理员",
        "description": "系统管理员"
      }
    ]
  }
}
```

#### 4.6.2 更新用户信息 `user.update_profile`

**权限**: 已登录（仅更新自己的信息）

**请求参数**:
```json
{
  "action": "user.update_profile",
  "request_id": "req_021",
  "data": {
    "display_name": "新显示名称",
    "email": "new@example.com"
  }
}
```

**响应数据**:
```json
{
  "action": "user.update_profile",
  "request_id": "req_021",
  "code": 0,
  "message": "用户信息更新成功",
  "data": {
    "id": "user_id",
    "username": "username",
    "display_name": "新显示名称",
    "email": "new@example.com",
    "updated_at": "2024-03-25T11:00:00"
  }
}
```

---

### 4.7 消息接口

#### 4.7.1 获取消息列表 `message.list`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "message.list",
  "request_id": "req_022",
  "data": {
    "is_read": 0,
    "page": 1,
    "page_size": 20
  }
}
```

**响应数据**:
```json
{
  "action": "message.list",
  "request_id": "req_022",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "message_id",
        "user_id": "user_id",
        "title": "消息标题",
        "content": "消息内容",
        "type": "info",
        "is_read": 0,
        "created_at": "2024-03-25T10:30:00"
      }
    ],
    "total": 10,
    "unread_count": 5,
    "page": 1,
    "page_size": 20
  }
}
```

#### 4.7.2 获取未读数量 `message.unread_count`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "message.unread_count",
  "request_id": "req_023",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "message.unread_count",
  "request_id": "req_023",
  "code": 0,
  "message": "success",
  "data": {
    "unread_count": 5
  }
}
```

#### 4.7.3 标记消息已读 `message.mark_read`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "message.mark_read",
  "request_id": "req_024",
  "data": {
    "message_id": "message_id"
  }
}
```

**响应数据**:
```json
{
  "action": "message.mark_read",
  "request_id": "req_024",
  "code": 0,
  "message": "标记成功",
  "data": null
}
```

#### 4.7.4 标记全部已读 `message.mark_all_read`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "message.mark_all_read",
  "request_id": "req_025",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "message.mark_all_read",
  "request_id": "req_025",
  "code": 0,
  "message": "标记成功",
  "data": {
    "count": 10
  }
}
```

#### 4.7.5 删除消息 `message.delete`

**权限**: 已登录

**请求参数**:
```json
{
  "action": "message.delete",
  "request_id": "req_026",
  "data": {
    "message_id": "message_id"
  }
}
```

**响应数据**:
```json
{
  "action": "message.delete",
  "request_id": "req_026",
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

---

### 4.8 管理员接口

#### 4.8.1 获取用户列表 `admin.user_list`

**权限**: SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "admin.user_list",
  "request_id": "req_027",
  "data": {}
}
```

**响应数据**:
```json
{
  "action": "admin.user_list",
  "request_id": "req_027",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "user_id",
        "username": "username",
        "display_name": "显示名称",
        "email": "user@example.com",
        "is_active": true,
        "created_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 10
  }
}
```

#### 4.8.2 更新用户角色 `admin.update_user_roles`

**权限**: SYSTEM_ADMIN

**请求参数**:
```json
{
  "action": "admin.update_user_roles",
  "request_id": "req_028",
  "data": {
    "user_id": "user_id",
    "roles": ["ADMIN", "WORKER"]
  }
}
```

**响应数据**:
```json
{
  "action": "admin.update_user_roles",
  "request_id": "req_028",
  "code": 0,
  "message": "角色更新成功",
  "data": null
}
```

---

## 五、服务器主动推送事件

### 5.1 事件类型

| 事件类型 | 触发条件 | 推送对象 |
|---------|---------|---------|
| `message.new` | 收到新消息 | 相关用户 |
| `milestone.updated` | 里程碑状态变更 | 项目成员 |
| `project.updated` | 项目状态变更 | 项目成员 |
| `deliverable.uploaded` | 新产出物上传 | 项目成员 |

### 5.2 事件推送格式

#### 新消息推送
```json
{
  "type": "notification",
  "event": "message.new",
  "data": {
    "message_id": "message_id",
    "title": "消息标题",
    "content": "消息内容",
    "type": "info"
  },
  "timestamp": "2024-03-25T10:30:00"
}
```

#### 里程碑更新推送
```json
{
  "type": "notification",
  "event": "milestone.updated",
  "data": {
    "project_id": "project_id",
    "project_name": "项目名称",
    "milestone_id": "milestone_id",
    "milestone_name": "里程碑名称",
    "status": "completed",
    "operator": "操作人"
  },
  "timestamp": "2024-03-25T10:30:00"
}
```

#### 项目更新推送
```json
{
  "type": "notification",
  "event": "project.updated",
  "data": {
    "project_id": "project_id",
    "project_name": "项目名称",
    "status": "completed",
    "operator": "操作人"
  },
  "timestamp": "2024-03-25T10:30:00"
}
```

#### 产出物上传推送
```json
{
  "type": "notification",
  "event": "deliverable.uploaded",
  "data": {
    "project_id": "project_id",
    "project_name": "项目名称",
    "deliverable_id": "deliverable_id",
    "original_name": "文件名.pdf",
    "uploaded_by": "上传人"
  },
  "timestamp": "2024-03-25T10:30:00"
}
```

---

## 六、权限控制

### 6.1 角色定义

| 角色 | 代码 | 说明 |
|------|------|------|
| 系统管理员 | SYSTEM_ADMIN | 拥有所有权限 |
| 管理员 | ADMIN | 可创建和管理项目 |
| 工作人员 | WORKER | 可参与项目工作 |

### 6.2 权限矩阵

| 功能 | SYSTEM_ADMIN | ADMIN | WORKER |
|------|:------------:|:-----:|:------:|
| 创建项目 | ✓ | ✓ | ✗ |
| 查看项目 | ✓ | ✓ | ✓ (参与的) |
| 修改项目 | ✓ | ✓ | ✗ |
| 更新项目状态 | ✓ | ✓ | ✗ |
| 管理项目成员 | ✓ | ✓ | ✗ |
| 创建里程碑 | ✓ | ✓ | ✓ (参与的) |
| 更新里程碑 | ✓ | ✓ | ✓ (参与的) |
| 上传产出物 | ✓ | ✓ | ✓ (参与的) |
| 查看消息 | ✓ | ✓ | ✓ |
| 用户管理 | ✓ | ✗ | ✗ |

---

## 七、操作日志

### 7.1 日志表结构

新增 `ws_logs` 表记录 WebSocket 操作：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 主键 |
| user_id | TEXT | 用户ID |
| action | TEXT | 操作名称 |
| request_id | TEXT | 请求ID |
| request_data | TEXT | 请求数据（JSON） |
| response_code | INTEGER | 响应码 |
| response_message | TEXT | 响应消息 |
| error_message | TEXT | 错误信息 |
| ip_address | TEXT | 客户端IP |
| created_at | TEXT | 操作时间 |

### 7.2 建表语句

```sql
CREATE TABLE IF NOT EXISTS ws_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    request_id TEXT NOT NULL,
    request_data TEXT,
    response_code INTEGER,
    response_message TEXT,
    error_message TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 八、开发指南

### 8.1 文件创建

1. 创建 `websocket/` 目录
2. 创建以下文件：
   - `websocket/__init__.py`
   - `websocket/manager.py` - 连接管理器
   - `websocket/schemas.py` - 消息模型
   - `websocket/handlers.py` - 接口处理器
   - `websocket/auth.py` - 鉴权中间件

### 8.2 代码组织

所有 WebSocket 处理逻辑集中在 `websocket/handlers.py` 中，每个接口对应一个静态方法：

```python
# websocket/handlers.py

class WebSocketHandlers:
    """WebSocket 接口处理器"""

    @staticmethod
    async def system_login(data: dict, user: dict, conn, request_id: str) -> dict:
        """处理登录"""
        pass

    @staticmethod
    async def project_create(data: dict, user: dict, conn, request_id: str) -> dict:
        """处理创建项目"""
        pass

    # ... 其他接口
```

### 8.3 接口注册

在 `main.py` 中添加 WebSocket 端点：

```python
from fastapi import WebSocket, WebSocketDisconnect
from websocket.manager import WebSocketManager
from websocket.handlers import WebSocketHandlers

ws_manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket 端点"""
    await ws_manager.connect(websocket, token)

    try:
        while True:
            data = await websocket.receive_json()
            response = await ws_manager.handle_message(data)
            await websocket.send_json(response)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

### 8.4 添加新接口流程

1. 在 `handlers.py` 中添加处理方法
2. 在 `manager.py` 的 `ACTION_HANDLERS` 中注册
3. 在本文档中添加接口说明
4. 在 `system.capabilities` 中添加接口描述

### 8.5 调试方法

1. 使用浏览器控制台或 WebSocket 测试工具
2. 启用日志输出：
   ```python
   logging.getLogger("websocket").setLevel(logging.DEBUG)
   ```
3. 检查 `ws_logs` 表中的操作记录

---

## 九、测试指南

### 9.1 测试工具

推荐使用以下工具测试 WebSocket 接口：
- 浏览器控制台
- Postman（支持 WebSocket）
- wscat（命令行工具）
- 在线 WebSocket 测试工具

### 9.2 测试示例

使用浏览器控制台测试：

```javascript
// 连接 WebSocket
const token = "your_token_here";
const ws = new WebSocket(`ws://localhost:8001/ws?token=${token}`);

// 监听消息
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log("收到响应:", response);
};

// 发送登录请求
ws.send(JSON.stringify({
  action: "system.login",
  request_id: "test_001",
  data: {
    username: "admin",
    password: "password123"
  }
}));

// 发送获取项目列表请求
ws.send(JSON.stringify({
  action: "project.list",
  request_id: "test_002",
  data: {
    page: 1,
    page_size: 20
  }
}));
```

### 9.3 测试用例

| 测试场景 | 验证点 |
|---------|--------|
| 无 Token 连接 | 返回 401 错误 |
| 无效 Token 连接 | 返回 401 错误 |
| 正常登录 | 返回 token 和用户信息 |
| 会话超时 | 15分钟无操作后断开 |
| 心跳检测 | 保持连接活跃 |
| 权限控制 | 无权限操作返回 403 |
| 主动推送 | 事件正确推送给相关用户 |

---

## 十、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.1.0 | 2026-03-30 | 更新会话令牌机制，添加 system.logout 接口 |
| 1.0.0 | 2024-03-25 | 初始版本 |

---

## 十一、注意事项

1. **会话令牌鉴权**：使用64字符随机会话令牌，需要验证会话存在、未过期、未撤销
2. **会话超时**：15分钟无活动自动断开，建议客户端定时发送心跳
3. **文件上传**：大文件上传仍使用 HTTP 接口，WebSocket 仅用于关联
4. **并发控制**：注意 SQLite 的并发限制，大量请求时考虑使用连接池
5. **错误处理**：所有异常都应返回标准格式的错误响应
6. **日志记录**：所有 WebSocket 操作都应记录到 ws_logs 表

---

## 十二、如何选择合适的 API？

### WebSocket API vs HTTP REST API 对比

| 对比项 | WebSocket API | HTTP REST API |
|--------|--------------|---------------|
| **通信协议** | WebSocket | HTTP/1.1 |
| **连接模式** | 长连接（持久连接） | 短连接（请求-响应） |
| **数据流向** | 双向通信 | 客户端主动请求 |
| **会话管理** | 需要手动传递会话令牌 | Cookie 自动管理 |
| **适用场景** | 实时通知、协作编辑、即时通讯 | 页面加载、CRUD操作、文件上传 |
| **文档位置** | 📄 本文档 | 📄 [API文档.md](./API文档.md) |

### 典型使用场景

**使用 WebSocket API 的场景**：
- ✅ 实时消息推送
- ✅ 多用户协作编辑
- ✅ 实时数据大屏
- ✅ 即时聊天功能
- ✅ 进度监控和日志流式输出

**使用 HTTP REST API 的场景**：
- ✅ 传统 Web 界面（表单提交、页面跳转）
- ✅ 移动应用的数据同步
- ✅ 文件上传和下载
- ✅ 第三方系统集成（Webhook、回调）
- ✅ 定时任务和批处理

### 能否同时使用两种 API？

**可以，但需要注意**：
- WebSocket API 和 HTTP API 使用 **相同的会话令牌机制**
- 通过 HTTP API 登录获取的会话令牌，可以用于 WebSocket 连接
- 通过 WebSocket API 登录获取的会话令牌，可以用于 HTTP 请求
- 两种 API **完全独立**，可以同时使用，互不干扰

**示例流程**：
```javascript
// 1. 通过 WebSocket API 登录
ws.send(JSON.stringify({
  action: "system.login",
  request_id: "login_001",
  data: {
    username: "admin",
    password: "admin123"
  }
}));

// 2. 收到会话令牌
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  if (response.action === "system.login" && response.code === 0) {
    const sessionToken = response.data.session_token;

    // 3. 使用会话令牌调用 HTTP API
    fetch('http://localhost:8001/api/v1/projects', {
      headers: {
        'Cookie': `token=${sessionToken}`
      }
    });
  }
};
```

### 文档导航

- 📄 **继续阅读本文档**：了解 WebSocket API 的所有接口
- 📄 [查看 HTTP REST API 文档](./API文档.md)：了解传统 HTTP 接口
- 📄 [查看 WebSocket API 测试方案](./WebSocket-API测试方案.md)：了解如何测试 WebSocket 接口

---

## 十三、联系方式

如有问题或建议，请联系开发团队。
