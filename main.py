"""
YourWork - 企业项目管理系统
主程序 - 所有代码在这里，清晰可追踪
"""

# ===== 标准库导入 =====
import sqlite3
import hashlib
import json
import logging
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# ===== 第三方库导入（仅 FastAPI）=====
from fastapi import FastAPI, Request, Response, Form, File, UploadFile, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ===== 配置常量 =====
DB_PATH = "data/yourwork.db"
LOG_PATH = "logs/app.log"
UPLOAD_PATH = "uploads/projects"
SERVER_HOST = "0.0.0.0"  # 监听地址
SERVER_PORT = 8001  # 服务端口号

# ===== 会话配置常量 =====
SESSION_TOKEN_LENGTH = 64  # 会话令牌长度
SESSION_DEFAULT_DURATION_HOURS = 24  # 默认会话有效期（小时）
SESSION_CLEANUP_INTERVAL_MINUTES = 60  # 会话清理间隔（分钟）

# ===== 日志配置（原生 logging）=====
def setup_logging():
    """配置日志系统"""
    # 确保 logs 目录存在
    os.makedirs("logs", exist_ok=True)

    # 配置日志格式
    log_format = '[%(levelname)s] %(asctime)s | %(name)s | %(message)s'
    date_format = '%H:%M:%S'

    # 命令行处理器（带颜色）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # 文件处理器
    file_handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return root_logger


# 初始化日志
logger = setup_logging()

# ===== FastAPI 应用 =====
app = FastAPI(
    title="YourWork",
    description="企业项目管理系统",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


# ===== 数据库函数 =====

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row  # 返回字典格式
    conn.execute("PRAGMA journal_mode=WAL")  # 开启 WAL 模式，允许读写并发
    conn.execute("PRAGMA busy_timeout=30000")  # 忙等待 30 秒
    return conn


def row_to_dict(row) -> Optional[Dict]:
    """将数据库行转换为字典"""
    return dict(row) if row else None


def rows_to_list(rows) -> List[Dict]:
    """将多行数据转换为字典列表"""
    return [dict(row) for row in rows]


# ===== 工具函数 =====

def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def format_file_size_static(bytes_size: int) -> str:
    """格式化文件大小"""
    if bytes_size == 0:
        return '0 B'
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB']
    i = 0
    while bytes_size >= k and i < len(sizes) - 1:
        bytes_size /= k
        i += 1
    return f'{round(bytes_size, 2)} {sizes[i]}'


def hash_password(password: str) -> str:
    """密码加密（原生 hashlib）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


# ===== 会话管理（从独立模块导入）=====
# 导入会话管理函数，避免循环导入
from session import create_session, validate_session, revoke_session, cleanup_expired_sessions


def get_current_user(request: Request) -> Optional[Dict]:
    """获取当前登录用户（基于会话令牌验证）"""
    token = request.cookies.get('token')
    return validate_session(token)


def check_permission(user: Optional[Dict], required_roles: List[str] = None) -> bool:
    """检查用户权限"""
    if not user:
        return False

    if not required_roles:
        return True

    conn = get_db()
    cursor = conn.execute(
        """SELECT r.code FROM user_roles ur
           JOIN roles r ON ur.role_id = r.id
           WHERE ur.user_id = ? AND r.code IN ({})
           """.format(','.join(['?' for _ in required_roles])),
        [user['id']] + required_roles
    )
    result = cursor.fetchone()
    conn.close()

    return result is not None


def log_api_request(method: str, path: str, user: Optional[Dict] = None, data: Any = None):
    """记录 API 请求日志"""
    user_info = f"user={user['username']}" if user else "user=未登录"
    data_info = f", data={data}" if data else ""
    logger.info(f"API请求: {method} {path} | {user_info}{data_info}")


def log_response(method: str, path: str, code: int, message: str = ""):
    """记录 API 响应日志"""
    logger.info(f"API响应: {method} {path} | code={code}, message={message}")


# ===== 页面路由（返回 HTML）=====

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页/仪表盘"""
    logger.info(f"访问首页: client={request.client.host if request.client else 'unknown'}")
    file_path = "templates/index.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>欢迎使用 YourWork</h1><p>请先完成前端页面开发</p>"


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    logger.info("访问登录页")
    file_path = "templates/login.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>登录页面</h1><p>请先完成前端页面开发</p>"


@app.get("/projects", response_class=HTMLResponse)
async def project_list_page(request: Request):
    """项目列表页面"""
    logger.info(f"访问项目列表: client={request.client.host if request.client else 'unknown'}")
    file_path = "templates/project/list.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>项目列表</h1><p>请先完成前端页面开发</p>"


@app.get("/projects/create", response_class=HTMLResponse)
async def project_create_page(request: Request):
    """创建项目页面"""
    logger.info("访问创建项目页")
    file_path = "templates/project/create.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>创建项目</h1><p>请先完成前端页面开发</p>"


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(project_id: str, request: Request):
    """项目详情页面"""
    logger.info(f"访问项目详情: project_id={project_id}")
    file_path = "templates/project/detail.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content.replace("{{ project_id }}", project_id)
    return f"<h1>项目详情</h1><p>项目ID: {project_id}</p>"


@app.get("/messages", response_class=HTMLResponse)
async def message_list_page(request: Request):
    """消息中心页面"""
    logger.info("访问消息中心")
    file_path = "templates/message/list.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>消息中心</h1><p>请先完成前端页面开发</p>"


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """用户管理页面（系统管理员）"""
    logger.info("访问用户管理页")
    file_path = "templates/admin/users.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>用户管理</h1><p>请先完成前端页面开发</p>"


# ===== API 路由：认证模块 =====

@app.post("/api/v1/auth/login")
async def login(request: Request, response: Response):
    """用户登录"""
    try:
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        log_api_request("POST", "/api/v1/auth/login", None, {"username": username})

        conn = get_db()
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if not user or not verify_password(password, user['password']):
            log_response("POST", "/api/v1/auth/login", 401, "用户名或密码错误")
            return {"code": 401, "message": "用户名或密码错误"}

        # 创建会话
        session_token = create_session(user['id'])
        expires_at = datetime.now() + timedelta(hours=SESSION_DEFAULT_DURATION_HOURS)

        # 设置 Cookie（使用会话令牌）
        response.set_cookie(
            key="token",
            value=session_token,
            httponly=True,
            max_age=SESSION_DEFAULT_DURATION_HOURS * 60 * 60,  # 使用配置的会话时长
            samesite="lax"
        )

        user_dict = row_to_dict(user)
        # 移除密码字段
        user_dict.pop('password', None)

        log_response("POST", "/api/v1/auth/login", 200, "登录成功")
        return {
            "code": 0,
            "message": "登录成功",
            "data": {
                **user_dict,
                "session_token": session_token,
                "expires_at": expires_at.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return {"code": 500, "message": "服务器错误"}


@app.post("/api/v1/auth/logout")
async def logout(request: Request, response: Response):
    """用户登出（撤销会话）"""
    log_api_request("POST", "/api/v1/auth/logout")

    # 撤销当前会话
    token = request.cookies.get('token')
    if token:
        revoke_session(token)

    # 清除 Cookie
    response.delete_cookie("token")

    log_response("POST", "/api/v1/auth/logout", 200, "登出成功")
    return {"code": 0, "message": "登出成功"}


@app.get("/api/v1/auth/profile")
async def get_profile(request: Request):
    """获取当前用户信息"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    # 移除密码字段
    user.pop('password', None)

    # 获取用户角色
    conn = get_db()
    cursor = conn.execute(
        """SELECT r.code, r.name, r.description FROM user_roles ur
           JOIN roles r ON ur.role_id = r.id
           WHERE ur.user_id = ?""",
        (user['id'],)
    )
    roles = rows_to_list(cursor.fetchall())
    conn.close()

    user['roles'] = roles

    log_response("GET", "/api/v1/auth/profile", 200)
    return {"code": 0, "data": user}


# ===== API 路由：用户管理 =====

@app.get("/api/v1/users")
async def get_users(request: Request):
    """获取用户列表（系统管理员）"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    log_api_request("GET", "/api/v1/users", user)

    conn = get_db()
    cursor = conn.execute("SELECT id, username, display_name, email, is_active, created_at FROM users ORDER BY created_at DESC")
    users = rows_to_list(cursor.fetchall())

    # 为每个用户获取角色信息
    for u in users:
        cursor = conn.execute(
            """SELECT r.id, r.code, r.name
               FROM roles r
               JOIN user_roles ur ON ur.role_id = r.id
               WHERE ur.user_id = ?
               ORDER BY r.code""",
            (u['id'],)
        )
        u['roles'] = rows_to_list(cursor.fetchall())

    conn.close()

    log_response("GET", "/api/v1/users", 200, f"返回{len(users)}个用户")
    return {"code": 0, "data": users}


@app.post("/api/v1/users")
async def create_user(request: Request):
    """创建用户（仅系统管理员）"""
    current_user = get_current_user(request)

    if not current_user or not check_permission(current_user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限：仅系统管理员可以创建用户"}

    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    display_name = data.get('display_name')
    email = data.get('email')
    role_codes = data.get('roles', ['WORKER'])  # 默认角色为员工

    log_api_request("POST", "/api/v1/users", current_user, {"username": username, "roles": role_codes})

    # 验证必填字段
    if not username or not password:
        return {"code": 400, "message": "用户名和密码不能为空"}

    if not display_name:
        display_name = username

    import hashlib
    conn = get_db()

    # 检查用户名是否已存在
    cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"code": 400, "message": "用户名已存在"}

    # 创建用户
    user_id = generate_id()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, password_hash, display_name, email, 1, now, now)
    )

    # 分配角色
    for role_code in role_codes:
        cursor = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,))
        role = cursor.fetchone()
        if role:
            conn.execute(
                "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                (generate_id(), user_id, role['id'])
            )

    conn.commit()
    conn.close()

    log_response("POST", "/api/v1/users", 200, f"用户创建成功: {username}")

    return {
        "code": 0,
        "message": "用户创建成功",
        "data": {
            "user_id": user_id,
            "username": username,
            "roles": role_codes
        }
    }


