# YourWork 安装指南

## 系统要求

- Python 3.12 或更高版本
- 操作系统：Windows / Linux / macOS
- 至少 100MB 可用磁盘空间

## 快速安装

### 1. 获取源代码

```bash
git clone <repository-url>
cd YourWork
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖列表**（仅两个外部库）：
- `fastapi` - Web框架
- `uvicorn` - ASGI服务器

其他所有功能使用Python内置模块实现。

### 3. 初始化数据库

```bash
python init_db.py
```

这将：
- 创建 `data/` 目录和数据库文件
- 创建所有必需的数据表
- 插入默认角色（SYSTEM_ADMIN, ADMIN, WORKER）
- 创建默认管理员账号：`admin` / `admin123`
- 插入测试数据（可选）

### 4. 启动服务

**Windows:**
```bash
start.bat
```

**Linux/macOS:**
```bash
./start.sh
```

**或直接运行:**
```bash
python main.py
```

### 5. 访问应用

服务启动后，访问以下地址：

| 地址 | 说明 |
|------|------|
| http://localhost:8001 | 主应用 |
| http://localhost:8001/docs | API文档（Swagger UI） |
| ws://localhost:8001/ws | WebSocket连接 |

**默认登录账号:**
- 用户名：`admin`
- 密码：`admin123`

## 目录结构说明

安装后会创建以下目录结构：

```
YourWork/
├── data/               # 数据库目录（自动创建）
│   └── yourwork.db    # SQLite数据库文件
├── logs/               # 日志目录（自动创建）
│   └── app.log        # 应用日志
├── uploads/            # 文件上传目录（自动创建）
│   └── projects/       # 项目产出物存储
│       └── {project_id}/
│           └── {milestone_id}/
├── static/             # 静态资源目录（自动创建）
│   ├── css/
│   ├── js/
│   └── img/
├── templates/          # HTML模板（自动创建）
│   ├── admin/
│   ├── message/
│   ├── milestone/
│   └── project/
└── websocket/          # WebSocket模块
```

## 验证安装

### 1. 检查数据库

```bash
python -c "import sqlite3; conn = sqlite3.connect('data/yourwork.db'); print('数据库表:', [t[0] for t in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"
```

预期输出包含：`users`, `roles`, `projects`, `milestones`, `sessions` 等14个表。

### 2. 检查API

访问 http://localhost:8001/docs，应该能看到完整的API文档界面。

### 3. 运行测试

```bash
# 运行所有测试
python test/test_runner.py

# 运行特定类型测试
python test/test_runner.py --type unit
python test/test_runner.py --type integration
python test/test_runner.py --type system

# 运行WebSocket测试
python test/run_websocket_tests.py
```

## 生产环境部署

### 配置端口

编辑 `main.py` 中的启动配置：

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",      # 监听所有网络接口
        port=8001,           # 修改为其他端口
        reload=False         # 生产环境关闭自动重载
    )
```

### 日志配置

默认日志级别为 INFO，可在 `main.py` 中调整：

```python
logging.basicConfig(
    level=logging.INFO,     # 改为 logging.DEBUG 获取详细日志
    format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

### 数据库备份

定期备份 `data/yourwork.db` 文件：

```bash
# Windows
xcopy data\yourwork.db data\backup\yourwork_%date%.db

# Linux/macOS
cp data/yourwork.db data/backup/yourwork_$(date +%Y%m%d).db
```

### 会话管理

默认会话有效期为24小时，可在 `main.py` 中修改：

```python
SESSION_DEFAULT_DURATION_HOURS = 24  # 修改小时数
```

会话清理间隔：
```python
SESSION_CLEANUP_INTERVAL_MINUTES = 60  # 每60分钟清理一次过期会话
```

## 故障排查

### 端口被占用

**错误信息**: `Address already in use`

**解决方案**:
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <进程ID> /F

# Linux/macOS
lsof -ti:8001 | xargs kill -9
```

### 数据库锁定

**错误信息**: `database is locked`

**解决方案**: 确保只有一个服务实例在运行，或等待超时。

### 权限错误

**错误信息**: `Permission denied`

**解决方案**: 确保有写入 `data/`、`logs/`、`uploads/` 目录的权限。

```bash
# Linux/macOS
chmod +w data logs uploads
```

## 升级指南

### 从旧版本升级

1. **备份数据库**
   ```bash
   cp data/yourwork.db data/yourwork.db.backup
   ```

2. **更新代码**
   ```bash
   git pull
   ```

3. **更新依赖**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **数据库迁移（如有）**
   ```bash
   # 如果有新的数据库迁移脚本
   python migrations/migrate_xxx.py
   ```

5. **重启服务**

### 数据库变更说明

当前版本 (v1.0) 数据库schema：

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| users | 用户表 | id, username, password, display_name |
| roles | 角色表 | id, code (SYSTEM_ADMIN/ADMIN/WORKER) |
| user_roles | 用户角色关联 | user_id, role_id |
| sessions | 会话表 | token, user_id, expires_at, is_revoked |
| projects | 项目表 | id, status (in_progress/completed/ignored/archived) |
| project_members | 项目成员 | project_id, user_id |
| milestones | 里程碑表 | id, project_id, status, type |
| milestone_items | 里程碑行动项 | id, milestone_id, status |
| milestone_dependencies | 里程碑依赖 | milestone_id, depends_on_id |
| milestone_logs | 里程碑日志 | milestone_id, action |
| deliverables | 产出物 | id, project_id, file_path |
| messages | 消息表 | user_id, is_read |
| ws_logs | WebSocket日志 | user_id, action |

## 卸载

### 完全卸载

1. **停止服务**

2. **删除文件**（可选，保留数据）
   ```bash
   # 仅删除应用代码，保留数据
   rm -rf YourWork/

   # 或包含数据目录全部删除
   rm -rf YourWork/ data/ logs/ uploads/
   ```

3. **卸载Python包**（可选）
   ```bash
   pip uninstall fastapi uvicorn
   ```

## 技术支持

- 查看日志: `logs/app.log`
- API文档: http://localhost:8001/docs
- 项目文档: `doc/` 目录
