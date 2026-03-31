<div align="center">

# YourWork

**企业级项目管理系统**

极简架构 · 零 ORM · 两个外部依赖

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[功能特性](#-功能特性) · [快速开始](#-快速开始) · [技术架构](#-技术架构) · [API 文档](#-api-文档) · [部署](#-生产环境部署)

</div>

---

## 简介

YourWork 是一个面向中小团队的企业项目管理系统，使用 Python + FastAPI 构建。所有业务逻辑集中在单个 `main.py` 文件中（~2500 行），追求透明、可维护的极简架构设计。

**核心设计理念：**
- 仅 **2 个外部依赖**（FastAPI + uvicorn），其余全部使用 Python 内置模块
- **无 ORM**，直接使用 sqlite3 操作 SQLite 数据库
- **无模板引擎**，纯 HTML + 原生 JavaScript 前端
- **单文件架构**，所有后端业务逻辑在一个文件中，便于审查和理解

## 功能特性

- **用户与权限** — 基于 RBAC 的角色权限管理（系统管理员 / 管理员 / 工作人员）
- **项目管理** — 项目创建、成员管理、状态追踪（进行中 / 已完成 / 已归档）
- **里程碑系统** — 支持任务、交付物、阶段三种类型，带依赖关系和状态机验证
- **实时通信** — WebSocket 支持即时消息推送、心跳检测、会话管理
- **文件管理** — 项目交付物上传、下载、版本管理
- **消息通知** — 站内消息系统，支持已读/未读状态
- **安全认证** — 64 位随机 Token 会话管理，支持过期和吊销
- **API 文档** — 自动生成 Swagger UI 文档
- **审计日志** — 全量 API 调用和 WebSocket 操作日志

## 快速开始

### 环境要求

- Python 3.12+
- pip

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/shanxuchen/YourWork.git
cd YourWork

# 2. 安装依赖（仅两个）
pip install -r requirements.txt

# 3. 初始化数据库
python init_db.py

# 4. 启动服务
python main.py
```

服务启动后访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8001 | 主应用 |
| http://localhost:8001/docs | API 文档（Swagger UI） |
| ws://localhost:8001/ws?token={token} | WebSocket 连接 |

默认管理员账号：`admin` / `admin123`

> 也可以使用 `start.bat`（Windows）或 `start.sh`（Linux/macOS）一键启动。

## 技术架构

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| 数据库 | SQLite（Python 内置 sqlite3） |
| 前端 | 原生 HTML / CSS / JavaScript |
| 实时通信 | WebSocket（FastAPI 原生支持） |
| 密码加密 | hashlib（Python 内置） |
| 日志 | logging（Python 内置） |

### 目录结构

```
YourWork/
├── main.py              # 核心业务逻辑（~2500 行，所有 API 路由和处理函数）
├── session.py           # 会话管理模块（Token 生成、验证、吊销）
├── init_db.py           # 数据库初始化脚本
├── requirements.txt     # 依赖声明（FastAPI + uvicorn）
├── websocket/           # WebSocket 模块
│   ├── manager.py       # 连接生命周期、心跳、会话管理
│   ├── handlers.py      # 消息路由（ACTION_HANDLERS 字典分发）
│   ├── auth.py          # WebSocket 认证
│   └── schemas.py       # 消息模型与常量定义
├── templates/           # HTML 页面模板
│   ├── admin/           # 管理后台页面
│   ├── project/         # 项目管理页面
│   ├── milestone/       # 里程碑页面
│   └── message/         # 消息页面
├── static/              # 静态资源
│   ├── css/
│   ├── js/
│   │   └── modules/     # JavaScript 模块
│   └── img/
├── doc/                 # 项目文档
├── data/                # SQLite 数据库（运行时生成）
├── uploads/             # 用户上传文件（运行时生成）
└── logs/                # 应用日志（运行时生成）
```

### 里程碑状态机

```
PENDING ──→ IN_PROGRESS ──→ COMPLETED
  ↑            │    ↑            │
  └────────────┘    └────────────┘
                    │
                    ↓
              CANCELLED
```

- `PENDING` → `IN_PROGRESS`：始终允许
- `IN_PROGRESS` → `COMPLETED`：所有依赖里程碑必须已完成
- 回退和取消操作需检查是否有其他里程碑依赖当前节点

### 认证流程

```
登录 → create_session() → 64位随机Token → Cookie存储
  ↓
请求 → get_current_user() → validate_session() → 验证Token有效性
  ↓
WebSocket → authenticate_websocket() → validate_session() → 建立长连接
  ↓
登出 → revoke_session() → 标记Token已吊销
```

## API 文档

API 基础路径：`/api/v1`

启动服务后访问 [http://localhost:8001/docs](http://localhost:8001/docs) 查看完整的 Swagger UI 文档。

主要 API 端点：

| 模块 | 端点前缀 | 说明 |
|------|----------|------|
| 用户认证 | `/api/v1/auth/*` | 登录、登出、会话管理 |
| 用户管理 | `/api/v1/users/*` | 用户 CRUD、角色分配 |
| 项目管理 | `/api/v1/projects/*` | 项目 CRUD、成员管理 |
| 里程碑 | `/api/v1/milestones/*` | 里程碑 CRUD、状态变更、依赖管理 |
| 交付物 | `/api/v1/deliverables/*` | 文件上传下载 |
| 消息 | `/api/v1/messages/*` | 站内消息通知 |

响应格式：`{"code": 0, "message": "...", "data": {...}}`

## 生产环境部署

详细部署指南请参阅 [INSTALL.md](INSTALL.md)。

关键配置项（位于 `main.py` 顶部）：

```python
DB_PATH = "data/yourwork.db"                    # 数据库路径
LOG_PATH = "logs/app.log"                       # 日志路径
UPLOAD_PATH = "uploads/projects"                # 上传目录
SESSION_TOKEN_LENGTH = 64                       # Token 长度
SESSION_DEFAULT_DURATION_HOURS = 24             # 会话有效期
SESSION_CLEANUP_INTERVAL_MINUTES = 60           # 过期会话清理间隔
```

## 技术支持

- 查看日志：`logs/app.log`
- API 文档：http://localhost:8001/docs
- 详细安装指南：[INSTALL.md](INSTALL.md)
- 开发指南：[CLAUDE.md](CLAUDE.md)

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

Copyright (c) 2026 Shanxuchen