@app.put("/api/v1/users/{user_id}/roles")
async def update_user_roles(user_id: str, request: Request):
    """更新用户角色（系统管理员）"""
    current_user = get_current_user(request)

    if not current_user or not check_permission(current_user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    role_codes = data.get('roles', [])

    log_api_request("PUT", f"/api/v1/users/{user_id}/roles", current_user, {"roles": role_codes})

    conn = get_db()

    # 删除用户现有角色
    conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))

    # 添加新角色
    for role_code in role_codes:
        cursor = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,))
        role = cursor.fetchone()
        if role:
            conn.execute(
                "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                (generate_id(), user_id, role['id'])
            )

    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/users/{user_id}/roles", 200, "角色更新成功")
    return {"code": 0, "message": "角色更新成功"}


@app.put("/api/v1/users/{user_id}")
async def update_user(user_id: str, request: Request):
    """更新用户信息（系统管理员）"""
    current_user = get_current_user(request)

    if not current_user or not check_permission(current_user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    display_name = data.get('display_name')
    email = data.get('email')

    log_api_request("PUT", f"/api/v1/users/{user_id}", current_user, {"display_name": display_name, "email": email})

    conn = get_db()

    # 检查用户是否存在
    cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return {"code": 404, "message": "用户不存在"}

    # 构建更新字段
    update_fields = []
    params = []

    if display_name is not None:
        update_fields.append("display_name = ?")
        params.append(display_name)

    if email is not None:
        update_fields.append("email = ?")
        params.append(email)

    if update_fields:
        params.append(user_id)
        conn.execute(
            f"UPDATE users SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?",
            params + [datetime.now().isoformat()]
        )

    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/users/{user_id}", 200, "用户信息更新成功")
    return {"code": 0, "message": "用户信息更新成功"}


@app.put("/api/v1/users/{user_id}/password")
async def reset_user_password(user_id: str, request: Request):
    """重置用户密码（系统管理员）"""
    current_user = get_current_user(request)

    if not current_user or not check_permission(current_user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    new_password = data.get('password')

    if not new_password:
        return {"code": 400, "message": "密码不能为空"}

    log_api_request("PUT", f"/api/v1/users/{user_id}/password", current_user)

    import hashlib
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()

    conn = get_db()

    # 检查用户是否存在
    cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return {"code": 404, "message": "用户不存在"}

    conn.execute(
        "UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
        (password_hash, datetime.now().isoformat(), user_id)
    )

    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/users/{user_id}/password", 200, "密码重置成功")
    return {"code": 0, "message": "密码重置成功"}


@app.delete("/api/v1/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """删除用户（系统管理员）"""
    current_user = get_current_user(request)

    if not current_user or not check_permission(current_user, ["SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    # 不能删除自己
    if user_id == current_user['id']:
        return {"code": 400, "message": "不能删除自己"}

    log_api_request("DELETE", f"/api/v1/users/{user_id}", current_user)

    conn = get_db()

    # 检查用户是否存在
    cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return {"code": 404, "message": "用户不存在"}

    # 删除用户关联数据
    conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM project_members WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM milestone_logs WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM ws_logs WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/users/{user_id}", 200, "用户删除成功")
    return {"code": 0, "message": "用户删除成功"}


# ===== API 路由：项目管理 =====

@app.get("/api/v1/projects")
async def get_projects(request: Request):
    """获取项目列表"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", "/api/v1/projects", user)

    # 获取查询参数
    status = request.query_params.get('status')
    keyword = request.query_params.get('keyword')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))

    conn = get_db()

    # 构建查询条件
    where_conditions = []
    params = []

    # 默认过滤归档项目，除非显式查询 status=archived
    if status != 'archived':
        where_conditions.append("p.status != 'archived'")

    if status:
        where_conditions.append("p.status = ?")
        params.append(status)

    if keyword:
        where_conditions.append("(p.name LIKE ? OR p.project_no LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

    # 如果不是管理员，只能看到自己参与的项目
    if not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        where_clause += f" AND EXISTS (SELECT 1 FROM project_members pm WHERE pm.project_id = p.id AND pm.user_id = '{user['id']}')"

    # 获取总数
    count_query = f"SELECT COUNT(*) as total FROM projects p WHERE {where_clause}"
    cursor = conn.execute(count_query, params)
    total = cursor.fetchone()['total']

    # 获取分页数据
    offset = (page - 1) * page_size
    query = f"""
        SELECT p.* FROM projects p
        WHERE {where_clause}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor = conn.execute(query, params + [page_size, offset])
    projects = rows_to_list(cursor.fetchall())
    conn.close()

    log_response("GET", "/api/v1/projects", 200, f"返回{len(projects)}个项目")

    return {
        "code": 0,
        "data": {
            "items": projects,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }


@app.post("/api/v1/projects")
async def create_project(request: Request):
    """创建项目"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    project_name = data.get('name')
    description = data.get('description', '')

    log_api_request("POST", "/api/v1/projects", user, {"name": project_name})

    project_id = generate_id()
    project_no = f"PRJ-{datetime.now().strftime('%Y%m%d')}-{project_id[:8]}"
    now = datetime.now().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, project_no, project_name, description, 'in_progress', now, now)
    )

    # 自动将创建者添加为项目成员
    conn.execute(
        """INSERT INTO project_members (id, project_id, user_id, roles, display_name)
           VALUES (?, ?, ?, ?, ?)""",
        (generate_id(), project_id, user['id'], 'owner', user['display_name'])
    )

    conn.commit()
    conn.close()

    log_response("POST", "/api/v1/projects", 200, f"项目创建成功: {project_no}")

    return {
        "code": 0,
        "message": "创建成功",
        "data": {
            "project_id": project_id,
            "project_no": project_no
        }
    }


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str, request: Request):
    """获取项目详情"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/projects/{project_id}", user)

    conn = get_db()
    cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        log_response("GET", f"/api/v1/projects/{project_id}", 404, "项目不存在")
        return {"code": 404, "message": "项目不存在"}

    # 检查权限
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 获取里程碑
    cursor = conn.execute(
        "SELECT * FROM milestones WHERE project_id = ? ORDER BY created_at ASC",
        (project_id,)
    )
    milestones = rows_to_list(cursor.fetchall())

    # 获取成员
    cursor = conn.execute(
        """SELECT pm.*, u.username FROM project_members pm
           LEFT JOIN users u ON pm.user_id = u.id
           WHERE pm.project_id = ?""",
        (project_id,)
    )
    members = rows_to_list(cursor.fetchall())

    # 获取产出物（包含里程碑名称）
    cursor = conn.execute(
        """SELECT d.*, m.name as milestone_name
           FROM deliverables d
           LEFT JOIN milestones m ON d.milestone_id = m.id
           WHERE d.project_id = ?
           ORDER BY d.created_at DESC""",
        (project_id,)
    )
    deliverables = rows_to_list(cursor.fetchall())

    conn.close()

    log_response("GET", f"/api/v1/projects/{project_id}", 200)

    return {
        "code": 0,
        "data": {
            "project": row_to_dict(project),
            "milestones": milestones,
            "members": members,
            "deliverables": deliverables
        }
    }


@app.put("/api/v1/projects/{project_id}")
async def update_project(project_id: str, request: Request):
    """更新项目信息"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    name = data.get('name')
    description = data.get('description')

    log_api_request("PUT", f"/api/v1/projects/{project_id}", user, data)

    now = datetime.now().isoformat()

    conn = get_db()
    conn.execute(
        "UPDATE projects SET name = ?, description = ?, updated_at = ? WHERE id = ?",
        (name, description, now, project_id)
    )
    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/projects/{project_id}", 200, "项目更新成功")
    return {"code": 0, "message": "更新成功"}


