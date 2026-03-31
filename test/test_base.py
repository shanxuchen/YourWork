"""
YourWork - 测试基础设施
提供测试基类和通用测试工具
"""

import os
import sys
import unittest
import tempfile
import shutil

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, get_db, generate_id, hash_password, DB_PATH
from fastapi.testclient import TestClient


class TestBase(unittest.TestCase):
    """测试基类，提供通用的测试功能和设置"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化（整个测试类只执行一次）"""
        # 创建测试客户端
        cls.client = TestClient(app)

        # 设置测试数据库路径
        cls.test_db_dir = tempfile.mkdtemp(prefix="yourwork_test_")
        cls.test_db_path = os.path.join(cls.test_db_dir, "test.db")

        # 保存原始数据库路径
        cls.original_db_path = DB_PATH

        # 初始化测试数据库
        cls.setup_test_database()

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 恢复原始数据库路径
        import main
        main.DB_PATH = cls.original_db_path

        # 删除测试数据库目录
        if os.path.exists(cls.test_db_dir):
            shutil.rmtree(cls.test_db_dir)

    def setUp(self):
        """每个测试方法前的设置"""
        # 清理测试数据
        self.clean_test_data()

    @classmethod
    def setup_test_database(cls):
        """设置测试数据库"""
        import main

        # 临时修改数据库路径
        main.DB_PATH = cls.test_db_path

        # 初始化数据库，传递测试数据库路径
        from init_db import init_database
        init_database(cls.test_db_path)

        # 创建测试数据
        cls.create_test_users()
        cls.create_test_roles()

    @classmethod
    def create_test_roles(cls):
        """创建测试角色"""
        conn = get_db()

        # 确保角色存在
        roles = [
            ("SYSTEM_ADMIN", "系统管理员", "拥有所有权限"),
            ("ADMIN", "管理员", "管理项目和用户"),
            ("PROJECT_MANAGER", "项目经理", "管理项目"),
            ("WORKER", "工作人员", "普通工作人员")
        ]

        for code, name, desc in roles:
            conn.execute(
                "INSERT OR IGNORE INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
                (generate_id(), name, code, desc, 1)
            )

        conn.commit()
        conn.close()

    @classmethod
    def create_test_users(cls):
        """创建测试用户"""
        conn = get_db()
        now = "2024-01-01T00:00:00"

        # 创建测试用户
        test_users = [
            {
                "id": generate_id(),
                "username": "admin",
                "password": hash_password("admin123"),
                "display_name": "系统管理员",
                "email": "admin@test.com",
                "is_active": 1,
                "role": "SYSTEM_ADMIN"
            },
            {
                "id": generate_id(),
                "username": "manager",
                "password": hash_password("manager123"),
                "display_name": "项目经理",
                "email": "manager@test.com",
                "is_active": 1,
                "role": "ADMIN"
            },
            {
                "id": generate_id(),
                "username": "worker",
                "password": hash_password("worker123"),
                "display_name": "普通员工",
                "email": "worker@test.com",
                "is_active": 1,
                "role": "WORKER"
            },
            {
                "id": generate_id(),
                "username": "inactive",
                "password": hash_password("inactive123"),
                "display_name": "禁用用户",
                "email": "inactive@test.com",
                "is_active": 0,
                "role": "WORKER"
            }
        ]

        for user_data in test_users:
            role = user_data.pop("role")
            user_id = user_data["id"]

            # 检查用户是否已存在
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (user_data["username"],))
            if cursor.fetchone():
                continue  # 用户已存在，跳过

            conn.execute(
                """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_data["id"], user_data["username"], user_data["password"],
                 user_data["display_name"], user_data["email"], user_data["is_active"],
                 now, now)
            )

            # 分配角色
            cursor = conn.execute("SELECT id FROM roles WHERE code = ?", (role,))
            role_row = cursor.fetchone()
            if role_row:
                conn.execute(
                    "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                    (generate_id(), user_id, role_row['id'])
                )

        conn.commit()
        conn.close()

    def clean_test_data(self):
        """清理测试数据（保留用户、角色和会话）"""
        conn = get_db()

        # 删除测试期间创建的项目、里程碑等数据
        conn.execute("DELETE FROM milestone_items")
        conn.execute("DELETE FROM milestone_dependencies")
        conn.execute("DELETE FROM deliverables")
        conn.execute("DELETE FROM milestone_logs")
        conn.execute("DELETE FROM milestones")
        conn.execute("DELETE FROM project_members")
        conn.execute("DELETE FROM projects")
        conn.execute("DELETE FROM messages")
        # 不删除sessions，让每个测试方法自己管理会话

        conn.commit()
        conn.close()

    def login_user(self, username="admin", password="admin123"):
        """登录用户并返回用户信息"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })

        if response.status_code != 200:
            raise AssertionError(f"登录失败: {response.text}")

        data = response.json()
        if data.get("code") != 0:
            raise AssertionError(f"登录失败: {data.get('message')}")

        return data["data"]

    def get_auth_cookies(self, username="admin", password="admin123"):
        """获取认证cookies（用于TestClient）"""
        user_data = self.login_user(username, password)
        session_token = user_data["session_token"]
        # TestClient中cookies通过cookies参数传递
        return {"token": session_token}

    def get_auth_headers(self, username="admin", password="admin123"):
        """获取认证头（通过Cookie头传递）"""
        user_data = self.login_user(username, password)
        session_token = user_data["session_token"]
        return {"cookie": f"token={session_token}"}

    def get_user_id(self, username):
        """根据用户名获取用户ID"""
        conn = get_db()
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row['id'] if row else None

    def assert_success_response(self, response, message=""):
        """断言响应成功"""
        self.assertEqual(response.status_code, 200, f"{message} 状态码应为200")
        data = response.json()
        self.assertEqual(data.get("code"), 0, f"{message} {data.get('message')}")
        return data

    def assert_error_response(self, response, expected_code, message=""):
        """断言响应失败"""
        self.assertEqual(response.status_code, 200, f"{message} 状态码应为200")
        data = response.json()
        self.assertEqual(data.get("code"), expected_code, f"{message} 错误码不匹配")
        return data

    def create_test_project(self, name="测试项目", description="测试描述", headers=None):
        """创建测试项目的辅助方法"""
        if headers is None:
            headers = self.get_auth_headers()

        response = self.client.post("/api/v1/projects",
                                   json={"name": name, "description": description},
                                   headers=headers)
        data = self.assert_success_response(response, "创建项目失败")
        return data["data"]["project_id"]

    def create_test_milestone(self, project_id, name="测试里程碑", **kwargs):
        """创建测试里程碑的辅助方法"""
        headers = kwargs.pop("headers", None) or self.get_auth_headers()

        milestone_data = {
            "project_id": project_id,
            "name": name,
            "description": kwargs.get("description", "测试里程碑描述"),
            "type": kwargs.get("type", "milestone"),
            "deadline": kwargs.get("deadline", "2024-12-31T23:59:59")
        }

        response = self.client.post("/api/v1/milestones",
                                   json=milestone_data,
                                   headers=headers)
        data = self.assert_success_response(response, "创建里程碑失败")
        return data["data"]["milestone_id"]


class APITestBase(TestBase):
    """API 测试基类"""

    def test_health_check(self):
        """健康检查"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class DatabaseTestBase(TestBase):
    """数据库测试基类"""

    def get_test_conn(self):
        """获取测试数据库连接"""
        return get_db()

    def assert_row_exists(self, table, conditions):
        """断言行存在"""
        conn = self.get_test_conn()
        where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()])
        values = list(conditions.values())

        cursor = conn.execute(f"SELECT * FROM {table} WHERE {where_clause}", values)
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, f"{table} 中不存在符合条件的行")
        return row

    def assert_row_count(self, table, expected_count, conditions=None):
        """断言行数"""
        conn = self.get_test_conn()
        if conditions:
            where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()])
            values = list(conditions.values())
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table} WHERE {where_clause}", values)
        else:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")

        count = cursor.fetchone()['count']
        conn.close()

        self.assertEqual(count, expected_count, f"{table} 行数不匹配，期望 {expected_count}，实际 {count}")


def run_test_suite(test_class, verbose=True):
    """运行测试套件"""
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    return runner.run(suite)
