"""
WebSocket 单元测试 - 测试 handlers 模块
测试 WebSocket 接口处理器的核心逻辑
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import json
import hashlib
from unittest.mock import Mock, AsyncMock, patch

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from websocket.handlers import (
    WebSocketHandlers,
    generate_id,
    hash_password,
    verify_password,
    row_to_dict,
    rows_to_list,
    check_permission
)
from websocket import handlers as handlers_module


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""

    def test_generate_id(self):
        """测试生成唯一ID"""
        id1 = generate_id()
        id2 = generate_id()

        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertEqual(len(id1), 36)  # UUID 格式

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test123"
        hashed = hash_password(password)

        self.assertIsInstance(hashed, str)
        self.assertEqual(len(hashed), 64)  # SHA256 输出长度

    def test_verify_password(self):
        """测试密码验证"""
        password = "test123"
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_row_to_dict(self):
        """测试数据库行转字典"""
        # 模拟数据库行对象
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        row = MockRow({"id": "123", "name": "Test"})
        result = row_to_dict(row)

        self.assertEqual(result["id"], "123")
        self.assertEqual(result["name"], "Test")

    def test_row_to_dict_with_none(self):
        """测试空行转字典"""
        result = row_to_dict(None)
        self.assertIsNone(result)

    def test_rows_to_list(self):
        """测试多行转列表"""
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        rows = [
            MockRow({"id": "1", "name": "Test1"}),
            MockRow({"id": "2", "name": "Test2"})
        ]

        result = rows_to_list(rows)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[1]["name"], "Test2")


class TestCheckPermission(unittest.TestCase):
    """测试权限检查功能"""

    @classmethod
    def setUpClass(cls):
        """设置测试数据库"""
        cls.test_db_path = os.path.join(tempfile.mkdtemp(), "test_permissions.db")
        conn = sqlite3.connect(cls.test_db_path)
        conn.row_factory = sqlite3.Row

        # 创建表
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL
            );
        """)

        # 插入测试数据
        user_id = "user_001"
        role_id = "role_001"

        conn.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, "testuser"))
        conn.execute("INSERT INTO roles (id, code) VALUES (?, ?)", (role_id, "ADMIN"))
        conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        """清理测试数据库"""
        import shutil
        db_dir = os.path.dirname(cls.test_db_path)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)

    def test_check_permission_with_valid_role(self):
        """测试有权限的用户"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row

        user = {"id": "user_001"}
        result = check_permission(user, conn, ["ADMIN"])

        self.assertTrue(result)
        conn.close()

    def test_check_permission_with_invalid_role(self):
        """测试无权限的用户"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row

        user = {"id": "user_001"}
        result = check_permission(user, conn, ["SYSTEM_ADMIN"])

        self.assertFalse(result)
        conn.close()

    def test_check_permission_with_no_roles_required(self):
        """测试不要求角色时"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row

        user = {"id": "user_001"}
        result = check_permission(user, conn, [])

        self.assertTrue(result)
        conn.close()

    def test_check_permission_with_no_user(self):
        """测试无用户时"""
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row

        result = check_permission(None, conn, ["ADMIN"])

        self.assertFalse(result)
        conn.close()


class TestSystemHandlers(unittest.TestCase):
    """测试系统接口处理器"""

    def test_system_ping_response(self):
        """测试 system.ping 接口"""
        import asyncio

        async def run_test():
            user = {"id": "test_user", "username": "test"}
            conn = sqlite3.connect(":memory:")

            response = await WebSocketHandlers.system_ping(
                data={},
                user=user,
                conn=conn,
                request_id="req_001",
                ip_address="127.0.0.1"
            )

            self.assertEqual(response.code, 0)
            self.assertEqual(response.message, "pong")
            self.assertIn("server_time", response.data)
            conn.close()

        asyncio.run(run_test())

    def test_system_login_with_invalid_credentials(self):
        """测试 system.login 错误凭据"""
        import asyncio

        async def run_test():
            conn = sqlite3.connect(":memory:")
            # 设置数据库表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id TEXT PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id TEXT,
                    role_id TEXT,
                    PRIMARY KEY (user_id, role_id)
                )
            """)
            # 添加一个测试用户（不是测试中尝试登录的用户）
            conn.execute(
                "INSERT INTO users (id, username, password, email, is_active) VALUES (?, ?, ?, ?, ?)",
                ("other_user", "other", "hash", "other@test.com", 1)
            )
            conn.commit()

            response = await WebSocketHandlers.system_login(
                data={"username": "invalid", "password": "wrong"},
                user=None,
                conn=conn,
                request_id="req_001",
                ip_address="127.0.0.1"
            )

            self.assertEqual(response.code, 401)
            self.assertEqual(response.message, "用户名或密码错误")
            conn.close()

        asyncio.run(run_test())


