# YourWork WebSocket API 完整测试方案

> **⚠️ 重要说明**
>
> YourWork 提供 **两套完全独立的 API 接口**：
>
> | API 类型 | 测试文档 | 接口数量 | 连接方式 |
> |----------|---------|---------|---------|
> | **HTTP REST API** | [API文档.md](./API文档.md) | ~50个 | HTTP 协议 |
> | **WebSocket API** | 📄 本文档 | 29个 | WebSocket 协议 |
>
> **两套 API 是完全独立的系统入口。**
>
> - **HTTP API**：用于传统Web界面、表单提交、文件操作
> - **WebSocket API**：用于实时通信、消息推送、长连接场景
>
> 本文档 **仅包含 WebSocket API 的测试**。

---

## 文档信息

| 项目 | 内容 |
|------|------|
| **文档名称** | WebSocket API 全覆盖测试方案 |
| **版本** | 1.1.0 |
| **适用系统** | YourWork 企业项目管理系统 |
| **测试目标** | 验证所有 29 个 WebSocket API 接口功能 |
| **编写日期** | 2026-03-30 |
| **更新内容** | 新增会话令牌机制测试，添加 system.logout 接口测试 |

---

## 一、测试概述

### 1.1 测试目的

本测试方案用于验证 YourWork 系统的 WebSocket API 接口功能完整性，确保外部系统能够通过 WebSocket 协议完成所有业务操作。

### 1.2 测试范围

覆盖所有 **29 个 WebSocket API 接口**：

| 模块 | 接口数量 | 接口列表 |
|------|---------|---------|
| **系统接口** | 4 | system.login, system.capabilities, system.ping, system.logout |
| **项目管理** | 5 | project.create, project.list, project.get, project.update, project.update_status |
| **里程碑管理** | 6 | milestone.create, milestone.list, milestone.get, milestone.update, milestone.logs, milestone.add_log |
| **产出物管理** | 3 | deliverable.upload, deliverable.list, deliverable.download |
| **项目成员** | 2 | project.add_member, project.remove_member |
| **用户管理** | 2 | user.profile, user.update_profile |
| **消息管理** | 5 | message.list, message.unread_count, message.mark_read, message.mark_all_read, message.delete |
| **管理员功能** | 2 | admin.user_list, admin.update_user_roles |

### 1.3 测试环境要求

| 项目 | 要求 |
|------|------|
| **服务器地址** | ws://localhost:8001/ws |
| **测试账号** | admin / admin123 (SYSTEM_ADMIN) |
| **Python 版本** | 3.8+ |
| **依赖库** | websockets, asyncio |

---

## 二、测试前准备

### 2.1 安装依赖

```bash
pip install websockets
```

### 2.2 获取测试用户 Token

**方法1：通过 HTTP API 登录获取会话令牌**

```python
import requests

response = requests.post('http://localhost:8001/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})
data = response.json()
if data['code'] == 0:
    session_token = data['data']['session_token']
    print(f"Session Token: {session_token}")
```

**方法2：通过 WebSocket API 登录获取会话令牌**

```python
import asyncio
import websockets
import json

async def get_session_token():
    uri = "ws://localhost:8001/ws"
    async with websockets.connect(uri) as websocket:
        request = {
            "action": "system.login",
            "request_id": "get_token",
            "data": {
                "username": "admin",
                "password": "admin123"
            }
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        data = json.loads(response)
        if data['code'] == 0:
            return data['data']['session_token']
        return None

session_token = asyncio.run(get_session_token())
print(f"Session Token: {session_token}")
```

### 2.3 初始化测试数据

确保数据库中存在以下测试数据：
- 至少 1 个项目
- 每个项目至少 1 个里程碑
- 至少 1 个普通用户（非 admin）

### 2.4 会话令牌测试说明

**会话令牌机制**：
- 令牌长度：64字符（随机生成）
- 默认有效期：24小时
- 令牌撤销：登出时将会话标记为已撤销
- 令牌续期：每次验证时自动更新最后使用时间

**测试场景**：
1. **正常登录**：验证返回64字符会话令牌
2. **令牌使用**：使用获取的令牌进行其他API调用
3. **令牌撤销**：调用logout接口撤销令牌
4. **撤销后拒绝**：验证撤销后的令牌无法使用
5. **过期处理**：等待令牌过期或手动修改数据库测试过期场景

---

## 三、接口测试用例

### 3.1 系统接口 (System)

#### TC001: system.login - 用户登录

**测试目的**: 验证 WebSocket 登录功能

