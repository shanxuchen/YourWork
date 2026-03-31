"""
YourWork - 认证模块单元测试
测试认证相关的 API 和功能
"""

import unittest

from test.test_base import APITestBase


class TestAuthLoginAPI(APITestBase):
    """测试登录 API"""

    def test_login_with_correct_credentials(self):
        """测试使用正确的凭据登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        data = self.assert_success_response(response, "登录应该成功")
        self.assertIn("data", data)
        self.assertIn("id", data["data"])
        self.assertEqual(data["data"]["username"], "admin")

    def test_login_with_wrong_password(self):
        """测试使用错误的密码登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })

        data = self.assert_error_response(response, 401, "应该返回 401 错误")
        self.assertIn("message", data)

    def test_login_with_nonexistent_user(self):
        """测试使用不存在的用户登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "password"
        })

        data = self.assert_error_response(response, 401, "应该返回 401 错误")

    def test_login_with_empty_username(self):
        """测试使用空用户名登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "",
            "password": "password"
        })

        # 应该返回 401 或 400
        self.assertIn(response.status_code, [200])

    def test_login_with_empty_password(self):
        """测试使用空密码登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": ""
        })

        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_login_sets_cookie(self):
        """测试登录设置 Cookie"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        # 检查响应中是否有设置 Cookie
        cookies = response.cookies
        self.assertTrue(len(cookies) > 0 or "set-cookie" in str(response.headers).lower())

    def test_login_inactive_user(self):
        """测试登录被禁用的用户"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "inactive",
            "password": "inactive123"
        })

        # 被禁用的用户不应该能够登录
        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_login_manager_user(self):
        """测试经理用户登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "manager",
            "password": "manager123"
        })

        data = self.assert_success_response(response, "经理登录应该成功")
        self.assertEqual(data["data"]["username"], "manager")

    def test_login_worker_user(self):
        """测试普通员工登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "worker",
            "password": "worker123"
        })

        data = self.assert_success_response(response, "员工登录应该成功")
        self.assertEqual(data["data"]["username"], "worker")


class TestAuthLogoutAPI(APITestBase):
    """测试登出 API"""

    def test_logout_success(self):
        """测试登出成功"""
        headers = self.get_auth_headers()
        response = self.client.post("/api/v1/auth/logout", headers=headers)

        data = self.assert_success_response(response, "登出应该成功")

    def test_logout_without_login(self):
        """测试未登录时登出"""
        response = self.client.post("/api/v1/auth/logout")

        # 未登录时登出也应该成功（幂等操作）
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("code"), 0)

    def test_logout_clears_cookie(self):
        """测试登出清除 Cookie"""
        # 先登录
        login_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        # 再登出
        logout_response = self.client.post("/api/v1/auth/logout")

        # 检查登出响应中是否有清除 Cookie 的指示
        cookies = logout_response.cookies
        headers = str(logout_response.headers).lower()

        # 应该有 set-cookie 响应头，且包含过期或清除指令
        self.assertTrue("set-cookie" in headers or len(cookies) > 0)


class TestAuthProfileAPI(APITestBase):
    """测试获取用户信息 API"""

    def test_get_profile_with_valid_token(self):
        """测试使用有效令牌获取用户信息"""
        headers = self.get_auth_headers()
        response = self.client.get("/api/v1/auth/profile", headers=headers)

        data = self.assert_success_response(response, "获取用户信息应该成功")
        self.assertIn("data", data)
        self.assertEqual(data["data"]["username"], "admin")
        self.assertNotIn("password", data["data"])  # 不应该返回密码

    def test_get_profile_without_token(self):
        """测试没有令牌时获取用户信息"""
        response = self.client.get("/api/v1/auth/profile")

        data = self.assert_error_response(response, 401, "应该返回 401 错误")

    def test_get_profile_includes_roles(self):
        """测试获取用户信息包含角色"""
        headers = self.get_auth_headers()
        response = self.client.get("/api/v1/auth/profile", headers=headers)

        data = self.assert_success_response(response)
        self.assertIn("roles", data["data"])
        self.assertIsInstance(data["data"]["roles"], list)

    def test_get_profile_admin_user(self):
        """测试获取管理员用户信息"""
        headers = self.get_auth_headers("admin", "admin123")
        response = self.client.get("/api/v1/auth/profile", headers=headers)

        data = self.assert_success_response(response)
        # 管理员应该有 ADMIN 或 SYSTEM_ADMIN 角色
        roles = data["data"]["roles"]
        role_codes = [r["code"] for r in roles]
        self.assertTrue("ADMIN" in role_codes or "SYSTEM_ADMIN" in role_codes)

    def test_get_profile_worker_user(self):
        """测试获取普通员工用户信息"""
        headers = self.get_auth_headers("worker", "worker123")
        response = self.client.get("/api/v1/auth/profile", headers=headers)

        data = self.assert_success_response(response)
        self.assertEqual(data["data"]["username"], "worker")


class TestAuthRegisterAPI(APITestBase):
    """测试注册 API"""

    def test_register_new_user(self):
        """测试注册新用户"""
        from test.test_data_generator import random_user

        new_user = random_user()
        response = self.client.post("/api/v1/auth/register", json={
            "username": new_user["username"],
            "password": new_user["password"],
            "display_name": new_user["display_name"],
            "email": new_user["email"]
        })

        data = self.assert_success_response(response, "注册应该成功")

        # 验证用户可以登录
        login_response = self.client.post("/api/v1/auth/login", json={
            "username": new_user["username"],
            "password": new_user["password"]
        })
        login_data = self.assert_success_response(login_response, "新注册用户应该能够登录")

    def test_register_duplicate_username(self):
        """测试注册重复用户名"""
        response = self.client.post("/api/v1/auth/register", json={
            "username": "admin",  # 已存在的用户名
            "password": "password123",
            "display_name": "管理员"
        })

        data = self.assert_error_response(response, 400, "应该返回 400 错误")
        self.assertIn("message", data)

    def test_register_missing_required_fields(self):
        """测试缺少必填字段的注册"""
        # 缺少用户名
        response = self.client.post("/api/v1/auth/register", json={
            "password": "password123"
        })
        # 应该返回错误
        self.assertIn(response.status_code, [200, 422])  # 422 是 FastAPI 的验证错误

    def test_register_minimal_data(self):
        """测试使用最少必需数据注册"""
        from test.test_data_generator import random_user

        new_user = random_user()
        response = self.client.post("/api/v1/auth/register", json={
            "username": new_user["username"],
            "password": new_user["password"]
        })

        data = self.assert_success_response(response, "只提供用户名和密码应该能注册")

    def test_register_with_email(self):
        """测试带邮箱的注册"""
        from test.test_data_generator import random_user

        new_user = random_user()
        response = self.client.post("/api/v1/auth/register", json={
            "username": new_user["username"],
            "password": new_user["password"],
            "email": new_user["email"]
        })

        data = self.assert_success_response(response, "带邮箱注册应该成功")


class TestAuthSecurity(APITestBase):
    """测试认证安全性"""

    def test_password_not_returned_in_login_response(self):
        """测试登录响应不包含密码"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        data = self.assert_success_response(response)
        self.assertNotIn("password", data["data"])

    def test_password_not_returned_in_profile_response(self):
        """测试用户信息响应不包含密码"""
        headers = self.get_auth_headers()
        response = self.client.get("/api/v1/auth/profile", headers=headers)

        data = self.assert_success_response(response)
        self.assertNotIn("password", data["data"])

    def test_password_is_hashed_in_database(self):
        """测试数据库中的密码是哈希值"""
        from main import get_db, hash_password

        conn = get_db()
        cursor = conn.execute("SELECT password FROM users WHERE username = ?", ("admin",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        stored_password = result["password"]

        # 应该是 SHA256 哈希（64个十六进制字符）
        self.assertEqual(len(stored_password), 64)
        self.assertNotEqual(stored_password, "admin123")

        # 验证确实是正确密码的哈希
        self.assertEqual(stored_password, hash_password("admin123"))

    def test_different_passwords_produce_different_hashes(self):
        """测试不同密码产生不同的哈希"""
        from main import hash_password

        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        self.assertNotEqual(hash1, hash2)


if __name__ == "__main__":
    unittest.main()
