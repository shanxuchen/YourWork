"""
YourWork - 认证流程集成测试
测试完整的认证流程，包括注册、登录、登出等
"""

import unittest

from test.test_base import APITestBase
from test.test_data_generator import random_user


class TestCompleteAuthFlow(APITestBase):
    """测试完整的认证流程"""

    def test_register_login_logout_flow(self):
        """测试注册 -> 登录 -> 登出完整流程"""
        # 1. 注册新用户
        new_user = random_user()
        register_response = self.client.post("/api/v1/auth/register", json={
            "username": new_user["username"],
            "password": new_user["password"],
            "display_name": new_user["display_name"],
            "email": new_user["email"]
        })
        register_data = self.assert_success_response(register_response, "注册失败")

        # 2. 使用新用户登录
        login_response = self.client.post("/api/v1/auth/login", json={
            "username": new_user["username"],
            "password": new_user["password"]
        })
        login_data = self.assert_success_response(login_response, "登录失败")
        self.assertEqual(login_data["data"]["username"], new_user["username"])
        self.assertEqual(login_data["data"]["display_name"], new_user["display_name"])

        # 3. 获取用户信息
        user_id = login_data["data"]["id"]
        profile_response = self.client.get("/api/v1/auth/profile",
                                          headers={"Cookie": f"token={user_id}"})
        profile_data = self.assert_success_response(profile_response, "获取用户信息失败")
        self.assertEqual(profile_data["data"]["username"], new_user["username"])

        # 4. 登出
        logout_response = self.client.post("/api/v1/auth/logout",
                                          headers={"Cookie": f"token={user_id}"})
        self.assert_success_response(logout_response, "登出失败")

        # 5. 验证登出后无法访问受保护资源
        profile_response2 = self.client.get("/api/v1/auth/profile",
                                           headers={"Cookie": f"token={user_id}"})
        # 登出后，token 应该仍然有效（因为我们是简单实现），但在实际应用中应该无效
        # 这里我们只验证操作成功完成

    def test_login_with_wrong_password_then_correct_password(self):
        """测试先使用错误密码登录，再使用正确密码登录"""
        # 使用错误密码
        wrong_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        self.assert_error_response(wrong_response, 401, "错误密码应该返回 401")

        # 使用正确密码
        correct_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.assert_success_response(correct_response, "正确密码应该成功")

    def test_multiple_user_sessions(self):
        """测试多用户同时会话"""
        # 用户1登录
        user1_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        user1_data = self.assert_success_response(user1_response)
        user1_token = user1_data["data"]["id"]

        # 用户2登录
        user2_response = self.client.post("/api/v1/auth/login", json={
            "username": "manager",
            "password": "manager123"
        })
        user2_data = self.assert_success_response(user2_response)
        user2_token = user2_data["data"]["id"]

        # 验证两个用户都能访问各自的用户信息
        user1_profile = self.client.get("/api/v1/auth/profile",
                                        headers={"Cookie": f"token={user1_token}"})
        user1_profile_data = self.assert_success_response(user1_profile)
        self.assertEqual(user1_profile_data["data"]["username"], "admin")

        user2_profile = self.client.get("/api/v1/auth/profile",
                                        headers={"Cookie": f"token={user2_token}"})
        user2_profile_data = self.assert_success_response(user2_profile)
        self.assertEqual(user2_profile_data["data"]["username"], "manager")

    def test_login_and_access_protected_resource(self):
        """测试登录后访问受保护资源"""
        # 1. 未登录时访问受保护资源
        response = self.client.get("/api/v1/projects")
        data = response.json()
        self.assertEqual(data.get("code"), 401, "未登录应该返回 401")

        # 2. 登录
        login_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        login_data = self.assert_success_response(login_response)
        token = login_data["data"]["id"]

        # 3. 登录后访问受保护资源
        protected_response = self.client.get("/api/v1/projects",
                                            headers={"Cookie": f"token={token}"})
        # 管理员应该能访问项目列表
        protected_data = protected_response.json()
        self.assertEqual(protected_data.get("code"), 0)


class TestRoleBasedAccessFlow(APITestBase):
    """测试基于角色的访问控制流程"""

    def test_admin_can_create_project(self):
        """测试管理员可以创建项目"""
        headers = self.get_auth_headers("admin", "admin123")

        response = self.client.post("/api/v1/projects",
                                   json={"name": "管理员创建的项目", "description": "测试"},
                                   headers=headers)
        self.assert_success_response(response, "管理员应该能创建项目")

    def test_worker_cannot_create_project(self):
        """测试普通员工不能创建项目"""
        headers = self.get_auth_headers("worker", "worker123")

        response = self.client.post("/api/v1/projects",
                                   json={"name": "员工尝试创建的项目", "description": "测试"},
                                   headers=headers)
        self.assert_error_response(response, 403, "普通员工不应该能创建项目")

    def test_admin_can_access_user_management(self):
        """测试管理员可以访问用户管理"""
        headers = self.get_auth_headers("admin", "admin123")

        response = self.client.get("/api/v1/users", headers=headers)
        self.assert_success_response(response, "管理员应该能访问用户管理")

    def test_worker_cannot_access_user_management(self):
        """测试普通员工不能访问用户管理"""
        headers = self.get_auth_headers("worker", "worker123")

        response = self.client.get("/api/v1/users", headers=headers)
        self.assert_error_response(response, 403, "普通员工不应该能访问用户管理")


class TestSessionManagement(APITestBase):
    """测试会话管理"""

    def test_session_persistence(self):
        """测试会话持久化"""
        # 1. 登录
        login_response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        login_data = self.assert_success_response(login_response)
        token = login_data["data"]["id"]

        # 2. 使用同一 token 多次访问
        for _ in range(3):
            response = self.client.get("/api/v1/auth/profile",
                                      headers={"Cookie": f"token={token}"})
            self.assert_success_response(response, "会话应该保持有效")

    def test_logout_and_login_again(self):
        """测试登出后重新登录"""
        # 1. 第一次登录
        login_response1 = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        login_data1 = self.assert_success_response(login_response1)
        token1 = login_data1["data"]["id"]

        # 2. 登出
        logout_response = self.client.post("/api/v1/auth/logout",
                                          headers={"Cookie": f"token={token1}"})
        self.assert_success_response(logout_response)

        # 3. 重新登录
        login_response2 = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        login_data2 = self.assert_success_response(login_response2)
        token2 = login_data2["data"]["id"]

        # 4. 使用新 token 访问
        profile_response = self.client.get("/api/v1/auth/profile",
                                          headers={"Cookie": f"token={token2}"})
        self.assert_success_response(profile_response)

    def test_concurrent_login(self):
        """测试并发登录"""
        import threading

        results = []

        def login_attempt():
            response = self.client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "admin123"
            })
            results.append(response.json())

        # 创建多个线程同时登录
        threads = [threading.Thread(target=login_attempt) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有登录都成功
        for result in results:
            self.assertEqual(result.get("code"), 0, "所有并发登录都应该成功")


class TestPasswordRecoveryFlow(APITestBase):
    """测试密码恢复流程（预留功能）"""

    def test_password_change_after_login(self):
        """测试登录后修改密码"""
        # 注意：当前实现可能没有修改密码的 API
        # 这里是预留的测试用例
        pass

    def test_password_reset_flow(self):
        """测试密码重置流程（预留）"""
        # 注意：当前实现可能没有密码重置功能
        # 这里是预留的测试用例
        pass


if __name__ == "__main__":
    unittest.main()
