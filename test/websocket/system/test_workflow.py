"""
WebSocket 流程测试 - 测试完整的业务流程
测试端到端的业务场景
"""

import os
import sys
import unittest
import asyncio
import json
import tempfile
import sqlite3
import hashlib

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from websocket.manager import WebSocketManager
from websocket.handlers import ACTION_HANDLERS


class WorkflowTestBase(unittest.TestCase):
    """流程测试基类"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.test_db_dir = tempfile.mkdtemp(prefix="yourwork_test_workflow_")
        cls.test_db_path = os.path.join(cls.test_db_dir, "test.db")

        cls.setup_test_database()

        # 保存原始数据库路径
        import main
        cls.original_db_path = main.DB_PATH
        main.DB_PATH = cls.test_db_path

        cls.ws_manager = WebSocketManager()

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        import main
        import shutil

        main.DB_PATH = cls.original_db_path

        if os.path.exists(cls.test_db_dir):
            shutil.rmtree(cls.test_db_dir)

    @classmethod
    def setup_test_database(cls):
        """设置测试数据库"""
        conn = sqlite3.connect(cls.test_db_path)
        conn.row_factory = sqlite3.Row

        # 创建所有表
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                display_name TEXT,
                email TEXT,
                avatar TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                is_system INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                project_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'in_progress',
                resources TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS project_members (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                roles TEXT,
                display_name TEXT
            );

            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                type TEXT DEFAULT 'milestone',
                name TEXT NOT NULL,
                description TEXT,
                deadline TEXT,
                status TEXT DEFAULT 'created',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS milestone_logs (
                id TEXT PRIMARY KEY,
                milestone_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS deliverables (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_type TEXT,
                project_id TEXT NOT NULL,
                milestone_id TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                type TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT
            );

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
                created_at TEXT NOT NULL
            );
        """)

        # 插入角色
        now = "2024-01-01T00:00:00"
        conn.execute(
            "INSERT INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
            ("role_admin", "系统管理员", "SYSTEM_ADMIN", "拥有所有权限", 1)
        )
        conn.execute(
            "INSERT INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
            ("role_manager", "管理员", "ADMIN", "可创建和管理项目", 1)
        )
        conn.execute(
            "INSERT INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
            ("role_worker", "工作人员", "WORKER", "可参与项目工作", 1)
        )

        # 插入测试用户
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("user_admin", "admin", hashlib.sha256("admin123".encode()).hexdigest(),
             "系统管理员", "admin@test.com", 1, now, now)
        )
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("user_manager", "manager", hashlib.sha256("manager123".encode()).hexdigest(),
             "项目经理", "manager@test.com", 1, now, now)
        )
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("user_worker", "worker", hashlib.sha256("worker123".encode()).hexdigest(),
             "工作人员", "worker@test.com", 1, now, now)
        )

        # 分配角色
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_001", "user_admin", "role_admin")
        )
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_002", "user_manager", "role_manager")
        )
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_003", "user_worker", "role_worker")
        )

        conn.commit()
        conn.close()

    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user(self, username):
        """获取用户信息"""
        conn = self.get_db()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    class TestDbPatch:
        """测试数据库路径补丁上下文管理器"""
        def __init__(self, test_db_path):
            self.test_db_path = test_db_path
            self.original_db_path = None

        def __enter__(self):
            import main
            import shutil
            import os

            # Save the original database path
            self.original_db_path = main.DB_PATH

            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)

            # Copy test database to the expected location
            if os.path.exists("data/yourwork.db"):
                os.remove("data/yourwork.db")
            shutil.copy2(self.test_db_path, "data/yourwork.db")

            # Set the database path
            main.DB_PATH = "data/yourwork.db"

            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            import main
            import os

            # Restore original database path
            main.DB_PATH = self.original_db_path

            # Clean up the test database file
            if os.path.exists("data/yourwork.db"):
                try:
                    os.remove("data/yourwork.db")
                except:
                    pass  # Ignore cleanup errors

    class MockConnection:
        """模拟 WebSocket 连接"""
        def __init__(self, user):
            self.user = user
            self.user_id = user.get('id', 'test_user_id')
            self.last_active_time = __import__('time').time()

            class MockWebSocket:
                client = type('obj', (object,), {'host': '127.0.0.1'})()

            self.websocket = MockWebSocket()

        def update_active_time(self):
            """更新最后活跃时间"""
            self.last_active_time = __import__('time').time()

        def is_timeout(self) -> bool:
            """检查是否超时"""
            return False  # 测试环境永不超时

    async def handle_message(self, user, action, data, request_id):
        """处理消息的辅助方法"""
        return await self.ws_manager.handle_message({
            "action": action,
            "request_id": request_id,
            "data": data
        }, self.MockConnection(user))