**请求示例**:
```json
{
  "action": "system.login",
  "request_id": "TC001_001",
  "data": {
    "username": "admin",
    "password": "admin123"
  }
}
```

**预期响应**:
```json
{
  "action": "system.login",
  "request_id": "TC001_001",
  "code": 0,
  "message": "登录成功",
  "data": {
    "session_token": "64字符随机令牌",
    "expires_at": "2026-03-31T16:13:23",
    "session_timeout_hours": 24,
    "user": {
      "id": "cc7b395b-6c24-46ca-adb4-0c9879aff417",
      "username": "admin",
      "display_name": "系统管理员",
      "email": "admin@example.com",
      "roles": ["SYSTEM_ADMIN"]
    },
    "capabilities": [...]
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] session_token 不为空且长度为64字符
- [ ] expires_at 为未来时间
- [ ] user 信息完整
- [ ] capabilities 列表不为空

---

#### TC002: system.capabilities - 获取可用接口

**测试目的**: 验证获取当前用户可用的接口列表

**请求示例**:
```json
{
  "action": "system.capabilities",
  "request_id": "TC002_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "system.capabilities",
  "request_id": "TC002_001",
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
      }
    ]
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] session_timeout = 900
- [ ] capabilities 数组不为空

---

#### TC003: system.ping - 心跳检测

**测试目的**: 验证心跳连接保持功能

