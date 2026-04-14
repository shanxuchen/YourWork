"""
WebSocket 接口处理器
所有 WebSocket 接口的处理逻辑集中在这里
"""
import sqlite3
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from websocket.schemas import WSResponse

# 从会话模块导入会话管理函数（避免循环导入）
from session import create_session, revoke_session, SESSION_DEFAULT_DURATION_HOURS

logger = logging.getLogger(__name__)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect("data/yourwork.db", timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def row_to_dict(row) -> Optional[Dict]:
    """将数据库行转换为字典"""
    return dict(row) if row else None


def rows_to_list(rows) -> List[Dict]:
    """将多行数据转换为字典列表"""
    return [dict(row) for row in rows]


def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """密码加密"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def check_permission(user: Optional[Dict], conn, required_roles: List[str] = None) -> bool:
    """检查用户权限"""
    if not user:
        return False

    if not required_roles:
        return True

    cursor = conn.execute(
        """SELECT r.code FROM user_roles ur
           JOIN roles r ON ur.role_id = r.id
           WHERE ur.user_id = ? AND r.code IN ({})
           """.format(','.join(['?' for _ in required_roles])),
        [user['id']] + required_roles
    )
    result = cursor.fetchone()
    return result is not None


def log_ws_action(user_id: str, action: str, request_id: str, response_code: int,
                   request_data: str = None, response_message: str = None,
                   error_message: str = None, ip_address: str = None):
    """记录 WebSocket 操作日志"""
    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO ws_logs (id, user_id, action, request_id, request_data,
               response_code, response_message, error_message, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), user_id, action, request_id, request_data,
             response_code, response_message, error_message, ip_address, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"记录 WebSocket 日志失败: {str(e)}")


class WebSocketHandlers:
    """WebSocket 接口处理器"""

    # ========== 系统接口 ==========

    @staticmethod
    async def system_login(data: dict, user: Optional[dict], conn, request_id: str,
                           ip_address: str = None, connection = None) -> WSResponse:
        """处理登录"""
        try:
            username = data.get('username')
            password = data.get('password')

            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            user_row = cursor.fetchone()

            if not user_row or not verify_password(password, user_row['password']):
                log_ws_action("", "system.login", request_id, 401,
                             request_data=json.dumps(data),
                             error_message="用户名或密码错误",
                             ip_address=ip_address)
                return WSResponse.error("system.login", request_id, 401, "用户名或密码错误")

            user_dict = row_to_dict(user_row)
            user_dict.pop('password', None)

            # 创建会话
            session_token = create_session(user_dict['id'])
            expires_at = datetime.now() + timedelta(hours=SESSION_DEFAULT_DURATION_HOURS)

            # 获取用户角色
            cursor = conn.execute(
                """SELECT r.code, r.name, r.description FROM user_roles ur
                   JOIN roles r ON ur.role_id = r.id
                   WHERE ur.user_id = ?""",
                (user_dict['id'],)
            )
            roles = rows_to_list(cursor.fetchall())
            user_dict['roles'] = [r['code'] for r in roles]

            # 获取可用接口列表
            capabilities = [
                {
                    "action": "project.create",
                    "description": "创建项目",
                    "params": {"name": "string - 项目名称", "description": "string - 项目描述（可选）"}
                },
                {
                    "action": "project.list",
                    "description": "获取项目列表",
                    "params": {"status": "string - 状态（可选）", "page": "int - 页码", "page_size": "int - 每页数量"}
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

            log_ws_action(user_dict['id'], "system.login", request_id, 0,
                         request_data=json.dumps(data),
                         response_message="登录成功",
                         ip_address=ip_address)

            # 更新连接认证状态（如果提供了连接对象）
            if connection:
                from websocket.manager import WebSocketManager
                # 需要通过全局manager或者传递manager实例来调用
                # 这里使用延迟导入避免循环引用
                import main
                await main.ws_manager.authenticate_connection(connection, user_dict['id'], user_dict, session_token)

            return WSResponse.success("system.login", request_id, {
                "session_token": session_token,
                "expires_at": expires_at.isoformat(),
                "session_timeout_hours": SESSION_DEFAULT_DURATION_HOURS,
                "user": user_dict,
                "capabilities": capabilities
            }, "登录成功")

        except Exception as e:
            logger.error(f"登录异常: {str(e)}")
            return WSResponse.error("system.login", request_id, 500, "服务器错误")

    @staticmethod
    async def system_capabilities(data: dict, user: Optional[dict], conn, request_id: str,
                                  ip_address: str = None, connection = None) -> WSResponse:
        """获取可用接口列表"""
        if not user:
            return WSResponse.error("system.capabilities", request_id, 401, "未登录")

        capabilities = [
            {"action": "project.create", "description": "创建项目",
             "params": {"name": "string - 项目名称", "description": "string - 项目描述（可选）"}},
            {"action": "project.list", "description": "获取项目列表",
             "params": {"status": "string - 状态（可选）", "page": "int - 页码", "page_size": "int - 每页数量"}},
            {"action": "milestone.create", "description": "创建里程碑",
             "params": {"project_id": "string - 项目ID", "name": "string - 里程碑名称"}},
        ]

        log_ws_action(user['id'], "system.capabilities", request_id, 0, ip_address=ip_address)

        return WSResponse.success("system.capabilities", request_id, {
            "session_timeout": 900,
            "capabilities": capabilities
        })

    @staticmethod
    async def system_ping(data: dict, user: Optional[dict], conn, request_id: str,
                         ip_address: str = None, connection = None) -> WSResponse:
        """心跳检测"""
        if not user:
            return WSResponse.error("system.ping", request_id, 401, "未登录")

        return WSResponse.success("system.ping", request_id, {
            "server_time": datetime.now().isoformat()
        }, "pong")

    @staticmethod
    async def system_logout(data: dict, user: Optional[dict], conn, request_id: str,
                           ip_address: str = None, connection = None) -> WSResponse:
        """用户登出（撤销会话）"""
        if not user:
            return WSResponse.error("system.logout", request_id, 401, "未登录")

        try:
            # 从请求中获取会话令牌
            session_token = data.get('session_token')
            if not session_token:
                return WSResponse.error("system.logout", request_id, 400, "缺少会话令牌")

            # 撤销会话
            if revoke_session(session_token):
                log_ws_action(user['id'], "system.logout", request_id, 0,
                             response_message="登出成功",
                             ip_address=ip_address)

                return WSResponse.success("system.logout", request_id, {
                    "message": "会话已撤销，请关闭连接"
                }, "登出成功")
            else:
                log_ws_action(user['id'], "system.logout", request_id, 404,
                             error_message="会话不存在或已撤销",
                             ip_address=ip_address)

                return WSResponse.error("system.logout", request_id, 404, "会话不存在或已撤销")

        except Exception as e:
            logger.error(f"登出异常: {str(e)}")
            return WSResponse.error("system.logout", request_id, 500, "服务器错误")

    # ========== 项目管理接口 ==========

    @staticmethod
    async def project_create(data: dict, user: Optional[dict], conn, request_id: str,
                            ip_address: str = None, connection = None) -> WSResponse:
        """创建项目"""
        if not user or not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            return WSResponse.error("project.create", request_id, 403, "无权限")

        project_name = data.get('name')
        description = data.get('description', '')

        project_id = generate_id()
        project_no = f"PRJ-{datetime.now().strftime('%Y%m%d')}-{project_id[:8]}"
        now = datetime.now().isoformat()

        conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, project_no, project_name, description, 'in_progress', now, now)
        )
        conn.commit()

        log_ws_action(user['id'], "project.create", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("project.create", request_id, {
            "id": project_id,
            "project_no": project_no,
            "name": project_name,
            "description": description,
            "status": "in_progress",
            "created_at": now
        }, "项目创建成功")

    @staticmethod
    async def project_list(data: dict, user: Optional[dict], conn, request_id: str,
                          ip_address: str = None, connection = None) -> WSResponse:
        """获取项目列表"""
        if not user:
            return WSResponse.error("project.list", request_id, 401, "未登录")

        status = data.get('status')
        keyword = data.get('keyword')
        page = int(data.get('page', 1))
        page_size = int(data.get('page_size', 20))

        where_conditions = []
        params = []

        if status:
            where_conditions.append("p.status = ?")
            params.append(status)

        if keyword:
            where_conditions.append("(p.name LIKE ? OR p.project_no LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        if not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            where_clause += f" AND EXISTS (SELECT 1 FROM project_members pm WHERE pm.project_id = p.id AND pm.user_id = '{user['id']}')"

        count_query = f"SELECT COUNT(*) as total FROM projects p WHERE {where_clause}"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()['total']

        offset = (page - 1) * page_size
        query = f"""
            SELECT p.* FROM projects p
            WHERE {where_clause}
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor = conn.execute(query, params + [page_size, offset])
        projects = rows_to_list(cursor.fetchall())

        log_ws_action(user['id'], "project.list", request_id, 0, ip_address=ip_address)

        return WSResponse.success("project.list", request_id, {
            "items": projects,
            "total": total,
            "page": page,
            "page_size": page_size
        })

    @staticmethod
    async def project_get(data: dict, user: Optional[dict], conn, request_id: str,
                         ip_address: str = None, connection = None) -> WSResponse:
        """获取项目详情"""
        if not user:
            return WSResponse.error("project.get", request_id, 401, "未登录")

        project_id = data.get('project_id')
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()

        if not project:
            return WSResponse.error("project.get", request_id, 404, "项目不存在")

        has_access = check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"])
        if not has_access:
            cursor = conn.execute("SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?",
                                (project_id, user['id']))
            has_access = cursor.fetchone() is not None

        if not has_access:
            return WSResponse.error("project.get", request_id, 403, "无权限")

        cursor = conn.execute("SELECT * FROM milestones WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
        milestones = rows_to_list(cursor.fetchall())

        cursor = conn.execute("""SELECT pm.*, u.username FROM project_members pm
                              LEFT JOIN users u ON pm.user_id = u.id
                              WHERE pm.project_id = ?""", (project_id,))
        members = rows_to_list(cursor.fetchall())

        cursor = conn.execute("SELECT * FROM deliverables WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        deliverables = rows_to_list(cursor.fetchall())

        log_ws_action(user['id'], "project.get", request_id, 0, ip_address=ip_address)

        return WSResponse.success("project.get", request_id, {
            "project": row_to_dict(project),
            "milestones": milestones,
            "members": members,
            "deliverables": deliverables
        })

    @staticmethod
    async def project_update(data: dict, user: Optional[dict], conn, request_id: str,
                            ip_address: str = None, connection = None) -> WSResponse:
        """更新项目"""
        if not user or not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            return WSResponse.error("project.update", request_id, 403, "无权限")

        project_id = data.get('project_id')
        name = data.get('name')
        description = data.get('description')

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE projects SET name = ?, description = ?, updated_at = ? WHERE id = ?",
            (name, description, now, project_id)
        )
        conn.commit()

        log_ws_action(user['id'], "project.update", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("project.update", request_id, {
            "id": project_id,
            "name": name,
            "description": description,
            "updated_at": now
        }, "项目更新成功")

    @staticmethod
    async def project_update_status(data: dict, user: Optional[dict], conn, request_id: str,
                                    ip_address: str = None, connection = None) -> WSResponse:
        """更新项目状态"""
        if not user or not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            return WSResponse.error("project.update_status", request_id, 403, "无权限")

        project_id = data.get('project_id')
        status = data.get('status')

        valid_statuses = ['in_progress', 'completed', 'ignored']
        if status not in valid_statuses:
            return WSResponse.error("project.update_status", request_id, 400,
                                   f"无效的状态值，必须是: {', '.join(valid_statuses)}")

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, project_id)
        )
        conn.commit()

        log_ws_action(user['id'], "project.update_status", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("project.update_status", request_id, {
            "id": project_id,
            "status": status,
            "updated_at": now
        }, "状态更新成功")

    # ========== 里程碑接口 ==========

    @staticmethod
    async def milestone_create(data: dict, user: Optional[dict], conn, request_id: str,
                              ip_address: str = None, connection = None) -> WSResponse:
        """创建里程碑"""
        if not user:
            return WSResponse.error("milestone.create", request_id, 401, "未登录")

        project_id = data.get('project_id')
        name = data.get('name')
        description = data.get('description', '')
        type = data.get('type', 'milestone')
        deadline = data.get('deadline')

        milestone_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, description, deadline, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (milestone_id, project_id, type, name, description, deadline, 'created', now, now)
        )
        conn.commit()

        conn.execute(
            "INSERT INTO milestone_logs (id, milestone_id, user_id, action, created_at) VALUES (?, ?, ?, ?, ?)",
            (generate_id(), milestone_id, user['id'], '创建里程碑', now)
        )
        conn.commit()

        log_ws_action(user['id'], "milestone.create", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("milestone.create", request_id, {
            "id": milestone_id,
            "project_id": project_id,
            "type": type,
            "name": name,
            "description": description,
            "deadline": deadline,
            "status": "created",
            "created_at": now
        }, "里程碑创建成功")

    @staticmethod
    async def milestone_list(data: dict, user: Optional[dict], conn, request_id: str,
                            ip_address: str = None, connection = None) -> WSResponse:
        """获取里程碑列表"""
        if not user:
            return WSResponse.error("milestone.list", request_id, 401, "未登录")

        project_id = data.get('project_id')
        cursor = conn.execute(
            "SELECT * FROM milestones WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,)
        )
        milestones = rows_to_list(cursor.fetchall())

        log_ws_action(user['id'], "milestone.list", request_id, 0, ip_address=ip_address)

        return WSResponse.success("milestone.list", request_id, {
            "items": milestones,
            "total": len(milestones)
        })

    @staticmethod
    async def milestone_get(data: dict, user: Optional[dict], conn, request_id: str,
                           ip_address: str = None, connection = None) -> WSResponse:
        """获取里程碑详情"""
        if not user:
            return WSResponse.error("milestone.get", request_id, 401, "未登录")

        milestone_id = data.get('milestone_id')
        cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        milestone = cursor.fetchone()

        if not milestone:
            return WSResponse.error("milestone.get", request_id, 404, "里程碑不存在")

        log_ws_action(user['id'], "milestone.get", request_id, 0, ip_address=ip_address)

        return WSResponse.success("milestone.get", request_id, row_to_dict(milestone))

    @staticmethod
    async def milestone_update(data: dict, user: Optional[dict], conn, request_id: str,
                              ip_address: str = None, connection = None) -> WSResponse:
        """更新里程碑"""
        if not user:
            return WSResponse.error("milestone.update", request_id, 401, "未登录")

        milestone_id = data.get('milestone_id')
        name = data.get('name')
        description = data.get('description')
        status = data.get('status')

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE milestones SET name = ?, description = ?, status = ?, updated_at = ? WHERE id = ?",
            (name, description, status, now, milestone_id)
        )
        conn.commit()

        conn.execute(
            "INSERT INTO milestone_logs (id, milestone_id, user_id, action, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (generate_id(), milestone_id, user['id'], '更新里程碑', f'状态改为: {status}', now)
        )
        conn.commit()

        log_ws_action(user['id'], "milestone.update", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("milestone.update", request_id, {
            "id": milestone_id,
            "name": name,
            "description": description,
            "status": status,
            "updated_at": now
        }, "里程碑更新成功")

    @staticmethod
    async def milestone_logs(data: dict, user: Optional[dict], conn, request_id: str,
                            ip_address: str = None, connection = None) -> WSResponse:
        """获取里程碑日志"""
        if not user:
            return WSResponse.error("milestone.logs", request_id, 401, "未登录")

        milestone_id = data.get('milestone_id')
        cursor = conn.execute(
            """SELECT ml.*, u.username FROM milestone_logs ml
               JOIN users u ON ml.user_id = u.id
               WHERE ml.milestone_id = ?
               ORDER BY ml.created_at DESC""",
            (milestone_id,)
        )
        logs = rows_to_list(cursor.fetchall())

        log_ws_action(user['id'], "milestone.logs", request_id, 0, ip_address=ip_address)

        return WSResponse.success("milestone.logs", request_id, {
            "items": logs,
            "total": len(logs)
        })

    @staticmethod
    async def milestone_add_log(data: dict, user: Optional[dict], conn, request_id: str,
                               ip_address: str = None, connection = None) -> WSResponse:
        """添加里程碑日志"""
        if not user:
            return WSResponse.error("milestone.add_log", request_id, 401, "未登录")

        milestone_id = data.get('milestone_id')
        action = data.get('action')
        description = data.get('description', '')

        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO milestone_logs (id, milestone_id, user_id, action, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (generate_id(), milestone_id, user['id'], action, description, now)
        )
        conn.commit()

        log_ws_action(user['id'], "milestone.add_log", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("milestone.add_log", request_id, {
            "id": generate_id(),
            "milestone_id": milestone_id,
            "action": action,
            "description": description,
            "created_at": now
        }, "日志添加成功")

    # ========== 产出物接口 ==========

    @staticmethod
    async def deliverable_upload(data: dict, user: Optional[dict], conn, request_id: str,
                                 ip_address: str = None, connection = None) -> WSResponse:
        """关联产出物"""
        if not user:
            return WSResponse.error("deliverable.upload", request_id, 401, "未登录")

        project_id = data.get('project_id')
        milestone_id = data.get('milestone_id')
        deliverable_id = data.get('deliverable_id')

        cursor = conn.execute("SELECT * FROM deliverables WHERE id = ?", (deliverable_id,))
        deliverable = cursor.fetchone()

        if not deliverable:
            return WSResponse.error("deliverable.upload", request_id, 404, "产出物不存在")

        log_ws_action(user['id'], "deliverable.upload", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("deliverable.upload", request_id, {
            "id": deliverable_id,
            "name": deliverable['name'],
            "original_name": deliverable['original_name'],
            "file_size": deliverable['file_size'],
            "file_type": deliverable['file_type'],
            "project_id": project_id,
            "milestone_id": milestone_id,
            "created_by": deliverable['created_by'],
            "created_at": deliverable['created_at']
        }, "产出物关联成功")

    @staticmethod
    async def deliverable_list(data: dict, user: Optional[dict], conn, request_id: str,
                              ip_address: str = None, connection = None) -> WSResponse:
        """获取产出物列表"""
        if not user:
            return WSResponse.error("deliverable.list", request_id, 401, "未登录")

        project_id = data.get('project_id')
        milestone_id = data.get('milestone_id')

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

        log_ws_action(user['id'], "deliverable.list", request_id, 0, ip_address=ip_address)

        return WSResponse.success("deliverable.list", request_id, {
            "items": deliverables,
            "total": len(deliverables)
        })

    @staticmethod
    async def deliverable_download(data: dict, user: Optional[dict], conn, request_id: str,
                                  ip_address: str = None, connection = None) -> WSResponse:
        """获取下载信息"""
        if not user:
            return WSResponse.error("deliverable.download", request_id, 401, "未登录")

        deliverable_id = data.get('deliverable_id')
        cursor = conn.execute("SELECT * FROM deliverables WHERE id = ?", (deliverable_id,))
        deliverable = cursor.fetchone()

        if not deliverable:
            return WSResponse.error("deliverable.download", request_id, 404, "产出物不存在")

        log_ws_action(user['id'], "deliverable.download", request_id, 0, ip_address=ip_address)

        return WSResponse.success("deliverable.download", request_id, {
            "deliverable_id": deliverable_id,
            "original_name": deliverable['original_name'],
            "download_url": f"/api/v1/deliverables/{deliverable_id}/download"
        })

    # ========== 项目成员接口 ==========

    @staticmethod
    async def project_add_member(data: dict, user: Optional[dict], conn, request_id: str,
                                 ip_address: str = None, connection = None) -> WSResponse:
        """添加项目成员"""
        if not user or not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            return WSResponse.error("project.add_member", request_id, 403, "无权限")

        project_id = data.get('project_id')
        user_id = data.get('user_id')
        display_name = data.get('display_name', '')
        roles = data.get('roles', [])

        cursor = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
        target_user = cursor.fetchone()

        if not target_user:
            return WSResponse.error("project.add_member", request_id, 404, "用户不存在")

        if not display_name:
            display_name = target_user['username']

        cursor = conn.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        if cursor.fetchone():
            return WSResponse.error("project.add_member", request_id, 400, "用户已是项目成员")

        member_id = generate_id()
        conn.execute(
            "INSERT INTO project_members (id, project_id, user_id, display_name, roles) VALUES (?, ?, ?, ?, ?)",
            (member_id, project_id, user_id, display_name, json.dumps(roles))
        )
        conn.commit()

        log_ws_action(user['id'], "project.add_member", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("project.add_member", request_id, {
            "id": member_id,
            "project_id": project_id,
            "user_id": user_id,
            "display_name": display_name,
            "roles": roles
        }, "成员添加成功")

    @staticmethod
    async def project_remove_member(data: dict, user: Optional[dict], conn, request_id: str,
                                    ip_address: str = None, connection = None) -> WSResponse:
        """移除项目成员"""
        if not user or not check_permission(user, conn, ["ADMIN", "SYSTEM_ADMIN"]):
            return WSResponse.error("project.remove_member", request_id, 403, "无权限")

        project_id = data.get('project_id')
        user_id = data.get('user_id')

        conn.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        conn.commit()

        log_ws_action(user['id'], "project.remove_member", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("project.remove_member", request_id, None, "成员移除成功")

    # ========== 用户接口 ==========

    @staticmethod
    async def user_profile(data: dict, user: Optional[dict], conn, request_id: str,
                          ip_address: str = None, connection = None) -> WSResponse:
        """获取用户信息"""
        if not user:
            return WSResponse.error("user.profile", request_id, 401, "未登录")

        cursor = conn.execute(
            """SELECT r.code, r.name, r.description FROM user_roles ur
               JOIN roles r ON ur.role_id = r.id
               WHERE ur.user_id = ?""",
            (user['id'],)
        )
        roles = rows_to_list(cursor.fetchall())

        user_info = user.copy()
        user_info['roles'] = roles

        log_ws_action(user['id'], "user.profile", request_id, 0, ip_address=ip_address)

        return WSResponse.success("user.profile", request_id, user_info)

    @staticmethod
    async def user_update_profile(data: dict, user: Optional[dict], conn, request_id: str,
                                 ip_address: str = None, connection = None) -> WSResponse:
        """更新用户信息"""
        if not user:
            return WSResponse.error("user.update_profile", request_id, 401, "未登录")

        display_name = data.get('display_name')
        email = data.get('email')

        now = datetime.now().isoformat()
        update_fields = []
        update_values = []
        params = []

        if display_name:
            update_fields.append("display_name = ?")
            params.append(display_name)
        if email:
            update_fields.append("email = ?")
            params.append(email)

        if update_fields:
            update_fields.append("updated_at = ?")
            params.extend([now, user['id']])

            conn.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
                params
            )
            conn.commit()

        log_ws_action(user['id'], "user.update_profile", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("user.update_profile", request_id, {
            "id": user['id'],
            "username": user['username'],
            "display_name": display_name or user.get('display_name'),
            "email": email or user.get('email'),
            "updated_at": now
        }, "用户信息更新成功")

    # ========== 消息接口 ==========

    @staticmethod
    async def message_list(data: dict, user: Optional[dict], conn, request_id: str,
                          ip_address: str = None, connection = None) -> WSResponse:
        """获取消息列表"""
        if not user:
            return WSResponse.error("message.list", request_id, 401, "未登录")

        is_read = data.get('is_read')
        page = int(data.get('page', 1))
        page_size = int(data.get('page_size', 20))

        where_clause = "user_id = ?"
        params = [user['id']]

        if is_read is not None:
            where_clause += " AND is_read = ?"
            params.append(int(is_read))

        count_query = f"SELECT COUNT(*) as total FROM messages WHERE {where_clause}"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()['total']

        offset = (page - 1) * page_size
        query = f"""
            SELECT * FROM messages
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor = conn.execute(query, params + [page_size, offset])
        messages = rows_to_list(cursor.fetchall())

        cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],))
        unread_count = cursor.fetchone()['count']

        log_ws_action(user['id'], "message.list", request_id, 0, ip_address=ip_address)

        return WSResponse.success("message.list", request_id, {
            "items": messages,
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size
        })

    @staticmethod
    async def message_unread_count(data: dict, user: Optional[dict], conn, request_id: str,
                                   ip_address: str = None, connection = None) -> WSResponse:
        """获取未读数量"""
        if not user:
            return WSResponse.error("message.unread_count", request_id, 401, "未登录")

        cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],))
        count = cursor.fetchone()['count']

        log_ws_action(user['id'], "message.unread_count", request_id, 0, ip_address=ip_address)

        return WSResponse.success("message.unread_count", request_id, {"unread_count": count})

    @staticmethod
    async def message_mark_read(data: dict, user: Optional[dict], conn, request_id: str,
                               ip_address: str = None, connection = None) -> WSResponse:
        """标记消息已读"""
        if not user:
            return WSResponse.error("message.mark_read", request_id, 401, "未登录")

        message_id = data.get('message_id')
        conn.execute("UPDATE messages SET is_read = 1 WHERE id = ? AND user_id = ?", (message_id, user['id']))
        conn.commit()

        log_ws_action(user['id'], "message.mark_read", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("message.mark_read", request_id, None, "标记成功")

    @staticmethod
    async def message_mark_all_read(data: dict, user: Optional[dict], conn, request_id: str,
                                    ip_address: str = None, connection = None) -> WSResponse:
        """标记全部已读"""
        if not user:
            return WSResponse.error("message.mark_all_read", request_id, 401, "未登录")

        conn.execute("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],))
        conn.commit()

        cursor = conn.execute("SELECT changes() as count", ())
        count = cursor.fetchone()['count']

        log_ws_action(user['id'], "message.mark_all_read", request_id, 0, ip_address=ip_address)

        return WSResponse.success("message.mark_all_read", request_id, {"count": count}, "标记成功")

    @staticmethod
    async def message_delete(data: dict, user: Optional[dict], conn, request_id: str,
                            ip_address: str = None, connection = None) -> WSResponse:
        """删除消息"""
        if not user:
            return WSResponse.error("message.delete", request_id, 401, "未登录")

        message_id = data.get('message_id')
        conn.execute("DELETE FROM messages WHERE id = ? AND user_id = ?", (message_id, user['id']))
        conn.commit()

        log_ws_action(user['id'], "message.delete", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("message.delete", request_id, None, "删除成功")

    # ========== 管理员接口 ==========

    @staticmethod
    async def admin_user_list(data: dict, user: Optional[dict], conn, request_id: str,
                              ip_address: str = None, connection = None) -> WSResponse:
        """获取用户列表"""
        if not user or not check_permission(user, conn, ["SYSTEM_ADMIN"]):
            return WSResponse.error("admin.user_list", request_id, 403, "无权限")

        cursor = conn.execute(
            "SELECT id, username, display_name, email, is_active, created_at FROM users ORDER BY created_at DESC"
        )
        users = rows_to_list(cursor.fetchall())

        log_ws_action(user['id'], "admin.user_list", request_id, 0, ip_address=ip_address)

        return WSResponse.success("admin.user_list", request_id, {
            "items": users,
            "total": len(users)
        })

    @staticmethod
    async def admin_update_user_roles(data: dict, user: Optional[dict], conn, request_id: str,
                                      ip_address: str = None, connection = None) -> WSResponse:
        """更新用户角色"""
        if not user or not check_permission(user, conn, ["SYSTEM_ADMIN"]):
            return WSResponse.error("admin.update_user_roles", request_id, 403, "无权限")

        target_user_id = data.get('user_id')
        role_codes = data.get('roles', [])

        conn.execute("DELETE FROM user_roles WHERE user_id = ?", (target_user_id,))

        for role_code in role_codes:
            cursor = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,))
            role = cursor.fetchone()
            if role:
                conn.execute(
                    "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                    (generate_id(), target_user_id, role['id'])
                )

        conn.commit()

        log_ws_action(user['id'], "admin.update_user_roles", request_id, 0,
                     request_data=json.dumps(data), ip_address=ip_address)

        return WSResponse.success("admin.update_user_roles", request_id, None, "角色更新成功")


# 接口路由映射
ACTION_HANDLERS = {
    # 系统接口
    "system.login": WebSocketHandlers.system_login,
    "system.capabilities": WebSocketHandlers.system_capabilities,
    "system.ping": WebSocketHandlers.system_ping,
    "system.logout": WebSocketHandlers.system_logout,

    # 项目管理
    "project.create": WebSocketHandlers.project_create,
    "project.list": WebSocketHandlers.project_list,
    "project.get": WebSocketHandlers.project_get,
    "project.update": WebSocketHandlers.project_update,
    "project.update_status": WebSocketHandlers.project_update_status,

    # 里程碑
    "milestone.create": WebSocketHandlers.milestone_create,
    "milestone.list": WebSocketHandlers.milestone_list,
    "milestone.get": WebSocketHandlers.milestone_get,
    "milestone.update": WebSocketHandlers.milestone_update,
    "milestone.logs": WebSocketHandlers.milestone_logs,
    "milestone.add_log": WebSocketHandlers.milestone_add_log,

    # 产出物
    "deliverable.upload": WebSocketHandlers.deliverable_upload,
    "deliverable.list": WebSocketHandlers.deliverable_list,
    "deliverable.download": WebSocketHandlers.deliverable_download,

    # 项目成员
    "project.add_member": WebSocketHandlers.project_add_member,
    "project.remove_member": WebSocketHandlers.project_remove_member,

    # 用户
    "user.profile": WebSocketHandlers.user_profile,
    "user.update_profile": WebSocketHandlers.user_update_profile,

    # 消息
    "message.list": WebSocketHandlers.message_list,
    "message.unread_count": WebSocketHandlers.message_unread_count,
    "message.mark_read": WebSocketHandlers.message_mark_read,
    "message.mark_all_read": WebSocketHandlers.message_mark_all_read,
    "message.delete": WebSocketHandlers.message_delete,

    # 管理员
    "admin.user_list": WebSocketHandlers.admin_user_list,
    "admin.update_user_roles": WebSocketHandlers.admin_update_user_roles,
}