@app.put("/api/v1/projects/{project_id}/status")
async def update_project_status(project_id: str, request: Request):
    """更新项目状态"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    status = data.get('status')

    # 验证状态值
    valid_statuses = ['in_progress', 'completed', 'ignored', 'archived']
    if status not in valid_statuses:
        return {"code": 400, "message": f"无效的状态值，必须是: {', '.join(valid_statuses)}"}

    log_api_request("PUT", f"/api/v1/projects/{project_id}/status", user, {"status": status})

    now = datetime.now().isoformat()

    conn = get_db()
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, project_id)
    )
    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/projects/{project_id}/status", 200, "项目状态更新成功")
    return {"code": 0, "message": "状态更新成功"}


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, request: Request):
    """归档项目（仅ADMIN和SYSTEM_ADMIN）
    归档后项目变为只读状态，不在列表中显示，但数据可查询
    """
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限：仅管理员可以归档项目"}

    log_api_request("DELETE", f"/api/v1/projects/{project_id}", user)

    conn = get_db()

    # 检查项目是否存在
    cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        return {"code": 404, "message": "项目不存在"}

    # 检查当前状态
    if project['status'] == 'archived':
        conn.close()
        return {"code": 400, "message": "项目已经是归档状态"}

    # 归档项目（只更新状态，不删除数据）
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        ('archived', now, project_id)
    )
    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/projects/{project_id}", 200, f"项目归档成功: {project['name']}")

    return {
        "code": 0,
        "message": "项目已归档",
        "data": {
            "project_id": project_id,
            "project_name": project['name'],
            "status": "archived"
        }
    }


@app.put("/api/v1/projects/{project_id}/unarchive")
async def unarchive_project(project_id: str, request: Request):
    """取消归档项目（仅ADMIN和SYSTEM_ADMIN）
    将归档状态的项目恢复为进行中状态
    """
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限：仅管理员可以取消归档"}

    log_api_request("PUT", f"/api/v1/projects/{project_id}/unarchive", user)

    conn = get_db()

    # 检查项目是否存在
    cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        return {"code": 404, "message": "项目不存在"}

    # 检查当前状态
    if project['status'] != 'archived':
        conn.close()
        return {"code": 400, "message": "只有归档状态的项目可以取消归档"}

    # 取消归档
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        ('in_progress', now, project_id)
    )
    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/projects/{project_id}/unarchive", 200, f"取消归档成功: {project['name']}")

    return {
        "code": 0,
        "message": "项目已恢复",
        "data": {
            "project_id": project_id,
            "project_name": project['name'],
            "status": "in_progress"
        }
    }


# ===== API 路由：项目成员 =====

@app.post("/api/v1/projects/{project_id}/members")
async def add_project_member(project_id: str, request: Request):
    """添加项目成员"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    data = await request.json()
    user_id = data.get('user_id')
    display_name = data.get('display_name', '')
    roles = data.get('roles', [])

    log_api_request("POST", f"/api/v1/projects/{project_id}/members", user, data)

    # 验证用户存在
    conn = get_db()
    cursor = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        return {"code": 404, "message": "用户不存在"}

    if not display_name:
        display_name = target_user['username']

    # 检查是否已是成员
    cursor = conn.execute(
        "SELECT id FROM project_members WHERE project_id = ? AND user_id = ?",
        (project_id, user_id)
    )
    if cursor.fetchone():
        conn.close()
        return {"code": 400, "message": "用户已是项目成员"}

    # 添加成员
    conn.execute(
        "INSERT INTO project_members (id, project_id, user_id, display_name, roles) VALUES (?, ?, ?, ?, ?)",
        (generate_id(), project_id, user_id, display_name, roles or '')
    )
    conn.commit()
    conn.close()

    log_response("POST", f"/api/v1/projects/{project_id}/members", 200, "成员添加成功")
    return {"code": 0, "message": "添加成功"}


@app.delete("/api/v1/projects/{project_id}/members/{user_id}")
async def remove_project_member(project_id: str, user_id: str, request: Request):
    """移除项目成员"""
    user = get_current_user(request)

    if not user or not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        return {"code": 403, "message": "无权限"}

    log_api_request("DELETE", f"/api/v1/projects/{project_id}/members/{user_id}", user)

    conn = get_db()
    conn.execute(
        "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
        (project_id, user_id)
    )
    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/projects/{project_id}/members/{user_id}", 200, "成员移除成功")
    return {"code": 0, "message": "移除成功"}


# ===== API 路由：里程碑管理 =====