class TestProjectManagementWorkflow(WorkflowTestBase):
    """测试项目管理完整流程"""

    def test_complete_project_lifecycle(self):
        """测试完整的项目生命周期：创建 -> 添加成员 -> 添加里程碑 -> 更新状态 -> 完成"""

        async def test():
            admin = self.get_user("admin")

            # 使用 TestDbPatch 覆盖整个工作流
            with self.TestDbPatch(self.test_db_path):
                # ===== 步骤1: 创建项目 =====
                print("\n[步骤1] 创建项目")
                response = await self.handle_message(admin, "project.create", {
                    "name": "测试项目 - 完整流程",
                    "description": "测试项目管理的完整流程"
                }, "workflow_001")

                self.assertEqual(response["code"], 0, f"创建项目失败: {response}")
                project_id = response["data"]["id"]
                project_no = response["data"]["project_no"]
                print(f"  项目创建成功: {project_no}")

                # 验证项目存在
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
                project = cursor.fetchone()
                self.assertIsNotNone(project)
                self.assertEqual(project["status"], "in_progress")

                # ===== 步骤2: 添加项目成员 =====
                print("\n[步骤2] 添加项目成员")
                response = await self.handle_message(admin, "project.add_member", {
                    "project_id": project_id,
                    "user_id": "user_manager",
                    "display_name": "项目经理",
                    "roles": ["管理", "测试"]
                }, "workflow_002")

                self.assertEqual(response["code"], 0, f"添加成员失败: {response}")
                print(f"  成员添加成功: 项目经理")

                # 验证成员已添加
                cursor = conn.execute("SELECT * FROM project_members WHERE project_id = ?", (project_id,))
                members = cursor.fetchall()
                self.assertEqual(len(members), 1)

                # ===== 步骤3: 创建里程碑 =====
                print("\n[步骤3] 创建里程碑")
                milestones = [
                    {"name": "需求分析", "type": "milestone", "description": "完成需求文档"},
                    {"name": "系统设计", "type": "milestone", "description": "完成设计文档"},
                    {"name": "开发实现", "type": "milestone", "description": "完成代码开发"}
                ]

                milestone_ids = []
                for i, ms in enumerate(milestones, 1):
                    response = await self.handle_message(admin, "milestone.create", {
                        "project_id": project_id,
                        "name": ms["name"],
                        "description": ms["description"],
                        "type": ms["type"]
                    }, f"workflow_003_{i}")

                    self.assertEqual(response["code"], 0, f"创建里程碑{i}失败: {response}")
                    milestone_ids.append(response["data"]["id"])
                    print(f"  里程碑{i}创建成功: {ms['name']}")

                # 验证里程碑已创建
                cursor = conn.execute("SELECT COUNT(*) as count FROM milestones WHERE project_id = ?", (project_id,))
                count = cursor.fetchone()["count"]
                self.assertEqual(count, 3)

                # ===== 步骤4: 更新里程碑状态 =====
                print("\n[步骤4] 更新里程碑状态")
                response = await self.handle_message(admin, "milestone.update", {
                    "milestone_id": milestone_ids[0],
                    "name": "需求分析",
                    "description": "完成需求文档",
                    "status": "completed"
                }, "workflow_004")

                self.assertEqual(response["code"], 0, f"更新里程碑失败: {response}")
                print(f"  里程碑状态更新: 需求分析 -> completed")

                # ===== 步骤5: 更新项目状态为完成 =====
                print("\n[步骤5] 更新项目状态")
                response = await self.handle_message(admin, "project.update_status", {
                    "project_id": project_id,
                    "status": "completed"
                }, "workflow_005")

                self.assertEqual(response["code"], 0, f"更新项目状态失败: {response}")
                print(f"  项目状态更新: in_progress -> completed")

                # 验证项目状态
                cursor = conn.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
                project = cursor.fetchone()
                self.assertEqual(project["status"], "completed")

                # ===== 验证：检查项目详情 =====
                print("\n[验证] 检查项目详情")
                response = await self.handle_message(admin, "project.get", {
                    "project_id": project_id
                }, "workflow_006")

                self.assertEqual(response["code"], 0)
                project_data = response["data"]["project"]
                self.assertEqual(project_data["status"], "completed")
                self.assertEqual(len(response["data"]["milestones"]), 3)
                self.assertEqual(len(response["data"]["members"]), 1)

                print(f"\n[完成] 项目管理流程测试通过!")
                print(f"  项目编号: {project_no}")
                print(f"  项目状态: {project_data['status']}")
                print(f"  里程碑数: {len(response['data']['milestones'])}")
                print(f"  成员数: {len(response['data']['members'])}")

                conn.close()

        asyncio.run(test())


