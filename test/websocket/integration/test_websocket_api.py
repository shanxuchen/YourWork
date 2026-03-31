"""
WebSocket 集成测试 - 测试 WebSocket API 接口
完整的 WebSocket 接口端到端测试
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

from fastapi.testclient import TestClient
from fastapi import WebSocket


class WebSocketAPITestBase(unittest.TestCase):
    """WebSocket API 测试基类"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建测试数据库
        cls.test_db_dir = tempfile.mkdtemp(prefix="yourwork_test_ws_")
        cls.test_db_path = os.path.join(cls.test_db_dir, "test.db")

        # 初始化测试数据库
        cls.setup_test_database()

        # 保存原始数据库路径
        import main
        cls.original_db_path = main.DB_PATH
        main.DB_PATH = cls.test_db_path

        # 导入 WebSocket 管理器
        from websocket.manager import WebSocketManager
        from websocket.handlers import ACTION_HANDLERS
        cls.ws_manager = WebSocketManager()
        cls.action_handlers = ACTION_HANDLERS

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        import main
        import shutil

        # 恢复原始数据库路径
        main.DB_PATH = cls.original_db_path

        # 删除测试数据库
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
                role_id TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (role_id) REFERENCES roles(id)
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
                display_name TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                type TEXT DEFAULT 'milestone',
                name TEXT NOT NULL,
                description TEXT,
                deliverables TEXT,
                deadline TEXT,
                status TEXT DEFAULT 'created',
                document TEXT,
                parent_id TEXT,
                execution_result TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS milestone_dependencies (
                id TEXT PRIMARY KEY,
                milestone_id TEXT NOT NULL,
                depends_on_id TEXT NOT NULL,
                FOREIGN KEY (milestone_id) REFERENCES milestones(id),
                FOREIGN KEY (depends_on_id) REFERENCES milestones(id)
            );

            CREATE TABLE IF NOT EXISTS milestone_logs (
                id TEXT PRIMARY KEY,
                milestone_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT,
                created_at TEXT,
                FOREIGN KEY (milestone_id) REFERENCES milestones(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
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
                created_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                type TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                related_id TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
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
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);
            CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_ws_logs_user ON ws_logs(user_id);
        """)

        # 插入角色
        now = "2024-01-01T00:00:00"
        roles = [
            ("role_001", "系统管理员", "SYSTEM_ADMIN", "拥有所有权限", 1),
            ("role_002", "管理员", "ADMIN", "可创建和管理项目", 1),
            ("role_003", "工作人员", "WORKER", "可参与项目工作", 1)
        ]

        for role_id, name, code, desc, is_system in roles:
            conn.execute(
                "INSERT INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
                (role_id, name, code, desc, is_system)
            )

        # 插入测试用户
        users = [
            ("user_admin", "admin", hashlib.sha256("admin123".encode()).hexdigest(),
             "系统管理员", "admin@test.com", 1),
            ("user_manager", "manager", hashlib.sha256("manager123".encode()).hexdigest(),
             "项目经理", "manager@test.com", 1),
            ("user_worker", "worker", hashlib.sha256("worker123".encode()).hexdigest(),
             "工作人员", "worker@test.com", 1),
        ]

        for user_id, username, password, display_name, email, is_active in users:
            conn.execute(
                """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, password, display_name, email, is_active, now, now)
            )

        # 分配角色
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_001", "user_admin", "role_001")
        )
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_002", "user_manager", "role_002")
        )
        conn.execute(
            "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
            ("ur_003", "user_worker", "role_003")
        )

        conn.commit()
        conn.close()

    def get_db(self):
        """获取测试数据库连接"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_token(self, username):
        """获取用户的 token（user_id）"""
        conn = self.get_db()
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user['id'] if user else None

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


class TestSystemAPI(WebSocketAPITestBase):
    """测试系统接口"""

    def test_system_ping(self):
        """测试心跳检测"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}
            conn = self.get_db()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "system.ping",
                    "request_id": "test_001",
                    "data": {}
                }, self.ws_manager.active_connections.get(user['id']) or MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertEqual(response["message"], "pong")
            self.assertIn("server_time", response["data"])

            conn.close()

        class MockConnection:
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

        asyncio.run(test())

    def test_system_capabilities(self):
        """测试获取可用接口"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}
            conn = self.get_db()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "system.capabilities",
                    "request_id": "test_002",
                    "data": {}
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertIn("capabilities", response["data"])
            self.assertIsInstance(response["data"]["capabilities"], list)

            conn.close()

        class MockConnection:
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

        asyncio.run(test())

    def test_system_login_success(self):
        """测试登录成功"""
        async def test():
            conn = self.get_db()

            class MockConnection:
                def __init__(self):
                    self.user = None  # No user for login
                    self.user_id = None
                    self.last_active_time = __import__('time').time()

                    class MockWebSocket:
                        client = type('obj', (object,), {'host': '127.0.0.1'})()

                    self.websocket = MockWebSocket()

                def update_active_time(self):
                    self.last_active_time = __import__('time').time()
                def is_timeout(self):
                    return False

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "system.login",
                    "request_id": "test_003",
                    "data": {
                        "username": "admin",
                        "password": "admin123"
                    }
                }, MockConnection())

            self.assertEqual(response["code"], 0)
            self.assertEqual(response["message"], "登录成功")
            self.assertIn("token", response["data"])
            self.assertIn("user", response["data"])
            self.assertEqual(response["data"]["user"]["username"], "admin")

            conn.close()

        asyncio.run(test())

    def test_system_login_invalid_credentials(self):
        """测试登录失败"""
        async def test():
            conn = self.get_db()

            class MockConnection:
                def __init__(self):
                    self.user = None  # No user for login
                    self.user_id = None
                    self.last_active_time = __import__('time').time()

                    class MockWebSocket:
                        client = type('obj', (object,), {'host': '127.0.0.1'})()

                    self.websocket = MockWebSocket()

                def update_active_time(self):
                    self.last_active_time = __import__('time').time()
                def is_timeout(self):
                    return False

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "system.login",
                    "request_id": "test_004",
                    "data": {
                        "username": "admin",
                        "password": "wrongpassword"
                    }
                }, MockConnection())

            self.assertEqual(response["code"], 401)
            self.assertEqual(response["message"], "用户名或密码错误")

            conn.close()

        asyncio.run(test())


class TestProjectAPI(WebSocketAPITestBase):
    """测试项目管理接口"""

    def test_project_create(self):
        """测试创建项目"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "project.create",
                    "request_id": "test_005",
                    "data": {
                        "name": "集成测试项目",
                        "description": "通过集成测试创建"
                    }
                }, MockConnection(user))

                self.assertEqual(response["code"], 0)
                self.assertEqual(response["message"], "项目创建成功")
                self.assertIn("project_no", response["data"])
                self.assertTrue(response["data"]["project_no"].startswith("PRJ-"))

                # 验证数据库中确实创建了项目（在TestDbPatch上下文中验证）
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM projects WHERE project_no = ?",
                    (response["data"]["project_no"],)
                )
                project = cursor.fetchone()
                self.assertIsNotNone(project)
                self.assertEqual(project["name"], "集成测试项目")
                conn.close()

        class MockConnection:
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

        asyncio.run(test())

    def test_project_list(self):
        """测试获取项目列表"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}

            with self.TestDbPatch(self.test_db_path):
                # 先创建一个测试项目
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row
                conn.execute(
                    "INSERT INTO projects (id, project_no, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("test_proj", "PRJ-TEST", "测试项目", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                )
                conn.commit()
                conn.close()

                response = await self.ws_manager.handle_message({
                    "action": "project.list",
                    "request_id": "test_006",
                    "data": {
                        "page": 1,
                        "page_size": 10
                    }
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertIn("items", response["data"])
            self.assertIn("total", response["data"])
            self.assertGreaterEqual(response["data"]["total"], 1)

        class MockConnection:
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

        asyncio.run(test())

    def test_project_update_status(self):
        """测试更新项目状态"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}

            with self.TestDbPatch(self.test_db_path):
                # 创建测试项目
                import sqlite3
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row
                conn.execute(
                    "INSERT INTO projects (id, project_no, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("test_proj", "PRJ-TEST", "测试项目", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                )
                conn.commit()
                conn.close()

                response = await self.ws_manager.handle_message({
                    "action": "project.update_status",
                    "request_id": "test_007",
                    "data": {
                        "project_id": "test_proj",
                        "status": "completed"
                    }
                }, MockConnection(user))

                self.assertEqual(response["code"], 0)
                self.assertEqual(response["message"], "状态更新成功")

                # 验证状态已更新
                conn = sqlite3.connect("data/yourwork.db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT status FROM projects WHERE id = ?", ("test_proj",))
                project = cursor.fetchone()
                self.assertEqual(project["status"], "completed")
                conn.close()

        class MockConnection:
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

        asyncio.run(test())


class TestMilestoneAPI(WebSocketAPITestBase):
    """测试里程碑接口"""

    def test_milestone_create(self):
        """测试创建里程碑"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}
            conn = self.get_db()

            # 创建测试项目
            conn.execute(
                "INSERT INTO projects (id, project_no, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("test_proj", "PRJ-TEST", "测试项目", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )
            conn.commit()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "milestone.create",
                    "request_id": "test_008",
                    "data": {
                        "project_id": "test_proj",
                        "name": "测试里程碑",
                        "description": "测试描述",
                        "type": "milestone"
                    }
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertEqual(response["message"], "里程碑创建成功")
            self.assertIn("id", response["data"])
            self.assertEqual(response["data"]["name"], "测试里程碑")

            conn.close()

        class MockConnection:
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

        asyncio.run(test())


class TestUserAPI(WebSocketAPITestBase):
    """测试用户接口"""

    def test_user_profile(self):
        """测试获取用户信息"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin", "display_name": "系统管理员"}
            conn = self.get_db()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "user.profile",
                    "request_id": "test_009",
                    "data": {}
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertEqual(response["data"]["username"], "admin")
            self.assertIn("roles", response["data"])

            conn.close()

        class MockConnection:
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

        asyncio.run(test())


class TestMessageAPI(WebSocketAPITestBase):
    """测试消息接口"""

    def test_message_unread_count(self):
        """测试获取未读消息数量"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}
            conn = self.get_db()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "message.unread_count",
                    "request_id": "test_010",
                    "data": {}
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertIn("unread_count", response["data"])

            conn.close()

        class MockConnection:
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

        asyncio.run(test())


class TestAdminAPI(WebSocketAPITestBase):
    """测试管理员接口"""

    def test_admin_user_list(self):
        """测试获取用户列表"""
        async def test():
            user = {"id": self.get_user_token("admin"), "username": "admin"}
            conn = self.get_db()

            with self.TestDbPatch(self.test_db_path):
                response = await self.ws_manager.handle_message({
                    "action": "admin.user_list",
                    "request_id": "test_011",
                    "data": {}
                }, MockConnection(user))

            self.assertEqual(response["code"], 0)
            self.assertIn("items", response["data"])
            self.assertIn("total", response["data"])
            # 应该有至少3个测试用户
            self.assertGreaterEqual(response["data"]["total"], 3)

            conn.close()

        class MockConnection:
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

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