@app.get("/api/v1/projects/{project_id}/milestones")
async def get_milestones(project_id: str, request: Request):
    """获取项目里程碑列表"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/projects/{project_id}/milestones", user)

    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM milestones WHERE project_id = ? ORDER BY created_at ASC",
        (project_id,)
    )
    milestones = rows_to_list(cursor.fetchall())
    conn.close()

    log_response("GET", f"/api/v1/projects/{project_id}/milestones", 200, f"返回{len(milestones)}个里程碑")
    return {"code": 0, "data": milestones}


@app.post("/api/v1/milestones")
async def create_milestone(request: Request):
    """创建里程碑"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    project_id = data.get('project_id')
    name = data.get('name')
    description = data.get('description', '')
    type = data.get('type', 'milestone')
    deadline = data.get('deadline')

    log_api_request("POST", "/api/v1/milestones", user, data)

    milestone_id = generate_id()
    now = datetime.now().isoformat()

    conn = get_db()
    conn.execute(
        """INSERT INTO milestones (id, project_id, type, name, description, deadline, status, created_by, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (milestone_id, project_id, type, name, description, deadline, 'created', user['id'], now, now)
    )
    conn.commit()
    conn.close()

    # 记录操作日志
    conn = get_db()
    conn.execute(
        "INSERT INTO milestone_logs (id, milestone_id, user_id, action, created_at) VALUES (?, ?, ?, ?, ?)",
        (generate_id(), milestone_id, user['id'], '创建里程碑', now)
    )
    conn.commit()
    conn.close()

    log_response("POST", "/api/v1/milestones", 200, "里程碑创建成功")

    return {
        "code": 0,
        "message": "创建成功",
        "data": {"milestone_id": milestone_id}
    }


@app.get("/api/v1/milestones/{milestone_id}")
async def get_milestone(milestone_id: str, request: Request):
    """获取里程碑详情"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/milestones/{milestone_id}", user)

    conn = get_db()
    cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()

    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    conn.close()

    log_response("GET", f"/api/v1/milestones/{milestone_id}", 200)
    return {"code": 0, "data": row_to_dict(milestone)}


def validate_status_change(conn, milestone_id, old_status, new_status, ms_type):
    """
    验证里程碑状态变更是否符合规则

    状态转换规则：
    - created → in_progress: 所有前置依赖必须完成
    - in_progress → completed: 所有行动项必须完成（仅里程碑）
    - 任意 → suspended: 无限制
    - suspended → in_progress/created: 需要满足相应的恢复条件
    """
    errors = []

    # 任何状态都可以转为挂起
    if new_status == 'suspended':
        return {'valid': True, 'errors': []}

    # 挂起状态恢复
    if old_status == 'suspended':
        # 恢复到进行中需要检查前置依赖
        if new_status == 'in_progress':
            cursor = conn.execute(
                """SELECT m.name FROM milestone_dependencies md
                   JOIN milestones m ON md.depends_on_id = m.id
                   WHERE md.milestone_id = ? AND m.status != 'completed'""",
                (milestone_id,)
            )
            uncompleted = cursor.fetchall()
            if uncompleted:
                errors = [f"前置里程碑「{row['name']}」尚未完成" for row in uncompleted]
                return {'valid': False, 'errors': errors}
        return {'valid': True, 'errors': []}

    # created → in_progress 需要检查前置依赖
    if old_status == 'created' and new_status == 'in_progress':
        cursor = conn.execute(
            """SELECT m.name FROM milestone_dependencies md
               JOIN milestones m ON md.depends_on_id = m.id
               WHERE md.milestone_id = ? AND m.status != 'completed'""",
            (milestone_id,)
        )
        uncompleted = cursor.fetchall()
        if uncompleted:
            errors = [f"前置里程碑「{row['name']}」尚未完成" for row in uncompleted]
            return {'valid': False, 'errors': errors}

    # in_progress → completed 需要检查行动项（仅里程碑，不包括目标）
    if old_status == 'in_progress' and new_status == 'completed' and ms_type == 'milestone':
        cursor = conn.execute(
            """SELECT title FROM milestone_items
               WHERE milestone_id = ? AND status != 'completed'
               AND source_type = 'manual'""",
            (milestone_id,)
        )
        uncompleted_items = cursor.fetchall()
        if uncompleted_items:
            errors = [f"存在未完成的行动项：{row['title']}" for row in uncompleted_items]
            return {'valid': False, 'errors': errors}

    # in_progress → completed 对于目标类型需要检查是否有上传文件
    if old_status == 'in_progress' and new_status == 'completed' and ms_type == 'deliverable':
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM deliverables WHERE milestone_id = ?",
            (milestone_id,)
        )
        count = cursor.fetchone()['cnt']
        if count == 0:
            errors = ["目标（验收点）需要上传产出物才能标记为完成"]
            return {'valid': False, 'errors': errors}

    return {'valid': True, 'errors': []}


@app.put("/api/v1/milestones/{milestone_id}")
async def update_milestone(milestone_id: str, request: Request):
    """更新里程碑"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    name = data.get('name')
    description = data.get('description')
    status = data.get('status')

    log_api_request("PUT", f"/api/v1/milestones/{milestone_id}", user, data)

    now = datetime.now().isoformat()

    try:
        conn = get_db()

        # 检查里程碑是否存在
        cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        milestone = cursor.fetchone()

        if not milestone:
            conn.close()
            return {"code": 404, "message": "里程碑不存在"}

        old_status = milestone['status']
        ms_type = milestone['type']

        # 权限检查：WORKER只能操作自己创建的里程碑
        if not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
            if milestone['created_by'] != user['id']:
                conn.close()
                return {"code": 403, "message": "无权限：只能操作自己创建的里程碑"}

        # 状态变更验证
        if status is not None and status != old_status:
            validation_result = validate_status_change(
                conn, milestone_id, old_status, status, ms_type
            )
            if not validation_result['valid']:
                conn.close()
                return {
                    "code": 400,
                    "message": "状态变更失败",
                    "errors": validation_result['errors']
                }

        # 构建动态UPDATE语句，只更新提供的字段
        update_fields = []
        params = []

        if name is not None:
            update_fields.append("name = ?")
            params.append(name)

        if description is not None:
            update_fields.append("description = ?")
            params.append(description)

        if status is not None:
            update_fields.append("status = ?")
            params.append(status)

        # 至少更新一个字段
        if not update_fields:
            conn.close()
            return {"code": 400, "message": "没有提供要更新的字段"}

        update_fields.append("updated_at = ?")
        params.append(now)
        params.append(milestone_id)

        sql = f"UPDATE milestones SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(sql, params)
        conn.commit()
        conn.close()

        # 记录操作日志
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO milestone_logs (id, milestone_id, user_id, action, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (generate_id(), milestone_id, user['id'], '更新里程碑', f'状态改为: {status}', now)
            )
            conn.commit()
        except Exception as log_error:
            # 日志记录失败不影响主操作
            pass
        finally:
            conn.close()

        log_response("PUT", f"/api/v1/milestones/{milestone_id}", 200, "里程碑更新成功")
        return {"code": 0, "message": "更新成功"}

    except Exception as e:
        return {"code": 500, "message": f"更新失败: {str(e)}"}


@app.delete("/api/v1/milestones/{milestone_id}")
async def delete_milestone(milestone_id: str, request: Request):
    """删除里程碑"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("DELETE", f"/api/v1/milestones/{milestone_id}", user)

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()

    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    # 权限检查：WORKER只能删除自己创建的里程碑
    if not check_permission(user, ["ADMIN", "SYSTEM_ADMIN"]):
        if milestone['created_by'] != user['id']:
            conn.close()
            return {"code": 403, "message": "无权限：只能删除自己创建的里程碑"}

    # 删除关联数据
    conn.execute("DELETE FROM milestone_dependencies WHERE milestone_id = ?", (milestone_id,))
    conn.execute("DELETE FROM milestone_dependencies WHERE depends_on_id = ?", (milestone_id,))
    conn.execute("DELETE FROM milestone_logs WHERE milestone_id = ?", (milestone_id,))

    # 删除里程碑
    conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))

    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/milestones/{milestone_id}", 200, "里程碑删除成功")

    return {"code": 0, "message": "里程碑删除成功"}


