"""
YourWork - 工具函数单元测试
测试通用工具函数的正确性
"""

import unittest
import hashlib
import uuid
from datetime import datetime

from main import generate_id, hash_password, verify_password
from test.test_base import TestBase


class TestGenerateId(TestBase):
    """测试 ID 生成函数"""

    def test_generate_id_returns_string(self):
        """测试 generate_id 返回字符串"""
        result = generate_id()
        self.assertIsInstance(result, str)

    def test_generate_id_returns_unique_values(self):
        """测试 generate_id 每次返回不同的值"""
        id1 = generate_id()
        id2 = generate_id()
        self.assertNotEqual(id1, id2)

    def test_generate_id_returns_valid_uuid_format(self):
        """测试 generate_id 返回有效的 UUID 格式"""
        result = generate_id()
        # UUID 格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        self.assertRegex(result, r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

    def test_generate_id_generates_many_unique_ids(self):
        """测试生成大量 ID 时的唯一性"""
        ids = set()
        for _ in range(1000):
            ids.add(generate_id())
        self.assertEqual(len(ids), 1000)


class TestHashPassword(TestBase):
    """测试密码哈希函数"""

    def test_hash_password_returns_string(self):
        """测试 hash_password 返回字符串"""
        result = hash_password("test_password")
        self.assertIsInstance(result, str)

    def test_hash_password_returns_fixed_length(self):
        """测试 hash_password 返回固定长度（SHA256 = 64 字符）"""
        result = hash_password("test_password")
        self.assertEqual(len(result), 64)

    def test_hash_password_same_input_same_output(self):
        """测试相同密码产生相同哈希值"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        self.assertEqual(hash1, hash2)

    def test_hash_password_different_input_different_output(self):
        """测试不同密码产生不同哈希值"""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        self.assertNotEqual(hash1, hash2)

    def test_hash_password_empty_string(self):
        """测试空字符串的哈希"""
        result = hash_password("")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_hash_password_special_characters(self):
        """测试包含特殊字符的密码"""
        password = "P@ssw0rd!#$%^&*()"
        result = hash_password(password)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_hash_password_unicode_characters(self):
        """测试包含 Unicode 字符的密码"""
        password = "密码123测试！@#"
        result = hash_password(password)
        self.assertIsInstance(result, str)

    def test_hash_password_matches_sha256(self):
        """测试哈希结果与标准 SHA256 一致"""
        password = "test_password"
        result = hash_password(password)
        expected = hashlib.sha256(password.encode()).hexdigest()
        self.assertEqual(result, expected)


class TestVerifyPassword(TestBase):
    """测试密码验证函数"""

    def test_verify_password_correct_password(self):
        """测试正确的密码验证"""
        password = "test_password"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))

    def test_verify_password_incorrect_password(self):
        """测试错误的密码验证"""
        password = "test_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        self.assertFalse(verify_password(wrong_password, hashed))

    def test_verify_password_empty_string(self):
        """测试空字符串验证"""
        password = ""
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("not_empty", hashed))

    def test_verify_password_case_sensitive(self):
        """测试密码大小写敏感"""
        password = "TestPassword"
        hashed = hash_password(password)
        self.assertFalse(verify_password("testpassword", hashed))
        self.assertFalse(verify_password("TESTPASSWORD", hashed))

    def test_verify_password_whitespace_sensitive(self):
        """测试密码空格敏感"""
        password = "test password"
        hashed = hash_password(password)
        self.assertFalse(verify_password("testpassword", hashed))
        self.assertFalse(verify_password("test  password", hashed))


class TestDatabaseHelpers(TestBase):
    """测试数据库辅助函数"""

    def test_get_db_returns_connection(self):
        """测试 get_db 返回有效的数据库连接"""
        from main import get_db
        conn = get_db()
        self.assertIsNotNone(conn)
        conn.close()

    def test_get_db_row_factory_set(self):
        """测试 get_db 返回的连接设置了 row_factory"""
        from main import get_db
        conn = get_db()
        # row_factory 设置后，fetchone 返回 Row 对象（支持字典访问）
        cursor = conn.execute("SELECT 1 as test_column")
        result = cursor.fetchone()
        # Row 对象支持字典式访问
        self.assertEqual(result["test_column"], 1)
        # 也支持索引访问
        self.assertEqual(result[0], 1)
        conn.close()

    def test_row_to_dict(self):
        """测试 row_to_dict 函数"""
        from main import get_db, row_to_dict
        conn = get_db()
        cursor = conn.execute("SELECT 1 as test_column")
        row = cursor.fetchone()
        result = row_to_dict(row)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["test_column"], 1)
        conn.close()

    def test_row_to_dict_with_none(self):
        """测试 row_to_dict 处理 None"""
        from main import row_to_dict
        result = row_to_dict(None)
        self.assertIsNone(result)

    def test_rows_to_list(self):
        """测试 rows_to_list 函数"""
        from main import get_db, rows_to_list
        conn = get_db()
        cursor = conn.execute("SELECT 1 as col UNION SELECT 2")
        rows = cursor.fetchall()
        result = rows_to_list(rows)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], dict)
        conn.close()


class TestLogFunctions(TestBase):
    """测试日志函数"""

    def test_log_api_request(self):
        """测试 log_api_request 函数"""
        from main import log_api_request
        # 不应该抛出异常
        log_api_request("GET", "/api/v1/test", None)
        log_api_request("POST", "/api/v1/test", {"username": "test"}, {"data": "test"})

    def test_log_response(self):
        """测试 log_response 函数"""
        from main import log_response
        # 不应该抛出异常
        log_response("GET", "/api/v1/test", 200)
        log_response("POST", "/api/v1/test", 400, "参数错误")

    def test_logging_configured(self):
        """测试日志系统已配置"""
        import logging
        logger = logging.getLogger()
        self.assertIsNotNone(logger)
        # 应该有处理器
        self.assertGreater(len(logger.handlers), 0)


class TestPermissionCheck(TestBase):
    """测试权限检查函数"""

    def test_check_permission_with_no_user(self):
        """测试没有用户时的权限检查"""
        from main import check_permission
        result = check_permission(None, ["ADMIN"])
        self.assertFalse(result)

    def test_check_permission_with_no_required_roles(self):
        """测试没有角色要求时的权限检查"""
        from main import check_permission, get_db
        # 需要一个已登录用户
        headers = self.get_auth_headers()
        user_id = headers["Cookie"].replace("token=", "")
        conn = get_db()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        conn.close()

        result = check_permission(user, None)
        self.assertTrue(result)

    def test_check_permission_admin_user(self):
        """测试管理员用户的权限检查"""
        from main import check_permission, get_db
        headers = self.get_auth_headers("admin", "admin123")
        user_id = headers["Cookie"].replace("token=", "")
        conn = get_db()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        conn.close()

        result = check_permission(user, ["ADMIN", "SYSTEM_ADMIN"])
        self.assertTrue(result)


class TestDateTimeUtils(TestBase):
    """测试日期时间工具函数"""

    def test_datetime_now_format(self):
        """测试 datetime.now() 返回有效日期时间"""
        now = datetime.now()
        self.assertIsInstance(now, datetime)

    def test_datetime_isoformat(self):
        """测试 ISO 格式化"""
        now = datetime.now()
        iso_str = now.isoformat()
        self.assertIsInstance(iso_str, str)
        # ISO 格式应该包含 T
        self.assertIn("T", iso_str)

    def test_datetime_from_isoformat(self):
        """测试从 ISO 格式解析"""
        iso_str = "2024-01-01T12:00:00"
        parsed = datetime.fromisoformat(iso_str)
        self.assertEqual(parsed.year, 2024)
        self.assertEqual(parsed.month, 1)
        self.assertEqual(parsed.day, 1)


if __name__ == "__main__":
    unittest.main()