class TestProjectHandlers(unittest.TestCase):
    """测试项目管理接口处理器"""

    def test_project_create_response_structure(self):
        """测试 project.create 响应结构"""
        import asyncio

        async def run_test():
            # 创建内存数据库并初始化表
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            init_test_tables(conn)

            # 添加测试用户和角色
            conn.execute("INSERT INTO users (id, username) VALUES (?, ?)", ("user_001", "admin"))
            conn.execute("INSERT INTO roles (id, code) VALUES (?, ?)", ("role_001", "ADMIN"))
            conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", ("user_001", "role_001"))
            conn.commit()

            user = {"id": "user_001", "username": "admin"}

            response = await WebSocketHandlers.project_create(
                data={"name": "Test Project", "description": "Test Description"},
                user=user,
                conn=conn,
                request_id="req_001",
                ip_address="127.0.0.1"
            )

            self.assertEqual(response.code, 0)
            self.assertEqual(response.message, "项目创建成功")
            self.assertIn("id", response.data)
            self.assertIn("project_no", response.data)
            self.assertEqual(response.data["name"], "Test Project")
            self.assertIn("PRJ-", response.data["project_no"])

            conn.close()

        asyncio.run(run_test())

    def test_project_create_without_permission(self):
        """测试 project.create 无权限"""
        import asyncio

        async def run_test():
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            init_test_tables(conn)

            # 创建一个没有 ADMIN 角色的用户
            user = {"id": "user_001", "username": "worker"}

            response = await WebSocketHandlers.project_create(
                data={"name": "Test Project"},
                user=user,
                conn=conn,
                request_id="req_001",
                ip_address="127.0.0.1"
            )

            self.assertEqual(response.code, 403)
            self.assertEqual(response.message, "无权限")

            conn.close()

        asyncio.run(run_test())


class TestMilestoneHandlers(unittest.TestCase):
    """测试里程碑接口处理器"""

    def test_milestone_create_response(self):
        """测试 milestone.create 响应"""
        import asyncio

        async def run_test():
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            init_test_tables(conn)

            user = {"id": "user_001", "username": "admin"}
            project_id = "proj_001"

            # 先创建项目
            conn.execute(
                "INSERT INTO projects (id, project_no, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, "PRJ-001", "Test Project", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )

            with patch('websocket.handlers.check_permission', return_value=True):
                response = await WebSocketHandlers.milestone_create(
                    data={
                        "project_id": project_id,
                        "name": "Test Milestone",
                        "description": "Test Description",
                        "type": "milestone"
                    },
                    user=user,
                    conn=conn,
                    request_id="req_001",
                    ip_address="127.0.0.1"
                )

            self.assertEqual(response.code, 0)
            self.assertEqual(response.message, "里程碑创建成功")
            self.assertIn("id", response.data)
            self.assertEqual(response.data["name"], "Test Milestone")

            conn.close()

        asyncio.run(run_test())


class TestMessageHandlers(unittest.TestCase):
    """测试消息接口处理器"""

    def test_message_unread_count_response(self):
        """测试 message.unread_count 响应"""
        import asyncio

        async def run_test():
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            init_test_tables(conn)

            user = {"id": "user_001", "username": "test"}

            response = await WebSocketHandlers.message_unread_count(
                data={},
                user=user,
                conn=conn,
                request_id="req_001",
                ip_address="127.0.0.1"
            )

            self.assertEqual(response.code, 0)
            self.assertIn("unread_count", response.data)
            self.assertEqual(response.data["unread_count"], 0)

            conn.close()

        asyncio.run(run_test())


def init_test_tables(conn):
    """初始化测试表"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT NOT NULL,
            role_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            project_no TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS milestones (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            type TEXT,
            name TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS milestone_logs (
            id TEXT PRIMARY KEY,
            milestone_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT,
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
    """)


if __name__ == "__main__":
    unittest.main()