@app.get("/api/v1/milestones/{milestone_id}/logs")
async def get_milestone_logs(milestone_id: str, request: Request):
    """获取里程碑操作日志"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/milestones/{milestone_id}/logs", user)

    conn = get_db()
    cursor = conn.execute(
        """SELECT ml.*, u.username FROM milestone_logs ml
           JOIN users u ON ml.user_id = u.id
           WHERE ml.milestone_id = ?
           ORDER BY ml.created_at DESC""",
        (milestone_id,)
    )
    logs = rows_to_list(cursor.fetchall())
    conn.close()

    log_response("GET", f"/api/v1/milestones/{milestone_id}/logs", 200, f"返回{len(logs)}条日志")
    return {"code": 0, "data": logs}


@app.post("/api/v1/milestones/{milestone_id}/logs")
async def add_milestone_log(milestone_id: str, request: Request):
    """添加里程碑操作日志"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    action = data.get('action')
    description = data.get('description', '')

    log_api_request("POST", f"/api/v1/milestones/{milestone_id}/logs", user, data)

    now = datetime.now().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO milestone_logs (id, milestone_id, user_id, action, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (generate_id(), milestone_id, user['id'], action, description, now)
    )
    conn.commit()
    conn.close()

    log_response("POST", f"/api/v1/milestones/{milestone_id}/logs", 200, "日志添加成功")
    return {"code": 0, "message": "添加成功"}


# ===== API 路由：里程碑行动项管理 =====

@app.get("/api/v1/milestones/{milestone_id}/items")
async def get_milestone_items(milestone_id: str, request: Request):
    """获取里程碑行动项列表"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/milestones/{milestone_id}/items", user)

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT id FROM milestones WHERE id = ?", (milestone_id,))
    if not cursor.fetchone():
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    # 获取行动项
    cursor = conn.execute(
        """SELECT mi.*, u.username as assignee_name, c.username as created_by_name
           FROM milestone_items mi
           LEFT JOIN users u ON mi.assignee_id = u.id
           LEFT JOIN users c ON mi.created_by = c.id
           WHERE mi.milestone_id = ?
           ORDER BY mi.sort_order, mi.created_at""",
        (milestone_id,)
    )
    items = rows_to_list(cursor.fetchall())

    # 统计
    summary = {
        "total": len(items),
        "completed": len([i for i in items if i['status'] == 'completed']),
        "in_progress": len([i for i in items if i['status'] == 'in_progress']),
        "pending": len([i for i in items if i['status'] == 'pending'])
    }

    conn.close()
    log_response("GET", f"/api/v1/milestones/{milestone_id}/items", 200, f"返回{len(items)}个行动项")
    return {"code": 0, "data": {"items": items, "summary": summary}}


@app.post("/api/v1/milestones/{milestone_id}/items")
async def create_milestone_item(milestone_id: str, request: Request):
    """创建里程碑行动项"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    title = data.get('title')
    description = data.get('description', '')
    assignee_id = data.get('assignee_id')
    deadline = data.get('deadline')
    sort_order = data.get('sort_order', 0)
    source_type = data.get('source_type', 'manual')

    log_api_request("POST", f"/api/v1/milestones/{milestone_id}/items", user, data)

    if not title:
        return {"code": 400, "message": "行动项标题不能为空"}

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT id, project_id FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()
    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    # 检查权限
    project_id = milestone['project_id']
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 创建行动项
    item_id = generate_id()
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO milestone_items (id, milestone_id, title, description, status, sort_order, assignee_id, deadline, created_by, created_at, updated_at, source_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_id, milestone_id, title, description, 'pending', sort_order, assignee_id, deadline, user['id'], now, now, source_type)
    )
    conn.commit()
    conn.close()

    log_response("POST", f"/api/v1/milestones/{milestone_id}/items", 200, "行动项创建成功")
    return {"code": 0, "message": "行动项创建成功", "data": {"item_id": item_id}}


@app.put("/api/v1/milestone-items/{item_id}")
async def update_milestone_item(item_id: str, request: Request):
    """更新里程碑行动项"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    title = data.get('title')
    description = data.get('description')
    status = data.get('status')
    assignee_id = data.get('assignee_id')
    deadline = data.get('deadline')
    sort_order = data.get('sort_order')

    log_api_request("PUT", f"/api/v1/milestone-items/{item_id}", user, data)

    conn = get_db()

    # 检查行动项是否存在
    cursor = conn.execute(
        """SELECT mi.*, m.project_id FROM milestone_items mi
           JOIN milestones m ON mi.milestone_id = m.id
           WHERE mi.id = ?""",
        (item_id,)
    )
    item = cursor.fetchone()
    if not item:
        conn.close()
        return {"code": 404, "message": "行动项不存在"}

    # 检查权限
    project_id = item['project_id']
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 更新字段
    update_fields = []
    params = []

    if title is not None:
        update_fields.append("title = ?")
        params.append(title)

    if description is not None:
        update_fields.append("description = ?")
        params.append(description)

    if status is not None:
        update_fields.append("status = ?")
        params.append(status)

    if assignee_id is not None:
        update_fields.append("assignee_id = ?")
        params.append(assignee_id)

    if deadline is not None:
        update_fields.append("deadline = ?")
        params.append(deadline)

    if sort_order is not None:
        update_fields.append("sort_order = ?")
        params.append(sort_order)

    if not update_fields:
        conn.close()
        return {"code": 400, "message": "没有提供要更新的字段"}

    update_fields.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(item_id)

    sql = f"UPDATE milestone_items SET {', '.join(update_fields)} WHERE id = ?"
    conn.execute(sql, params)
    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/milestone-items/{item_id}", 200, "行动项更新成功")
    return {"code": 0, "message": "行动项更新成功"}


@app.delete("/api/v1/milestone-items/{item_id}")
async def delete_milestone_item(item_id: str, request: Request):
    """删除里程碑行动项"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("DELETE", f"/api/v1/milestone-items/{item_id}", user)

    conn = get_db()

    # 检查行动项是否存在
    cursor = conn.execute(
        """SELECT mi.*, m.project_id FROM milestone_items mi
           JOIN milestones m ON mi.milestone_id = m.id
           WHERE mi.id = ?""",
        (item_id,)
    )
    item = cursor.fetchone()
    if not item:
        conn.close()
        return {"code": 404, "message": "行动项不存在"}

    # 检查权限（只有管理员和创建者可以删除）
    project_id = item['project_id']
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        if item['created_by'] != user['id']:
            conn.close()
            return {"code": 403, "message": "无权限：只能删除自己创建的行动项"}
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 删除行动项
    conn.execute("DELETE FROM milestone_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/milestone-items/{item_id}", 200, "行动项删除成功")
    return {"code": 0, "message": "行动项删除成功"}


# ===== API 路由：里程碑依赖关系管理 =====

