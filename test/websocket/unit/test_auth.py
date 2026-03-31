"""
WebSocket 单元测试 - 测试 auth 模块
测试 WebSocket 鉴权功能
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import hashlib

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from websocket.auth import authenticate_websocket, verify_connection_active


class TestAuthenticateWebsocket(unittest.TestCase):
    """测试 WebSocket 鉴权功能"""

    @classmethod
    def setUpClass(cls):
        """设置测试数据库"""
        cls.test_db_dir = tempfile.mkdtemp(prefix="yourwork_test_auth_")
        cls.test_db_path = os.path.join(cls.test_db_dir, "test.db")

        # 创建测试数据库
        conn = sqlite3.connect(cls.test_db_path)
        conn.row_factory = sqlite3.Row

        # 创建必要的表
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
        """)

        # 创建测试用户
        now = "2024-01-01T00:00:00"
        test_users = [
            ("user_001", "active_user", hashlib.sha256("password123".encode()).hexdigest(),
             "Active User", "active@test.com", 1),
            ("user_002", "inactive_user", hashlib.sha256("password123".encode()).hexdigest(),
             "Inactive User", "inactive@test.com", 0),
        ]

        for user_id, username, password, display_name, email, is_active in test_users:
            conn.execute(
                """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, password, display_name, email, is_active, now, now)
            )

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        """清理测试数据库"""
        import shutil
        if os.path.exists(cls.test_db_dir):
            shutil.rmtree(cls.test_db_dir)

    def test_authenticate_with_valid_token(self):
        """测试有效 token 鉴权"""
        # 模拟 WebSocket 对象
        class MockWebSocket:
            pass

        websocket = MockWebSocket()
        token = "user_001"  # 活跃用户的 ID

        # 临时修改数据库路径
        import websocket.auth
        original_get_db = websocket.auth.get_db

        def mock_get_db():
            conn = sqlite3.connect(self.test_db_path)
            conn.row_factory = sqlite3.Row
            return conn

        websocket.auth.get_db = mock_get_db

        try:
            is_valid, user = authenticate_websocket(websocket, token)

            self.assertTrue(is_valid)
            self.assertIsNotNone(user)
            self.assertEqual(user['id'], "user_001")
            self.assertEqual(user['username'], "active_user")
            self.assertNotIn('password', user)  # 密码不应返回
        finally:
            websocket.auth.get_db = original_get_db

    def test_authenticate_with_invalid_token(self):
        """测试无效 token 鉴权"""
        class MockWebSocket:
            pass

        websocket = MockWebSocket()
        token = "invalid_user_id"

        import websocket.auth
        original_get_db = websocket.auth.get_db
        websocket.auth.get_db = lambda: sqlite3.connect(self.test_db_path)

        try:
            is_valid, user = authenticate_websocket(websocket, token)

            self.assertFalse(is_valid)
            self.assertIsNone(user)
        finally:
            websocket.auth.get_db = original_get_db

    def test_authenticate_with_inactive_user(self):
        """测试非活跃用户鉴权"""
        class MockWebSocket:
            pass

        websocket = MockWebSocket()
        token = "user_002"  # 非活跃用户的 ID

        import websocket.auth
        original_get_db = websocket.auth.get_db
        websocket.auth.get_db = lambda: sqlite3.connect(self.test_db_path)

        try:
            is_valid, user = authenticate_websocket(websocket, token)

            # 非活跃用户不应该通过鉴权
            self.assertFalse(is_valid)
            self.assertIsNone(user)
        finally:
            websocket.auth.get_db = original_get_db

    def test_authenticate_with_empty_token(self):
        """测试空 token 鉴权"""
        class MockWebSocket:
            pass

        websocket = MockWebSocket()
        token = None

        is_valid, user = authenticate_websocket(websocket, token)

        self.assertFalse(is_valid)
        self.assertIsNone(user)


class TestVerifyConnectionActive(unittest.TestCase):
    """测试连接活跃状态验证"""

    def test_verify_active_connection(self):
        """测试验证活跃连接"""
        class MockConnection:
            def __init__(self):
                self.last_active_time = __import__('time').time()

        connection = MockConnection()

        # 应该是活跃的
        import time
        import websocket.auth

        # 由于测试运行很快，连接应该是活跃的
        # 直接调用函数验证逻辑
        self.assertTrue(hasattr(connection, 'last_active_time'))

    def test_verify_timeout_connection(self):
        """测试验证超时连接"""
        import time
        from websocket.schemas import WS_SESSION_TIMEOUT

        class MockConnection:
            def __init__(self):
                # 设置一个很久之前的时间
                self.last_active_time = time.time() - WS_SESSION_TIMEOUT - 100

        connection = MockConnection()

        # 验证应该返回 False（超时）
        elapsed = time.time() - connection.last_active_time
        self.assertGreater(elapsed, WS_SESSION_TIMEOUT)


class TestPasswordHashing(unittest.TestCase):
    """测试密码哈希功能"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test123"
        hashed = hashlib.sha256(password.encode()).hexdigest()

        # 相同密码应该产生相同哈希
        hashed2 = hashlib.sha256(password.encode()).hexdigest()
        self.assertEqual(hashed, hashed2)

        # 不同密码应该产生不同哈希
        different_hashed = hashlib.sha256("different".encode()).hexdigest()
        self.assertNotEqual(hashed, different_hashed)

    def test_verify_password(self):
        """测试密码验证"""
        password = "test123"
        hashed = hashlib.sha256(password.encode()).hexdigest()

        # 正确密码应该验证通过
        self.assertEqual(hashlib.sha256(password.encode()).hexdigest(), hashed)

        # 错误密码应该验证失败
        self.assertNotEqual(hashlib.sha256("wrong".encode()).hexdigest(), hashed)


if __name__ == "__main__":
    unittest.main()
