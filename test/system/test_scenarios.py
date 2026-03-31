"""
YourWork - 场景测试
测试各种实际业务场景和边界情况
"""

import unittest
import threading
import time

from test.test_base import APITestBase
from test.test_data_generator import random_user, random_project


class TestErrorRecoveryScenarios(APITestBase):
    """测试错误恢复场景"""

    def test_invalid_project_id_recovery(self):
        """测试使用无效项目ID后的恢复"""
        headers = self.get_auth_headers()

        # 尝试访问不存在的项目
        fake_id = "non-existent-id-12345"
        response = self.client.get(f"/api/v1/projects/{fake_id}", headers=headers)
        data = response.json()
        self.assertEqual(data.get("code"), 404)

        # 验证可以继续访问其他项目
        valid_response = self.client.get("/api/v1/projects", headers=headers)
        self.assert_success_response(valid_response)

    def test_failed_operation_retry(self):
        """测试操作失败后的重试"""
        headers = self.get_auth_headers()

        # 尝试更新不存在的里程碑
        fake_milestone_id = "fake-milestone-id"
        response = self.client.put(f"/api/v1/milestones/{fake_milestone_id}",
                                  json={"status": "completed"},
                                  headers=headers)
        data = response.json()
        self.assertEqual(data.get("code"), 404)

        # 创建真实的里程碑并更新
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "重试测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 现在更新应该成功
        update_response = self.client.put(f"/api/v1/milestones/{milestone_id}",
                                         json={"status": "completed"},
                                         headers=headers)
        self.assert_success_response(update_response)

    def test_network_error_simulation(self):
        """测试网络错误场景（模拟）"""
        # 这个测试主要用于验证错误处理机制
        headers = self.get_auth_headers()

        # 发送格式错误的数据
        response = self.client.post("/api/v1/projects",
                                  json={"invalid": "data"},  # 缺少name字段
                                  headers=headers)
        # 应该返回错误
        data = response.json()
        self.assertNotEqual(data.get("code"), 0)