@app.get("/api/v1/milestones/{milestone_id}/dependencies")
async def get_milestone_dependencies(milestone_id: str, request: Request):
    """获取里程碑的依赖关系（前置里程碑列表）"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/milestones/{milestone_id}/dependencies", user)

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT id, project_id FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()
    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    # 获取当前里程碑信息
    current_ms = row_to_dict(milestone)
    project_id = current_ms['project_id']

    # 获取前置依赖列表
    cursor = conn.execute(
        """SELECT m.id, m.name, m.type, m.status, m.deadline
           FROM milestone_dependencies md
           JOIN milestones m ON md.depends_on_id = m.id
           WHERE md.milestone_id = ?
           ORDER BY m.created_at""",
        (milestone_id,)
    )
    dependencies = rows_to_list(cursor.fetchall())

    # 获取当前项目所有可用的里程碑（用于添加依赖）
    cursor = conn.execute(
        """SELECT id, name, type, status
           FROM milestones
           WHERE project_id = ? AND id != ?
           ORDER BY type, created_at""",
        (project_id, milestone_id)
    )
    available = rows_to_list(cursor.fetchall())

    # 获取依赖此里程碑的其他里程碑（反向依赖）
    cursor = conn.execute(
        """SELECT m.id, m.name, m.type, m.status
           FROM milestone_dependencies md
           JOIN milestones m ON md.milestone_id = m.id
           WHERE md.depends_on_id = ?""",
        (milestone_id,)
    )
    blocking = rows_to_list(cursor.fetchall())

    conn.close()
    log_response("GET", f"/api/v1/milestones/{milestone_id}/dependencies", 200, f"返回{len(dependencies)}个前置依赖")
    return {
        "code": 0,
        "data": {
            "dependencies": dependencies,
            "available": available,
            "blocking": blocking,
            "milestone_type": current_ms.get('type'),
            "is_deliverable": current_ms.get('type') == 'deliverable'
        }
    }


@app.post("/api/v1/milestones/{milestone_id}/dependencies")
async def add_milestone_dependencies(milestone_id: str, request: Request):
    """添加里程碑前置依赖"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    depends_on_ids = data.get('depends_on_ids', [])

    log_api_request("POST", f"/api/v1/milestones/{milestone_id}/dependencies", user, data)

    if not depends_on_ids:
        return {"code": 400, "message": "请选择要添加的前置依赖"}

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT id, project_id, type FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()
    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    project_id = milestone['project_id']
    ms_type = milestone['type']

    # 检查权限
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 如果是目标（deliverable），必须有至少1个前置依赖
    if ms_type == 'deliverable' and not depends_on_ids:
        conn.close()
        return {"code": 400, "message": "目标（验收点）必须有至少1个前置里程碑依赖"}

    now = datetime.now().isoformat()
    added_count = 0

    for dep_id in depends_on_ids:
        # 检查依赖的里程碑是否存在
        cursor = conn.execute("SELECT id FROM milestones WHERE id = ? AND project_id = ?", (dep_id, project_id))
        if not cursor.fetchone():
            continue

        # 检查是否已经存在依赖关系
        cursor = conn.execute("SELECT id FROM milestone_dependencies WHERE milestone_id = ? AND depends_on_id = ?", (milestone_id, dep_id))
        if cursor.fetchone():
            continue

        # 检查循环依赖
        cursor = conn.execute(
            """SELECT 1 FROM milestone_dependencies WHERE milestone_id = ? AND depends_on_id = ?""",
            (dep_id, milestone_id)
        )
        if cursor.fetchone():
            conn.close()
            return {"code": 400, "message": f"不能添加循环依赖：{dep_id}"}

        # 添加依赖关系
        conn.execute(
            "INSERT INTO milestone_dependencies (id, milestone_id, depends_on_id) VALUES (?, ?, ?)",
            (generate_id(), milestone_id, dep_id)
        )
        added_count += 1

    conn.commit()
    conn.close()

    if added_count == 0:
        return {"code": 400, "message": "没有添加新的依赖关系（可能已存在）"}

    log_response("POST", f"/api/v1/milestones/{milestone_id}/dependencies", 200, f"添加了{added_count}个依赖")
    return {"code": 0, "message": f"成功添加{added_count}个依赖关系"}


@app.delete("/api/v1/milestones/{milestone_id}/dependencies")
async def delete_milestone_dependencies(milestone_id: str, request: Request):
    """删除里程碑前置依赖"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    depends_on_ids = data.get('depends_on_ids', [])

    log_api_request("DELETE", f"/api/v1/milestones/{milestone_id}/dependencies", user, data)

    if not depends_on_ids:
        return {"code": 400, "message": "请选择要删除的依赖关系"}

    conn = get_db()

    # 检查里程碑是否存在
    cursor = conn.execute("SELECT id, project_id, type FROM milestones WHERE id = ?", (milestone_id,))
    milestone = cursor.fetchone()
    if not milestone:
        conn.close()
        return {"code": 404, "message": "里程碑不存在"}

    project_id = milestone['project_id']
    ms_type = milestone['type']

    # 检查权限
    has_access = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
    if not has_access:
        cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, user['id']))
        has_access = cursor.fetchone() is not None

    if not has_access:
        conn.close()
        return {"code": 403, "message": "无权限"}

    # 如果是目标（deliverable），删除后必须至少保留1个前置依赖
    if ms_type == 'deliverable':
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM milestone_dependencies WHERE milestone_id = ?", (milestone_id,))
        current_count = cursor.fetchone()['cnt']
        if current_count - len(depends_on_ids) < 1:
            conn.close()
            return {"code": 400, "message": "目标（验收点）必须有至少1个前置里程碑依赖"}

    # 删除依赖关系
    deleted_count = 0
    for dep_id in depends_on_ids:
        cursor = conn.execute(
            "DELETE FROM milestone_dependencies WHERE milestone_id = ? AND depends_on_id = ?",
            (milestone_id, dep_id)
        )
        if cursor.rowcount > 0:
            deleted_count += 1

    conn.commit()
    conn.close()

    if deleted_count == 0:
        return {"code": 400, "message": "没有删除任何依赖关系"}

    log_response("DELETE", f"/api/v1/milestones/{milestone_id}/dependencies", 200, f"删除了{deleted_count}个依赖")
    return {"code": 0, "message": f"成功删除{deleted_count}个依赖关系"}


@app.get("/api/v1/projects/{project_id}/milestone-status")
async def get_project_milestone_status(project_id: str, request: Request):
    """获取项目里程碑状态汇总"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/projects/{project_id}/milestone-status", user)

    conn = get_db()

    # 检查项目是否存在
    cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if not cursor.fetchone():
        conn.close()
        return {"code": 404, "message": "项目不存在"}

    # 获取所有里程碑
    cursor = conn.execute(
        """SELECT id, name, type, status, deadline, created_at
           FROM milestones
           WHERE project_id = ?
           ORDER BY created_at""",
        (project_id,)
    )
    milestones = rows_to_list(cursor.fetchall())

    # 统计各状态数量
    summary = {
        "total": len(milestones),
        "created": 0,
        "in_progress": 0,
        "completed": 0,
        "suspended": 0,
        "blocked": 0,
        "milestone_count": 0,
        "deliverable_count": 0,
        "completion_rate": 0.0
    }

    blocked_milestones = []

    for ms in milestones:
        # 统计各状态
        summary[ms['status']] = summary.get(ms['status'], 0) + 1

        # 统计类型
        if ms['type'] == 'milestone':
            summary['milestone_count'] += 1
        else:
            summary['deliverable_count'] += 1

        # 检查是否被阻塞（有未完成的前置依赖）
        cursor = conn.execute(
            """SELECT m.name FROM milestone_dependencies md
               JOIN milestones m ON md.depends_on_id = m.id
               WHERE md.milestone_id = ? AND m.status != 'completed'""",
            (ms['id'],)
        )
        uncompleted_deps = cursor.fetchall()

        if uncompleted_deps and ms['status'] not in ['completed', 'suspended']:
            summary['blocked'] += 1
            blocked_milestones.append({
                "id": ms['id'],
                "name": ms['name'],
                "type": ms['type'],
                "status": ms['status'],
                "uncompleted_dependencies": [row['name'] for row in uncompleted_deps]
            })

    # 计算完成率
    if summary['total'] > 0:
        summary['completion_rate'] = round(summary['completed'] / summary['total'] * 100, 1)

    conn.close()
    log_response("GET", f"/api/v1/projects/{project_id}/milestone-status", 200, "状态汇总获取成功")
    return {
        "code": 0,
        "data": {
            "summary": summary,
            "blocked_milestones": blocked_milestones
        }
    }