**请求示例**:
```json
{
  "action": "system.ping",
  "request_id": "TC003_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "system.ping",
  "request_id": "TC003_001",
  "code": 0,
  "message": "pong",
  "data": {
    "server_time": "2026-03-30T16:13:23.285853"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] message = "pong"
- [ ] server_time 为有效时间戳

---

#### TC004: system.logout - 用户登出

**测试目的**: 验证WebSocket登出功能，撤销会话令牌

**请求示例**:
```json
{
  "action": "system.logout",
  "request_id": "TC004_001",
  "data": {
    "session_token": "当前会话令牌"
  }
}
```

**预期响应**:
```json
{
  "action": "system.logout",
  "request_id": "TC004_001",
  "code": 0,
  "message": "登出成功",
  "data": {
    "message": "会话已撤销，请关闭连接"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 会话被撤销
- [ ] 撤销后的令牌无法继续使用

---

### 3.2 项目管理接口 (Project)

#### TC004: project.create - 创建项目

**测试目的**: 验证创建新项目功能

**请求示例**:
```json
{
  "action": "project.create",
  "request_id": "TC004_001",
  "data": {
    "name": "WebSocket测试项目",
    "description": "通过WebSocket API创建的测试项目"
  }
}
```

**预期响应**:
```json
{
  "action": "project.create",
  "request_id": "TC004_001",
  "code": 0,
  "message": "项目创建成功",
  "data": {
    "id": "project_uuid",
    "project_no": "PRJ-20260330-xxxxx",
    "name": "WebSocket测试项目",
    "description": "通过WebSocket API创建的测试项目",
    "status": "in_progress",
    "created_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 返回项目 id
- [ ] project_no 格式正确
- [ ] status = "in_progress"

---

#### TC005: project.list - 获取项目列表

**测试目的**: 验证获取项目列表功能

**请求示例**:
```json
{
  "action": "project.list",
  "request_id": "TC005_001",
  "data": {
    "status": "in_progress",
    "keyword": "",
    "page": 1,
    "page_size": 20
  }
}
```

**预期响应**:
```json
{
  "action": "project.list",
  "request_id": "TC005_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "project_uuid",
        "project_no": "PRJ-20260330-xxxxx",
        "name": "项目名称",
        "description": "项目描述",
        "status": "in_progress",
        "created_at": "2026-03-30T16:13:23"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] items 为数组
- [ ] total >= 0
- [ ] 分页参数正确

---

#### TC006: project.get - 获取项目详情

**测试目的**: 验证获取单个项目的详细信息

**请求示例**:
```json
{
  "action": "project.get",
  "request_id": "TC006_001",
  "data": {
    "project_id": "project_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "project.get",
  "request_id": "TC006_001",
  "code": 0,
  "message": "success",
  "data": {
    "project": {...},
    "milestones": [],
    "members": [],
    "deliverables": []
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] project 对象包含所有字段
- [ ] milestones/members/deliverables 为数组

---

#### TC007: project.update - 更新项目信息

**测试目的**: 验证更新项目基本信息

**请求示例**:
```json
{
  "action": "project.update",
  "request_id": "TC007_001",
  "data": {
    "project_id": "project_uuid",
    "name": "更新后的项目名称",
    "description": "更新后的描述"
  }
}
```

**预期响应**:
```json
{
  "action": "project.update",
  "request_id": "TC007_001",
  "code": 0,
  "message": "项目更新成功",
  "data": {
    "id": "project_uuid",
    "name": "更新后的项目名称",
    "description": "更新后的描述",
    "updated_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] name 和 description 已更新
- [ ] updated_at 为最新时间

---

#### TC008: project.update_status - 更新项目状态

**测试目的**: 验证更新项目状态功能

**请求示例**:
```json
{
  "action": "project.update_status",
  "request_id": "TC008_001",
  "data": {
    "project_id": "project_uuid",
    "status": "completed"
  }
}
```

**有效状态值**: `in_progress` | `completed` | `ignored`

**预期响应**:
```json
{
  "action": "project.update_status",
  "request_id": "TC008_001",
  "code": 0,
  "message": "状态更新成功",
  "data": {
    "id": "project_uuid",
    "status": "completed",
    "updated_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] status 已更新
- [ ] 无效状态值返回 400

---

### 3.3 里程碑接口 (Milestone)

#### TC009: milestone.create - 创建里程碑

**测试目的**: 验证创建里程碑功能

**请求示例**:
```json
{
  "action": "milestone.create",
  "request_id": "TC009_001",
  "data": {
    "project_id": "project_uuid",
    "name": "需求分析阶段",
    "description": "完成需求调研和分析",
    "type": "phase",
    "deadline": "2026-12-31"
  }
}
```

**有效类型值**: `milestone` | `phase` | `acceptance`

**预期响应**:
```json
{
  "action": "milestone.create",
  "request_id": "TC009_001",
  "code": 0,
  "message": "里程碑创建成功",
  "data": {
    "id": "milestone_uuid",
    "project_id": "project_uuid",
    "type": "phase",
    "name": "需求分析阶段",
    "status": "created",
    "created_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 返回里程碑 id
- [ ] status = "created"

---

#### TC010: milestone.list - 获取里程碑列表

**测试目的**: 验证获取项目的里程碑列表

**请求示例**:
```json
{
  "action": "milestone.list",
  "request_id": "TC010_001",
  "data": {
    "project_id": "project_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "milestone.list",
  "request_id": "TC010_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "milestone_uuid",
        "project_id": "project_uuid",
        "type": "phase",
        "name": "需求分析阶段",
        "status": "created",
        "created_at": "2026-03-30T16:13:23"
      }
    ],
    "total": 1
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] items 为数组
- [ ] total 数量正确

---

#### TC011: milestone.get - 获取里程碑详情

**测试目的**: 验证获取单个里程碑的详细信息

**请求示例**:
```json
{
  "action": "milestone.get",
  "request_id": "TC011_001",
  "data": {
    "milestone_id": "milestone_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "milestone.get",
  "request_id": "TC011_001",
  "code": 0,
  "message": "success",
  "data": {
    "id": "milestone_uuid",
    "project_id": "project_uuid",
    "type": "phase",
    "name": "需求分析阶段",
    "status": "created",
    "created_at": "2026-03-30T16:13:23",
    "updated_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 所有字段完整

---

#### TC012: milestone.update - 更新里程碑

**测试目的**: 验证更新里程碑信息

**请求示例**:
```json
{
  "action": "milestone.update",
  "request_id": "TC012_001",
  "data": {
    "milestone_id": "milestone_uuid",
    "name": "更新后的名称",
    "description": "更新后的描述",
    "status": "in_progress"
  }
}
```

**有效状态值**: `created` | `waiting` | `paused` | `completed`

**预期响应**:
```json
{
  "action": "milestone.update",
  "request_id": "TC012_001",
  "code": 0,
  "message": "里程碑更新成功",
  "data": {
    "id": "milestone_uuid",
    "name": "更新后的名称",
    "status": "in_progress",
    "updated_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 字段已更新

---

#### TC013: milestone.logs - 获取里程碑日志

**测试目的**: 验证获取里程碑操作日志

**请求示例**:
```json
{
  "action": "milestone.logs",
  "request_id": "TC013_001",
  "data": {
    "milestone_id": "milestone_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "milestone.logs",
  "request_id": "TC013_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "log_uuid",
        "milestone_id": "milestone_uuid",
        "user_id": "user_uuid",
        "username": "admin",
        "action": "创建里程碑",
        "created_at": "2026-03-30T16:13:23"
      }
    ],
    "total": 1
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] items 为数组
- [ ] 包含操作日志

---

#### TC014: milestone.add_log - 添加里程碑日志

**测试目的**: 验证添加里程碑操作日志

**请求示例**:
```json
{
  "action": "milestone.add_log",
  "request_id": "TC014_001",
  "data": {
    "milestone_id": "milestone_uuid",
    "action": "更新状态",
    "description": "状态改为进行中"
  }
}
```

**预期响应**:
```json
{
  "action": "milestone.add_log",
  "request_id": "TC014_001",
  "code": 0,
  "message": "日志添加成功",
  "data": {
    "id": "log_uuid",
    "milestone_id": "milestone_uuid",
    "action": "更新状态",
    "description": "状态改为进行中",
    "created_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 返回日志 id

---

### 3.4 产出物接口 (Deliverable)

#### TC015: deliverable.upload - 关联产出物

**测试目的**: 验证将已上传文件关联到项目/里程碑

**前置条件**: 先通过 HTTP API 上传文件获得 deliverable_id

**请求示例**:
```json
{
  "action": "deliverable.upload",
  "request_id": "TC015_001",
  "data": {
    "project_id": "project_uuid",
    "milestone_id": "milestone_uuid",
    "deliverable_id": "deliverable_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "deliverable.upload",
  "request_id": "TC015_001",
  "code": 0,
  "message": "产出物关联成功",
  "data": {
    "id": "deliverable_uuid",
    "name": "stored_name.pdf",
    "original_name": "原始名称.pdf",
    "file_size": 1024000,
    "project_id": "project_uuid",
    "milestone_id": "milestone_uuid",
    "created_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 关联成功

---

#### TC016: deliverable.list - 获取产出物列表

**测试目的**: 验证获取项目/里程碑的产出物列表

**请求示例**:
```json
{
  "action": "deliverable.list",
  "request_id": "TC016_001",
  "data": {
    "project_id": "project_uuid",
    "milestone_id": "milestone_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "deliverable.list",
  "request_id": "TC016_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "deliverable_uuid",
        "name": "stored_name.pdf",
        "original_name": "原始名称.pdf",
        "file_size": 1024000,
        "file_type": "application/pdf",
        "created_at": "2026-03-30T16:13:23"
      }
    ],
    "total": 1
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] items 为数组

---

#### TC017: deliverable.download - 获取下载信息

**测试目的**: 验证获取产出物下载链接

**请求示例**:
```json
{
  "action": "deliverable.download",
  "request_id": "TC017_001",
  "data": {
    "deliverable_id": "deliverable_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "deliverable.download",
  "request_id": "TC017_001",
  "code": 0,
  "message": "success",
  "data": {
    "deliverable_id": "deliverable_uuid",
    "original_name": "原始名称.pdf",
    "download_url": "/api/v1/deliverables/deliverable_uuid/download"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] download_url 不为空

---

### 3.5 项目成员接口 (Project Member)

#### TC018: project.add_member - 添加项目成员

**测试目的**: 验证添加用户到项目

**请求示例**:
```json
{
  "action": "project.add_member",
  "request_id": "TC018_001",
  "data": {
    "project_id": "project_uuid",
    "user_id": "target_user_uuid",
    "display_name": "张三",
    "roles": ["开发", "测试"]
  }
}
```

**预期响应**:
```json
{
  "action": "project.add_member",
  "request_id": "TC018_001",
  "code": 0,
  "message": "成员添加成功",
  "data": {
    "id": "member_uuid",
    "project_id": "project_uuid",
    "user_id": "target_user_uuid",
    "display_name": "张三",
    "roles": ["开发", "测试"]
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 成员添加成功

---

#### TC019: project.remove_member - 移除项目成员

**测试目的**: 验证从项目移除用户

**请求示例**:
```json
{
  "action": "project.remove_member",
  "request_id": "TC019_001",
  "data": {
    "project_id": "project_uuid",
    "user_id": "target_user_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "project.remove_member",
  "request_id": "TC019_001",
  "code": 0,
  "message": "成员移除成功",
  "data": null
}
```

**验证点**:
- [ ] code = 0
- [ ] 成员移除成功

---

### 3.6 用户接口 (User)

#### TC020: user.profile - 获取用户信息

**测试目的**: 验证获取当前用户信息

**请求示例**:
```json
{
  "action": "user.profile",
  "request_id": "TC020_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "user.profile",
  "request_id": "TC020_001",
  "code": 0,
  "message": "success",
  "data": {
    "id": "user_uuid",
    "username": "admin",
    "display_name": "系统管理员",
    "email": "admin@example.com",
    "is_active": true,
    "roles": [
      {
        "code": "SYSTEM_ADMIN",
        "name": "系统管理员"
      }
    ]
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 用户信息完整

---

#### TC021: user.update_profile - 更新用户信息

**测试目的**: 验证更新当前用户信息

**请求示例**:
```json
{
  "action": "user.update_profile",
  "request_id": "TC021_001",
  "data": {
    "display_name": "新显示名称",
    "email": "new@example.com"
  }
}
```

**预期响应**:
```json
{
  "action": "user.update_profile",
  "request_id": "TC021_001",
  "code": 0,
  "message": "用户信息更新成功",
  "data": {
    "id": "user_uuid",
    "username": "admin",
    "display_name": "新显示名称",
    "email": "new@example.com",
    "updated_at": "2026-03-30T16:13:23"
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 信息已更新

---

### 3.7 消息接口 (Message)

#### TC022: message.list - 获取消息列表

**测试目的**: 验证获取用户消息列表

**请求示例**:
```json
{
  "action": "message.list",
  "request_id": "TC022_001",
  "data": {
    "is_read": 0,
    "page": 1,
    "page_size": 20
  }
}
```

**预期响应**:
```json
{
  "action": "message.list",
  "request_id": "TC022_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "message_uuid",
        "title": "消息标题",
        "content": "消息内容",
        "type": "info",
        "is_read": 0,
        "created_at": "2026-03-30T16:13:23"
      }
    ],
    "total": 10,
    "unread_count": 5,
    "page": 1,
    "page_size": 20
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] 分页信息正确
- [ ] unread_count 准确

---

#### TC023: message.unread_count - 获取未读数量

**测试目的**: 验证获取未读消息数量

**请求示例**:
```json
{
  "action": "message.unread_count",
  "request_id": "TC023_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "message.unread_count",
  "request_id": "TC023_001",
  "code": 0,
  "message": "success",
  "data": {
    "unread_count": 5
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] unread_count 为数字

---

#### TC024: message.mark_read - 标记消息已读

**测试目的**: 验证标记单条消息为已读

**请求示例**:
```json
{
  "action": "message.mark_read",
  "request_id": "TC024_001",
  "data": {
    "message_id": "message_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "message.mark_read",
  "request_id": "TC024_001",
  "code": 0,
  "message": "标记成功",
  "data": null
}
```

**验证点**:
- [ ] code = 0

---

#### TC025: message.mark_all_read - 标记全部已读

**测试目的**: 验证标记所有消息为已读

**请求示例**:
```json
{
  "action": "message.mark_all_read",
  "request_id": "TC025_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "message.mark_all_read",
  "request_id": "TC025_001",
  "code": 0,
  "message": "标记成功",
  "data": {
    "count": 10
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] count 为标记的数量

---

#### TC026: message.delete - 删除消息

**测试目的**: 验证删除消息

**请求示例**:
```json
{
  "action": "message.delete",
  "request_id": "TC026_001",
  "data": {
    "message_id": "message_uuid"
  }
}
```

**预期响应**:
```json
{
  "action": "message.delete",
  "request_id": "TC026_001",
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

**验证点**:
- [ ] code = 0

---

### 3.8 管理员接口 (Admin)

#### TC027: admin.user_list - 获取用户列表

**测试目的**: 验证管理员获取所有用户列表

**权限**: SYSTEM_ADMIN

**请求示例**:
```json
{
  "action": "admin.user_list",
  "request_id": "TC027_001",
  "data": {}
}
```

**预期响应**:
```json
{
  "action": "admin.user_list",
  "request_id": "TC027_001",
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "user_uuid",
        "username": "admin",
        "display_name": "系统管理员",
        "email": "admin@example.com",
        "is_active": true,
        "created_at": "2026-01-01T00:00:00"
      }
    ],
    "total": 5
  }
}
```

**验证点**:
- [ ] code = 0
- [ ] items 为数组
- [ ] 非管理员访问返回 403

---

#### TC028: admin.update_user_roles - 更新用户角色

**测试目的**: 验证管理员更新用户角色

**权限**: SYSTEM_ADMIN

**请求示例**:
```json
{
  "action": "admin.update_user_roles",
  "request_id": "TC028_001",
  "data": {
    "user_id": "target_user_uuid",
    "roles": ["ADMIN", "WORKER"]
  }
}
```

**预期响应**:
```json
{
  "action": "admin.update_user_roles",
  "request_id": "TC028_001",
  "code": 0,
  "message": "角色更新成功",
  "data": null
}
```

**验证点**:
- [ ] code = 0
- [ ] 非管理员访问返回 403

---

## 四、完整测试代码

### 4.1 Python 测试客户端

```python
"""
YourWork WebSocket API 完整测试客户端
覆盖所有 28 个 WebSocket API 接口
"""
import asyncio
import websockets
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

# 配置
WS_URL = "ws://localhost:8001/ws"
DB_PATH = "data/yourwork.db"


class WebSocketAPITester:
    """WebSocket API 测试类"""

    def __init__(self, token: str):
        self.token = token
        self.url = f"{WS_URL}?token={token}"
        self.websocket = None
        self.test_results = []
        self.project_id = None
        self.milestone_id = None

    async def connect(self):
        """建立 WebSocket 连接"""
        print(f"连接到: {self.url}")
        self.websocket = await websockets.connect(self.url)
        print("✅ 连接成功\n")

    async def disconnect(self):
        """断开 WebSocket 连接"""
        if self.websocket:
            await self.websocket.close()
            print("✅ 连接已断开")

    async def send_request(self, action: str, data: Dict[str, Any], request_id: str = None) -> Dict:
        """发送 WebSocket 请求"""
        if not request_id:
            request_id = f"{action}_{int(datetime.now().timestamp())}"

        request = {
            "action": action,
            "request_id": request_id,
            "data": data
        }

        print(f"📤 发送: {action}")
        print(f"   数据: {json.dumps(data, ensure_ascii=False)}")

        await self.websocket.send(json.dumps(request))
        response_text = await asyncio.wait_for(self.websocket.recv(), timeout=10)
        response = json.loads(response_text)

        print(f"📥 响应: code={response.get('code')}, message={response.get('message')}")

        # 记录测试结果
        self.test_results.append({
            "action": action,
            "request_id": request_id,
            "code": response.get("code"),
            "success": response.get("code") == 0
        })

        return response

    def print_summary(self):
        """打印测试摘要"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed

        print("\n" + "=" * 80)
        print("测试摘要")
        print("=" * 80)
        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  ❌ {r['action']} (request_id: {r['request_id']})")
        print("=" * 80)

    async def run_all_tests(self):
        """运行所有测试"""
        try:
            await self.connect()

            # ========== 系统接口测试 ==========
            print("\n" + "="*80)
            print("【系统接口测试】")
            print("="*80)

            await self.test_system_ping()
            await self.test_system_capabilities()
            # 登出测试放在最后，因为会撤销会话
            # await self.test_system_logout()

            # ========== 项目管理测试 ==========
            print("\n" + "="*80)
            print("【项目管理测试】")
            print("="*80)

            await self.test_project_list()
            await self.test_project_create()
            await self.test_project_get()
            await self.test_project_update()
            await self.test_project_update_status()

            # ========== 里程碑测试 ==========
            print("\n" + "="*80)
            print("【里程碑测试】")
            print("="*80)

            await self.test_milestone_create()
            await self.test_milestone_list()
            await self.test_milestone_get()
            await self.test_milestone_update()
            await self.test_milestone_logs()
            await self.test_milestone_add_log()

            # ========== 产出物测试 ==========
            print("\n" + "="*80)
            print("【产出物测试】")
            print("="*80)

            await self.test_deliverable_list()

            # ========== 项目成员测试 ==========
            print("\n" + "="*80)
            print("【项目成员测试】")
            print("="*80)

            await self.test_project_add_member()
            await self.test_project_remove_member()

            # ========== 用户接口测试 ==========
            print("\n" + "="*80)
            print("【用户接口测试】")
            print("="*80)

            await self.test_user_profile()
            await self.test_user_update_profile()

            # ========== 消息接口测试 ==========
            print("\n" + "="*80)
            print("【消息接口测试】")
            print("="*80)

            await self.test_message_unread_count()
            await self.test_message_list()
            await self.test_message_mark_all_read()

            # ========== 管理员接口测试 ==========
            print("\n" + "="*80)
            print("【管理员接口测试】")
            print("="*80)

            await self.test_admin_user_list()

            # 打印测试摘要
            self.print_summary()

        finally:
            await self.disconnect()

    # ========== 具体测试方法 ==========

    async def test_system_ping(self):
        """TC003: system.ping"""
        response = await self.send_request("system.ping", {})
        assert response["code"] == 0
        assert response["message"] == "pong"

    async def test_system_capabilities(self):
        """TC002: system.capabilities"""
        response = await self.send_request("system.capabilities", {})
        assert response["code"] == 0
        assert "capabilities" in response["data"]

    async def test_system_logout(self):
        """TC004: system.logout"""
        response = await self.send_request("system.logout", {
            "session_token": self.token
        })
        assert response["code"] == 0
        print("   ⚠️  注意：会话已撤销，后续测试将失败")

    async def test_project_list(self):
        """TC005: project.list"""
        response = await self.send_request("project.list", {
            "page": 1,
            "page_size": 10
        })
        assert response["code"] == 0
        assert "items" in response["data"]

    async def test_project_create(self):
        """TC004: project.create"""
        response = await self.send_request("project.create", {
            "name": f"WebSocket测试项目_{datetime.now().strftime('%H%M%S')}",
            "description": "通过 WebSocket API 创建"
        })
        assert response["code"] == 0
        self.project_id = response["data"]["id"]
        print(f"   📝 创建的项目ID: {self.project_id}")

    async def test_project_get(self):
        """TC006: project.get"""
        if not self.project_id:
            print("   ⚠️  跳过：需要先创建项目")
            return
        response = await self.send_request("project.get", {
            "project_id": self.project_id
        })
        assert response["code"] == 0

    async def test_project_update(self):
        """TC007: project.update"""
        if not self.project_id:
            return
        response = await self.send_request("project.update", {
            "project_id": self.project_id,
            "name": "更新后的项目名称",
            "description": "更新后的描述"
        })
        assert response["code"] == 0

    async def test_project_update_status(self):
        """TC008: project.update_status"""
        if not self.project_id:
            return
        response = await self.send_request("project.update_status", {
            "project_id": self.project_id,
            "status": "completed"
        })
        assert response["code"] == 0

    async def test_milestone_create(self):
        """TC009: milestone.create"""
        if not self.project_id:
            print("   ⚠️  跳过：需要先创建项目")
            return
        response = await self.send_request("milestone.create", {
            "project_id": self.project_id,
            "name": f"测试里程碑_{datetime.now().strftime('%H%M%S')}",
            "description": "通过 WebSocket API 创建",
            "type": "milestone"
        })
        assert response["code"] == 0
        self.milestone_id = response["data"]["id"]
        print(f"   📝 创建的里程碑ID: {self.milestone_id}")

    async def test_milestone_list(self):
        """TC010: milestone.list"""
        if not self.project_id:
            return
        response = await self.send_request("milestone.list", {
            "project_id": self.project_id
        })
        assert response["code"] == 0

    async def test_milestone_get(self):
        """TC011: milestone.get"""
        if not self.milestone_id:
            return
        response = await self.send_request("milestone.get", {
            "milestone_id": self.milestone_id
        })
        assert response["code"] == 0

    async def test_milestone_update(self):
        """TC012: milestone.update"""
        if not self.milestone_id:
            return
        response = await self.send_request("milestone.update", {
            "milestone_id": self.milestone_id,
            "status": "completed"
        })
        assert response["code"] == 0

    async def test_milestone_logs(self):
        """TC013: milestone.logs"""
        if not self.milestone_id:
            return
        response = await self.send_request("milestone.logs", {
            "milestone_id": self.milestone_id
        })
        assert response["code"] == 0

    async def test_milestone_add_log(self):
        """TC014: milestone.add_log"""
        if not self.milestone_id:
            return
        response = await self.send_request("milestone.add_log", {
            "milestone_id": self.milestone_id,
            "action": "测试操作",
            "description": "通过 WebSocket API 添加日志"
        })
        assert response["code"] == 0

    async def test_deliverable_list(self):
        """TC016: deliverable.list"""
        if not self.project_id:
            return
        response = await self.send_request("deliverable.list", {
            "project_id": self.project_id
        })
        assert response["code"] == 0

    async def test_project_add_member(self):
        """TC018: project.add_member"""
        if not self.project_id:
            return
        # 获取一个普通用户
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id FROM users WHERE username != 'admin' LIMIT 1"
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            print("   ⚠️  跳过：需要其他用户")
            return

        response = await self.send_request("project.add_member", {
            "project_id": self.project_id,
            "user_id": user["id"],
            "display_name": "测试成员",
            "roles": ["开发者"]
        })
        assert response["code"] == 0

    async def test_project_remove_member(self):
        """TC019: project.remove_member"""
        if not self.project_id:
            return
        # 这个测试需要先有成员，暂时跳过
        print("   ⚠️  跳过：需要先添加成员")

    async def test_user_profile(self):
        """TC020: user.profile"""
        response = await self.send_request("user.profile", {})
        assert response["code"] == 0

    async def test_user_update_profile(self):
        """TC021: user.update_profile"""
        response = await self.send_request("user.update_profile", {
            "display_name": "WebSocket测试用户"
        })
        assert response["code"] == 0

    async def test_message_unread_count(self):
        """TC023: message.unread_count"""
        response = await self.send_request("message.unread_count", {})
        assert response["code"] == 0

    async def test_message_list(self):
        """TC022: message.list"""
        response = await self.send_request("message.list", {
            "page": 1,
            "page_size": 20
        })
        assert response["code"] == 0

    async def test_message_mark_all_read(self):
        """TC025: message.mark_all_read"""
        response = await self.send_request("message.mark_all_read", {})
        assert response["code"] == 0

    async def test_admin_user_list(self):
        """TC027: admin.user_list"""
        response = await self.send_request("admin.user_list", {})
        assert response["code"] == 0


def get_admin_token() -> str:
    """获取管理员会话令牌"""
    import requests
    try:
        response = requests.post('http://localhost:8001/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        data = response.json()
        if data['code'] == 0:
            return data['data']['session_token']
        return ""
    except Exception as e:
        print(f"❌ 获取令牌失败: {e}")
        return ""


async def main():
    """主函数"""
    print("="*80)
    print("YourWork WebSocket API 完整测试")
    print("="*80)

    # 获取管理员 token
    token = get_admin_token()
    if not token:
        print("❌ 错误：无法获取 admin 用户 token")
        return

    print(f"使用会话令牌: {token[:16]}...\n")

    # 运行测试
    tester = WebSocketAPITester(token)
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
```

---

## 五、测试执行指南

### 5.1 快速开始

```bash
# 1. 确保 YourWork 服务正在运行
python main.py

# 2. 在另一个终端运行测试
python test_websocket_full.py
```

### 5.2 预期输出

```
================================================================================
YourWork WebSocket API 完整测试
================================================================================
使用会话令牌: 1a2b3c4d5e6f7g8h...

连接到: ws://localhost:8001/ws?token=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3g4h5i6j7k8
✅ 连接成功

================================================================================
【系统接口测试】
================================================================================
📤 发送: system.ping
📥 响应: code=0, message=pong
📤 发送: system.capabilities
📥 响应: code=0, message=success
...

================================================================================
测试摘要
================================================================================
总计: 29 | 通过: 29 | 失败: 0
通过率: 100.0%
================================================================================
```

---

## 六、错误码说明

| 错误码 | 说明 | 处理建议 |
|--------|------|---------|
| 0 | 成功 | - |
| 400 | 请求参数错误 | 检查请求参数格式和内容 |
| 401 | 未登录或会话过期 | 重新登录获取新会话令牌 |
| 403 | 无权限 | 检查用户角色权限 |
| 404 | 资源不存在 | 确认资源 ID 是否正确 |
| 500 | 服务器内部错误 | 联系系统管理员 |

---

## 七、附录

### 7.1 测试数据清理

测试完成后，可以清理测试数据：

```sql
-- 删除测试项目
DELETE FROM projects WHERE name LIKE 'WebSocket测试项目%';

-- 删除测试日志
DELETE FROM ws_logs WHERE request_id LIKE 'TC%';

-- 清理测试会话（可选）
DELETE FROM sessions WHERE created_at > datetime('now', '-1 day');
```

### 7.2 会话测试高级场景

**测试会话过期**：
```python
# 手动将会话设置为已过期
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/yourwork.db')
conn.execute(
    "UPDATE sessions SET expires_at = ? WHERE token = ?",
    ((datetime.now() - timedelta(hours=1)).isoformat(), session_token)
)
conn.commit()
conn.close()

# 现在尝试使用该令牌应该失败
```

**测试会话撤销**：
```python
# 撤销当前会话
await tester.test_system_logout()

# 尝试使用已撤销的令牌应该返回401
response = await tester.send_request("system.ping", {})
assert response["code"] == 401
```

**测试多设备登录**：
```python
# 同一用户在不同设备登录
token1 = await get_session_token()
token2 = await get_session_token()

# 两个令牌都应该有效
# 旧令牌不会被自动撤销（系统允许多个并发会话）
```

### 7.3 联系方式

如有问题或建议，请联系开发团队。