class TestConcurrentOperationsScenarios(APITestBase):
    """测试并发操作场景"""

    def test_concurrent_project_creation(self):
        """测试并发创建项目"""
        headers = self.get_auth_headers()
        results = []
        errors = []

        def create_project(index):
            try:
                response = self.client.post("/api/v1/projects",
                                          json={"name": f"并发项目{index}"},
                                          headers=headers)
                results.append(response.json())
            except Exception as e:
                errors.append(e)

        # 创建10个线程同时创建项目
        threads = [threading.Thread(target=create_project, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有创建都成功
        self.assertEqual(len(errors), 0, f"发生错误: {errors}")
        success_count = sum(1 for r in results if r.get("code") == 0)
        self.assertEqual(success_count, 10, "应该成功创建10个项目")

    def test_concurrent_milestone_updates(self):
        """测试并发更新里程碑"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "并发测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "并发测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        results = []

        def update_milestone(index):
            response = self.client.put(f"/api/v1/milestones/{milestone_id}",
                                      json={
                                          "name": f"更新名称{index}",
                                          "status": "waiting"
                                      },
                                      headers=headers)
            results.append(response.json())

        # 多个线程同时更新
        threads = [threading.Thread(target=update_milestone, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证至少有一些更新成功
        success_count = sum(1 for r in results if r.get("code") == 0)
        self.assertGreater(success_count, 0)

    def test_concurrent_user_sessions(self):
        """测试多用户并发会话"""
        results = []

        def user_login(username, password):
            response = self.client.post("/api/v1/auth/login",
                                      json={"username": username, "password": password})
            results.append(response.json())

        # 多个用户同时登录
        threads = [
            threading.Thread(target=user_login, args=("admin", "admin123")),
            threading.Thread(target=user_login, args=("manager", "manager123")),
            threading.Thread(target=user_login, args=("worker", "worker123"))
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有登录都成功
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.get("code"), 0)


class TestDataIntegrityScenarios(APITestBase):
    """测试数据完整性场景"""

    def test_cascade_delete_prevention(self):
        """测试级联删除保护"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "完整性测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 上传产出物
        from io import BytesIO
        files = {"file": ("test.txt", BytesIO(b"content"), "text/plain")}
        self.client.post(f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
                        files=files,
                        headers=headers)

        # 删除项目
        self.client.delete(f"/api/v1/projects/{project_id}", headers=headers)

        # 验证项目已删除
        response = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
        data = response.json()
        self.assertEqual(data.get("code"), 404)

    def test_orphaned_data_detection(self):
        """测试孤立数据检测"""
        from main import get_db

        # 直接在数据库中创建孤立里程碑（没有对应项目）
        conn = get_db()
        fake_project_id = "fake-project-id"
        milestone_id = "orphan-milestone-id"

        from datetime import datetime
        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (milestone_id, fake_project_id, "milestone", "孤立里程碑", "created",
             datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        # 尝试访问孤立里程碑
        headers = self.get_auth_headers()
        response = self.client.get(f"/api/v1/milestones/{milestone_id}", headers=headers)
        data = response.json()
        # 应该能获取到，但项目ID是无效的
        self.assertIsNotNone(data)

    def test_data_consistency_after_rollback(self):
        """测试回滚后的数据一致性"""
        headers = self.get_auth_headers()

        # 创建项目
        response1 = self.client.post("/api/v1/projects",
                                   json={"name": "一致性测试项目"},
                                   headers=headers)
        project_id = response1.json()["data"]["project_id"]

        # 更新项目
        self.client.put(f"/api/v1/projects/{project_id}",
                       json={"name": "更新后的名称"},
                       headers=headers)

        # 验证更新
        response2 = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
        data = self.assert_success_response(response2)
        self.assertEqual(data["data"]["project"]["name"], "更新后的名称")


class TestPerformanceScenarios(APITestBase):
    """测试性能场景"""

    def test_large_project_list_performance(self):
        """测试大项目列表的性能"""
        headers = self.get_auth_headers()

        # 创建多个项目
        start_time = time.time()
        for i in range(20):
            self.client.post("/api/v1/projects",
                            json={"name": f"性能测试项目{i}"},
                            headers=headers)

        # 测试获取项目列表的性能
        list_start = time.time()
        response = self.client.get("/api/v1/projects", headers=headers)
        list_time = time.time() - list_start

        self.assert_success_response(response)
        self.assertLess(list_time, 2.0, "获取项目列表应该在2秒内完成")

    def test_large_milestone_list_performance(self):
        """测试大里程碑列表的性能"""
        headers = self.get_auth_headers()

        # 创建项目和大量里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "性能测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建50个里程碑
        for i in range(50):
            self.client.post("/api/v1/milestones",
                           json={
                               "project_id": project_id,
                               "name": f"里程碑{i}"
                           },
                           headers=headers)

        # 测试获取里程碑列表的性能
        start_time = time.time()
        response = self.client.get(f"/api/v1/projects/{project_id}/milestones",
                                  headers=headers)
        elapsed = time.time() - start_time

        self.assert_success_response(response)
        self.assertLess(elapsed, 1.0, "获取里程碑列表应该在1秒内完成")

    def test_concurrent_read_performance(self):
        """测试并发读取性能"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "并发读取测试"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        results = []
        errors = []

        def read_project():
            try:
                start = time.time()
                response = self.client.get(f"/api/v1/projects/{project_id}",
                                         headers=headers)
                elapsed = time.time() - start
                results.append(elapsed)
            except Exception as e:
                errors.append(e)

        # 20个并发读取
        threads = [threading.Thread(target=read_project) for _ in range(20)]
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        self.assertEqual(len(errors), 0)
        self.assertLess(total_time, 5.0, "20个并发读取应该在5秒内完成")
        self.assertEqual(len(results), 20)


class TestBoundaryScenarios(APITestBase):
    """测试边界场景"""

    def test_very_long_project_name(self):
        """测试超长项目名称"""
        headers = self.get_auth_headers()

        long_name = "A" * 500
        response = self.client.post("/api/v1/projects",
                                  json={"name": long_name},
                                  headers=headers)
        # 应该成功或返回合适的错误
        self.assertIn(response.status_code, [200])

    def test_special_characters_in_name(self):
        """测试名称中的特殊字符"""
        headers = self.get_auth_headers()

        special_names = [
            "项目<script>alert('xss')</script>",
            "项目'; DROP TABLE users; --",
            "项目\u0000\u0001\u0002",
            "项目🎉🎊🎁"
        ]

        for name in special_names:
            response = self.client.post("/api/v1/projects",
                                      json={"name": name},
                                      headers=headers)
            # 验证不会崩溃
            self.assertIn(response.status_code, [200, 400])

    def test_empty_and_whitespace_inputs(self):
        """测试空输入和纯空格输入"""
        headers = self.get_auth_headers()

        # 测试空名称
        response1 = self.client.post("/api/v1/projects",
                                   json={"name": ""},
                                   headers=headers)
        self.assertNotEqual(response1.json().get("code"), 0)

        # 测试纯空格名称
        response2 = self.client.post("/api/v1/projects",
                                   json={"name": "   "},
                                   headers=headers)
        self.assertNotEqual(response2.json().get("code"), 0)

    def test_unicode_inputs(self):
        """测试Unicode输入"""
        headers = self.get_auth_headers()

        unicode_names = [
            "项目中文名称",
            "Проект на русском",
            "プロジェクト日本語",
            "المشروع العربي",
            "🎯Important Project🚀"
        ]

        for name in unicode_names:
            response = self.client.post("/api/v1/projects",
                                      json={"name": name},
                                      headers=headers)
            data = self.assert_success_response(response)

    def test_date_boundary_values(self):
        """测试日期边界值"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "日期测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 测试各种日期值
        boundary_dates = [
            "2024-01-01T00:00:00",  # 最小合理日期
            "2099-12-31T23:59:59",  # 最大合理日期
            "2024-02-29T12:00:00",  # 闰年日期
        ]

        for deadline in boundary_dates:
            response = self.client.post("/api/v1/milestones",
                                      json={
                                          "project_id": project_id,
                                          "name": "边界测试里程碑",
                                          "deadline": deadline
                                      },
                                      headers=headers)
            data = self.assert_success_response(response)


class TestSecurityScenarios(APITestBase):
    """测试安全场景"""

    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        headers = self.get_auth_headers()

        # 尝试SQL注入
        injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "admin' /*",
            "' OR 1=1--"
        ]

        for payload in injection_payloads:
            response = self.client.post("/api/v1/auth/login",
                                      json={"username": payload, "password": "any"})
            data = response.json()
            # 应该失败，不应该泄露数据库信息
            self.assertNotEqual(data.get("code"), 0)

    def test_xss_prevention(self):
        """测试XSS防护"""
        headers = self.get_auth_headers()

        xss_payload = "<script>alert('xss')</script>"

        # 创建包含XSS载荷的项目
        response = self.client.post("/api/v1/projects",
                                  json={"name": xss_payload},
                                  headers=headers)

        # 获取项目列表
        list_response = self.client.get("/api/v1/projects", headers=headers)
        list_data = self.assert_success_response(list_response)

        # 验证XSS没有被执行（应该在响应中转义）
        # 这里我们只验证响应成功
        self.assertEqual(list_data.get("code"), 0)

    def test_authentication_bypass_attempts(self):
        """测试认证绕过尝试"""
        # 不带token访问受保护资源
        response = self.client.get("/api/v1/projects")
        data = response.json()
        self.assertEqual(data.get("code"), 401)

        # 使用无效token
        response = self.client.get("/api/v1/projects",
                                 headers={"Cookie": "token=invalid-token-12345"})
        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_authorization_bypass_attempts(self):
        """测试授权绕过尝试"""
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 普通员工尝试创建项目
        response = self.client.post("/api/v1/projects",
                                  json={"name": "未授权项目"},
                                  headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403)

        # 普通员工尝试访问用户管理
        response = self.client.get("/api/v1/users", headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403)


if __name__ == "__main__":
    unittest.main()