@app.get("/api/v1/projects/{project_id}/deliverables")
async def get_deliverables(project_id: str, request: Request):
    """获取项目产出物列表"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/projects/{project_id}/deliverables", user)

    milestone_id = request.query_params.get('milestone_id')

    conn = get_db()
    if milestone_id:
        cursor = conn.execute(
            "SELECT * FROM deliverables WHERE project_id = ? AND milestone_id = ? ORDER BY created_at DESC",
            (project_id, milestone_id)
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM deliverables WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,)
        )
    deliverables = rows_to_list(cursor.fetchall())
    conn.close()

    log_response("GET", f"/api/v1/projects/{project_id}/deliverables", 200, f"返回{len(deliverables)}个产出物")
    return {"code": 0, "data": deliverables}


@app.post("/api/v1/projects/{project_id}/deliverables/upload")
async def upload_deliverable(project_id: str, file: UploadFile = File(...), milestone_id: str = None, request: Request = None):
    """上传产出物"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("POST", f"/api/v1/projects/{project_id}/deliverables/upload", user, {"file": file.filename})

    # 确保上传目录存在
    upload_dir = os.path.join(UPLOAD_PATH, project_id)
    if milestone_id:
        upload_dir = os.path.join(upload_dir, milestone_id)
    os.makedirs(upload_dir, exist_ok=True)

    # 生成文件名
    file_id = generate_id()
    file_ext = os.path.splitext(file.filename)[1]
    stored_name = f"{file_id}{file_ext}"
    file_path = os.path.join(upload_dir, stored_name)

    # 保存文件
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    file_size = os.path.getsize(file_path)
    now = datetime.now().isoformat()

    # 保存到数据库
    conn = get_db()
    conn.execute(
        """INSERT INTO deliverables (id, name, original_name, file_path, file_size, file_type, project_id, milestone_id, created_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (file_id, stored_name, file.filename, file_path, file_size, file.content_type, project_id, milestone_id, user['id'], now)
    )
    conn.commit()

    # 如果上传到里程碑，自动记录为行动项
    if milestone_id:
        conn.execute(
            """INSERT INTO milestone_items (id, milestone_id, title, description, status, sort_order, created_by, created_at, updated_at, source_type, is_auto_created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), milestone_id, f'上传产出物：{file.filename}', f'文件大小：{format_file_size_static(file_size)}', 'completed', 0, user['id'], now, now, 'upload', 1)
        )
        conn.commit()

    conn.close()

    log_response("POST", f"/api/v1/projects/{project_id}/deliverables/upload", 200, "文件上传成功")

    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "deliverable_id": file_id,
            "name": stored_name,
            "original_name": file.filename,
            "file_size": file_size
        }
    }


@app.get("/api/v1/deliverables/{deliverable_id}/download")
async def download_deliverable(deliverable_id: str, request: Request):
    """下载产出物"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", f"/api/v1/deliverables/{deliverable_id}/download", user)

    conn = get_db()
    cursor = conn.execute("SELECT * FROM deliverables WHERE id = ?", (deliverable_id,))
    deliverable = cursor.fetchone()

    if not deliverable:
        conn.close()
        return {"code": 404, "message": "文件不存在"}

    # 检查项目成员权限
    project_id = deliverable['project_id']
    cursor = conn.execute(
        """SELECT COUNT(*) as count FROM project_members
           WHERE project_id = ? AND user_id = ?""",
        (project_id, user['id'])
    )
    member_count = cursor.fetchone()['count']

    logger = logging.getLogger(__name__)
    logger.info(f"Permission check: user_id={user['id']}, project_id={project_id}, member_count={member_count}")

    conn.close()

    # 只有项目成员可以下载文件
    if member_count == 0:
        logger.warning(f"Access denied: user {user['username']} ({user['id']}) is not a member of project {project_id}")
        return {"code": 403, "message": "无权限访问该文件"}

    file_path = deliverable['file_path']
    if not os.path.exists(file_path):
        return {"code": 404, "message": "文件不存在"}

    log_response("GET", f"/api/v1/deliverables/{deliverable_id}/download", 200, "文件下载")
    return FileResponse(file_path, filename=deliverable['original_name'])


@app.post("/api/v1/deliverables/batch-download")
async def batch_download_deliverables(request: Request):
    """批量下载产出物（打包成ZIP）"""
    import zipfile
    import io

    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    data = await request.json()
    deliverable_ids = data.get('deliverable_ids', [])

    if not deliverable_ids:
        return {"code": 400, "message": "请选择要下载的文件"}

    log_api_request("POST", "/api/v1/deliverables/batch-download", user, {"count": len(deliverable_ids)})

    conn = get_db()

    # 获取所有产出物信息
    placeholders = ','.join(['?' for _ in deliverable_ids])
    cursor = conn.execute(
        f"SELECT * FROM deliverables WHERE id IN ({placeholders})",
        deliverable_ids
    )
    deliverables = cursor.fetchall()

    if not deliverables:
        conn.close()
        return {"code": 404, "message": "文件不存在"}

    # 检查权限（所有文件都必须来自用户有权限的项目）
    for deliverable in deliverables:
        project_id = deliverable['project_id']
        cursor = conn.execute(
            """SELECT COUNT(*) as count FROM project_members
               WHERE project_id = ? AND user_id = ?""",
            (project_id, user['id'])
        )
        member_count = cursor.fetchone()['count']

        if member_count == 0:
            conn.close()
            return {"code": 403, "message": f"无权限访问文件: {deliverable['original_name']}"}

    conn.close()

    # 创建ZIP文件
    zip_buffer = io.BytesIO()

    # 用于追踪同名文件，添加序号
    name_counter = {}

    # 重新连接数据库以获取里程碑信息
    conn = get_db()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for deliverable in deliverables:
            file_path = deliverable['file_path']
            if os.path.exists(file_path):
                original_name = deliverable['original_name']
                milestone_id = deliverable.get('milestone_id')

                # 构建ZIP内文件名
                if milestone_id:
                    # 获取里程碑名称作为子目录
                    cursor = conn.execute("SELECT name FROM milestones WHERE id = ?", (milestone_id,))
                    milestone = cursor.fetchone()
                    milestone_name = milestone['name'] if milestone else '未分类'
                    zip_name = f"{milestone_name}/{original_name}"
                else:
                    zip_name = original_name

                # 处理同名冲突：添加序号
                if zip_name not in name_counter:
                    name_counter[zip_name] = 1  # 记录出现次数
                else:
                    name_counter[zip_name] += 1
                    # 添加序号（从1开始：报告(1).pdf, 报告(2).pdf...）
                    if '/' in zip_name:
                        dir_part, file_part = zip_name.rsplit('/', 1)
                        name, ext = os.path.splitext(file_part)
                        zip_name = f"{dir_part}/{name}({name_counter[zip_name]}){ext}"
                    else:
                        name, ext = os.path.splitext(zip_name)
                        zip_name = f"{name}({name_counter[zip_name]}){ext}"

                zip_file.write(file_path, zip_name)

    conn.close()

    zip_buffer.seek(0)

    log_response("POST", "/api/v1/deliverables/batch-download", 200, f"打包{len(deliverables)}个文件")

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=deliverables_{int(datetime.now().timestamp())}.zip"
        }
    )


# ===== API 路由：消息管理 =====

@app.get("/api/v1/messages")
async def get_messages(request: Request):
    """获取用户消息列表"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", "/api/v1/messages", user)

    is_read = request.query_params.get('is_read')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))

    conn = get_db()

    # 构建查询条件
    where_clause = "user_id = ?"
    params = [user['id']]

    if is_read is not None:
        where_clause += " AND is_read = ?"
        params.append(int(is_read))

    # 获取总数
    count_query = f"SELECT COUNT(*) as total FROM messages WHERE {where_clause}"
    cursor = conn.execute(count_query, params)
    total = cursor.fetchone()['total']

    # 获取分页数据
    offset = (page - 1) * page_size
    query = f"""
        SELECT * FROM messages
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor = conn.execute(query, params + [page_size, offset])
    messages = rows_to_list(cursor.fetchall())

    # 获取未读数量
    cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],))
    unread_count = cursor.fetchone()['count']

    conn.close()

    log_response("GET", "/api/v1/messages", 200, f"返回{len(messages)}条消息")

    return {
        "code": 0,
        "data": {
            "items": messages,
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size
        }
    }


@app.get("/api/v1/messages/unread-count")
async def get_unread_count(request: Request):
    """获取未读消息数量"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("GET", "/api/v1/messages/unread-count", user)

    conn = get_db()
    cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],))
    count = cursor.fetchone()['count']
    conn.close()

    log_response("GET", "/api/v1/messages/unread-count", 200, f"未读消息: {count}")
    return {"code": 0, "data": {"unread_count": count}}