class TestMilestoneWorkflow(WorkflowTestBase):
    """测试里程碑管理流程"""

    def test_milestone_complete_workflow(self):
        """测试里程碑完整流程：创建 -> 更新 -> 添加日志 -> 完成"""

        async def test():
            admin = self.get_user("admin")

            # 使用 TestDbPatch 覆盖整个工作流
            with self.TestDbPatch(self.test_db_path):
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row

                # 先创建测试项目
                conn.execute(
                    "INSERT INTO projects (id, project_no, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("proj_test", "PRJ-WORKFLOW", "工作流测试项目", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                )
                conn.commit()

                # ===== 步骤1: 创建里程碑 =====
                print("\n[步骤1] 创建里程碑")
                response = await self.handle_message(admin, "milestone.create", {
                    "project_id": "proj_test",
                    "name": "工作流测试里程碑",
                    "description": "测试完整工作流",
                    "type": "milestone",
                    "deadline": "2024-12-31"
                }, "workflow_101")

                self.assertEqual(response["code"], 0)
                milestone_id = response["data"]["id"]
                print(f"  里程碑创建成功: {response['data']['name']}")

                # ===== 步骤2: 更新里程碑状态 =====
                print("\n[步骤2] 更新里程碑状态")
                response = await self.handle_message(admin, "milestone.update", {
                    "milestone_id": milestone_id,
                    "name": "工作流测试里程碑",
                    "description": "更新后的描述",
                    "status": "in_progress"
                }, "workflow_102")

                self.assertEqual(response["code"], 0)
                print(f"  状态更新: created -> in_progress")

                # ===== 步骤3: 添加操作日志 =====
                print("\n[步骤3] 添加操作日志")
                response = await self.handle_message(admin, "milestone.add_log", {
                    "milestone_id": milestone_id,
                    "action": "开始执行",
                    "description": "开始开发工作"
                }, "workflow_103")

                self.assertEqual(response["code"], 0)
                print(f"  日志添加成功")

                # 验证日志已添加
                cursor = conn.execute(
                    "SELECT * FROM milestone_logs WHERE milestone_id = ? ORDER BY created_at DESC",
                    (milestone_id,)
                )
                logs = cursor.fetchall()
                self.assertGreater(len(logs), 0)

                # ===== 步骤4: 完成里程碑 =====
                print("\n[步骤4] 完成里程碑")
                response = await self.handle_message(admin, "milestone.update", {
                    "milestone_id": milestone_id,
                    "name": "工作流测试里程碑",
                    "status": "completed"
                }, "workflow_104")

                self.assertEqual(response["code"], 0)
                print(f"  状态更新: in_progress -> completed")

                # ===== 验证：获取里程碑日志 =====
                print("\n[验证] 获取里程碑日志")
                response = await self.handle_message(admin, "milestone.logs", {
                    "milestone_id": milestone_id
                }, "workflow_105")

                self.assertEqual(response["code"], 0)
                self.assertGreater(len(response["data"]["items"]), 0)
                print(f"  日志条数: {len(response['data']['items'])}")

                print(f"\n[完成] 里程碑工作流测试通过!")

                conn.close()

        asyncio.run(test())


class TestUserManagementWorkflow(WorkflowTestBase):
    """测试用户管理流程"""

    def test_admin_user_management_workflow(self):
        """测试管理员用户管理流程：获取用户列表 -> 更新用户角色"""

        async def test():
            admin = self.get_user("admin")

            # 使用 TestDbPatch 覆盖整个工作流
            with self.TestDbPatch(self.test_db_path):
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row

                # ===== 步骤1: 获取用户列表 =====
                print("\n[步骤1] 获取用户列表")
                response = await self.handle_message(admin, "admin.user_list", {}, "workflow_201")

                self.assertEqual(response["code"], 0)
                users = response["data"]["items"]
                total_users = response["data"]["total"]
                print(f"  用户列表获取成功，共 {total_users} 个用户")

                # ===== 步骤2: 更新用户角色 =====
                print("\n[步骤2] 更新用户角色")
                worker_user = self.get_user("worker")

                response = await self.handle_message(admin, "admin.update_user_roles", {
                    "user_id": worker_user["id"],
                    "roles": ["ADMIN", "WORKER"]  # 升职为管理员
                }, "workflow_202")

                self.assertEqual(response["code"], 0)
                print(f"  用户角色更新成功: {worker_user['username']} -> ADMIN, WORKER")

                # 验证角色已更新
                cursor = conn.execute(
                    """SELECT r.code FROM user_roles ur
                       JOIN roles r ON ur.role_id = r.id
                       WHERE ur.user_id = ?""",
                    (worker_user["id"],)
                )
                roles = [row["code"] for row in cursor.fetchall()]
                self.assertIn("ADMIN", roles)
                self.assertIn("WORKER", roles)

                # ===== 步骤3: 再次获取用户信息验证 =====
                print("\n[步骤3] 验证角色更新")
                response = await self.handle_message(admin, "user.profile", {}, "workflow_203")

                self.assertEqual(response["code"], 0)
                print(f"  用户信息获取成功")

                print(f"\n[完成] 用户管理工作流测试通过!")

                conn.close()

        asyncio.run(test())


class TestCollaborationWorkflow(WorkflowTestBase):
    """测试协作流程"""

    def test_project_collaboration_workflow(self):
        """测试项目协作流程：创建项目 -> 添加多个成员 -> 各自创建里程碑"""

        async def test():
            admin = self.get_user("admin")
            manager = self.get_user("manager")
            worker = self.get_user("worker")

            # 使用 TestDbPatch 覆盖整个工作流
            with self.TestDbPatch(self.test_db_path):
                # ===== 步骤1: 管理员创建项目 =====
                print("\n[步骤1] 管理员创建协作项目")
                response = await self.handle_message(admin, "project.create", {
                    "name": "协作测试项目",
                    "description": "多人协作项目"
                }, "workflow_301")

                self.assertEqual(response["code"], 0)
                project_id = response["data"]["id"]
                print(f"  项目创建成功: {response['data']['project_no']}")

                # ===== 步骤2: 添加项目经理和工作人员 =====
                print("\n[步骤2] 添加项目成员")

                # 添加项目经理
                response = await self.handle_message(admin, "project.add_member", {
                    "project_id": project_id,
                    "user_id": manager["id"],
                    "display_name": "项目经理",
                    "roles": ["项目管理"]
                }, "workflow_302")
                self.assertEqual(response["code"], 0)

                # 添加工作人员
                response = await self.handle_message(admin, "project.add_member", {
                    "project_id": project_id,
                    "user_id": worker["id"],
                    "display_name": "开发人员",
                    "roles": ["开发"]
                }, "workflow_303")
                self.assertEqual(response["code"], 0)
                print(f"  添加了 2 名成员")

                # ===== 步骤3: 项目经理创建里程碑 =====
                print("\n[步骤3] 项目经理创建里程碑")
                response = await self.handle_message(manager, "milestone.create", {
                    "project_id": project_id,
                    "name": "里程碑1",
                    "description": "第一个里程碑",
                    "type": "milestone"
                }, "workflow_304")

                self.assertEqual(response["code"], 0)
                milestone_id = response["data"]["id"]
                print(f"  里程碑创建成功")

                # ===== 步骤4: 工作人员添加日志 =====
                print("\n[步骤4] 工作人员添加进度日志")
                response = await self.handle_message(worker, "milestone.add_log", {
                    "milestone_id": milestone_id,
                    "action": "进度更新",
                    "description": "完成50%"
                }, "workflow_305")

                self.assertEqual(response["code"], 0)
                print(f"  日志添加成功")

                # ===== 验证：获取项目详情 =====
                print("\n[验证] 获取项目详情验证协作")
                response = await self.handle_message(admin, "project.get", {
                    "project_id": project_id
                }, "workflow_306")

                self.assertEqual(response["code"], 0)
                self.assertEqual(len(response["data"]["members"]), 2)
                self.assertGreaterEqual(len(response["data"]["milestones"]), 1)

                print(f"\n[完成] 协作流程测试通过!")
                print(f"  项目成员数: {len(response['data']['members'])}")
                print(f"  里程碑数: {len(response['data']['milestones'])}")

        asyncio.run(test())


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