@app.put("/api/v1/messages/{message_id}/read")
async def mark_message_read(message_id: str, request: Request):
    """标记消息为已读"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("PUT", f"/api/v1/messages/{message_id}/read", user)

    conn = get_db()
    conn.execute("UPDATE messages SET is_read = 1 WHERE id = ? AND user_id = ?", (message_id, user['id']))
    conn.commit()
    conn.close()

    log_response("PUT", f"/api/v1/messages/{message_id}/read", 200, "消息已标记为已读")
    return {"code": 0, "message": "标记成功"}


@app.put("/api/v1/messages/read-all")
async def mark_all_messages_read(request: Request):
    """标记所有消息为已读"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("PUT", "/api/v1/messages/read-all", user)

    conn = get_db()
    conn.execute("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],))
    conn.commit()

    cursor = conn.execute("SELECT changes() as count FROM messages WHERE user_id = ?", (user['id'],))
    count = cursor.fetchone()['count']
    conn.close()

    log_response("PUT", "/api/v1/messages/read-all", 200, f"标记了{count}条消息为已读")
    return {"code": 0, "message": "标记成功", "data": {"count": count}}


@app.delete("/api/v1/messages/{message_id}")
async def delete_message(message_id: str, request: Request):
    """删除消息"""
    user = get_current_user(request)

    if not user:
        return {"code": 401, "message": "未登录"}

    log_api_request("DELETE", f"/api/v1/messages/{message_id}", user)

    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id = ? AND user_id = ?", (message_id, user['id']))
    conn.commit()
    conn.close()

    log_response("DELETE", f"/api/v1/messages/{message_id}", 200, "消息删除成功")
    return {"code": 0, "message": "删除成功"}


# ===== WebSocket 配置 =====
from websocket.manager import WebSocketManager

# 创建 WebSocket 管理器
ws_manager = WebSocketManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket 端点

    连接地址: ws://host:8001/ws（可选token参数）
    无token连接后需调用 system.login 进行认证
    """
    # 接受连接
    success = await ws_manager.connect(websocket, token)
    if not success:
        return

    # 获取连接对象（通过临时ID或用户ID）
    connection = None
    for conn in ws_manager.active_connections.values():
        if conn.websocket == websocket:
            connection = conn
            break

    if not connection:
        await websocket.close()
        return

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理消息（内部会检查认证状态）
            response = await ws_manager.handle_message(data, connection)

            # 发送响应
            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端主动断开连接")
    except Exception as e:
        logger.error(f"WebSocket 异常: {str(e)}")
    finally:
        ws_manager.disconnect(websocket)


# ===== 后台任务：里程碑超时检查 =====

async def check_milestone_deadlines():
    """定期检查里程碑超时并发送消息提醒"""
    while True:
        try:
            now = datetime.now()
            check_time = now - timedelta(minutes=30)  # 只检查30分钟内未提醒过的

            conn = get_db()
            cursor = conn.execute("""
                SELECT m.*, u.id as owner_id, u.username as owner_name, p.name as project_name
                FROM milestones m
                LEFT JOIN users u ON m.created_by = u.id
                LEFT JOIN projects p ON m.project_id = p.id
                WHERE m.deadline IS NOT NULL
                AND m.deadline < ?
                AND m.status NOT IN ('completed', 'suspended')
                ORDER BY m.deadline ASC
            """, (now.isoformat(),))
            overdue_milestones = cursor.fetchall()

            for ms in overdue_milestones:
                milestone_id = ms['id']
                owner_id = ms['owner_id']

                if not owner_id:
                    continue

                # 检查是否在最近30分钟内已经发送过提醒
                cursor = conn.execute("""
                    SELECT id FROM messages
                    WHERE user_id = ?
                    AND type = 'deadline_warning'
                    AND related_id = ?
                    AND created_at > ?
                """, (owner_id, milestone_id, check_time.isoformat()))

                if not cursor.fetchone():
                    # 发送超时提醒消息
                    message_id = generate_id()
                    deadline_str = ms['deadline']
                    if isinstance(deadline_str, str):
                        try:
                            deadline_dt = datetime.fromisoformat(deadline_str)
                            deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pass

                    conn.execute("""
                        INSERT INTO messages (id, user_id, title, content, type, related_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        message_id,
                        owner_id,
                        f'里程碑超时提醒：{ms["name"]}',
                        f'项目：{ms["project_name"]}\n截止时间：{deadline_str}\n当前状态：{ms["status"]}\n\n该里程碑已超过截止时间，请及时处理。',
                        'deadline_warning',
                        milestone_id,
                        now.isoformat()
                    ))

                    logger.info(f'[超时提醒] 里程碑 {ms["name"]} ({ms["project_name"]}) 已超时，已通知 {ms["owner_name"]}')

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f'检查里程碑超时异常: {str(e)}')

        # 每5分钟检查一次
        await asyncio.sleep(300)


async def cleanup_sessions_background():
    """后台任务：定期清理过期会话"""
    while True:
        try:
            deleted_count = cleanup_expired_sessions()
            if deleted_count > 0:
                logger.info(f"会话清理完成: 删除 {deleted_count} 条过期记录")
        except Exception as e:
            logger.error(f"会话清理异常: {str(e)}")

        # 按配置的间隔执行清理
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL_MINUTES * 60)


# ===== 启动配置 =====

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("=" * 50)
    logger.info("YourWork 服务启动中...")
    logger.info("=" * 50)

    # 确保目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("uploads/projects", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    os.makedirs("static/img", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("templates/project", exist_ok=True)
    os.makedirs("templates/milestone", exist_ok=True)
    os.makedirs("templates/message", exist_ok=True)
    os.makedirs("templates/admin", exist_ok=True)
    os.makedirs("test/test_data", exist_ok=True)

    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        logger.info("数据库不存在，请运行 python init_db.py 初始化数据库")
    else:
        logger.info("数据库已就绪")

    # 启动里程碑超时检查后台任务
    asyncio.create_task(check_milestone_deadlines())
    logger.info("里程碑超时检查任务已启动")

    # 启动会话清理后台任务
    asyncio.create_task(cleanup_sessions_background())
    logger.info(f"会话清理任务已启动 (间隔: {SESSION_CLEANUP_INTERVAL_MINUTES} 分钟)")

    logger.info("=" * 50)
    logger.info("服务启动完成")
    logger.info("访问地址: http://localhost:8001")
    logger.info("API文档: http://localhost:8001/docs")
    logger.info("WebSocket: ws://localhost:8001/ws (可选token参数)")
    logger.info("=" * 50)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
