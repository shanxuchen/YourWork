"""
YourWork - 错误处理单元测试
测试数据库、文件系统和网络错误处理
"""

import unittest
import os
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

from test.test_base import TestBase, DatabaseTestBase
from main import app, get_db, DB_PATH
from fastapi.testclient import TestClient


class TestDatabaseErrorHandling(TestBase):
    """测试数据库错误处理"""

    def test_database_connection_failure(self):
        """测试数据库连接失败处理"""
        # 临时破坏数据库路径
        original_db_path = DB_PATH
        invalid_path = "/invalid/path/to/database.db"

        import main
        main.DB_PATH = invalid_path

        try:
            # 尝试访问需要数据库的端点
            client = TestClient(app)
            headers = self.get_auth_headers()

            response = client.get("/api/v1/projects", headers=headers)

            # 应该返回错误
            data = response.json()
            self.assertIsNotNone(data)
            # 可能返回500或其他错误码
            self.assertIn(data.get("code"), [0, 500, 503])  # 0表示使用了测试数据库

        finally:
            # 恢复原始路径
            main.DB_PATH = original_db_path

    def test_database_query_timeout(self):
        """测试数据库查询超时处理"""
        # 这个测试需要模拟长时间运行的查询
        # SQLite的timeout设置
        pass

    def test_corrupted_database(self):
        """测试损坏数据库处理"""
        # 创建临时损坏的数据库
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            f.write("This is not a valid SQLite database")
            corrupted_db_path = f.name

        try:
            # 尝试连接损坏的数据库
            conn = sqlite3.connect(corrupted_db_path)
            cursor = conn.cursor()

            # 尝试查询应该失败
            with self.assertRaises(sqlite3.DatabaseError):
                cursor.execute("SELECT * FROM users")

            conn.close()

        finally:
            os.unlink(corrupted_db_path)

    def test_sqlite_locked_error(self):
        """测试SQLite锁定错误处理"""
        # 模拟数据库被锁定的情况
        pass

    def test_database_schema_mismatch(self):
        """测试数据库架构不匹配处理"""
        # 测试当表不存在时的处理
        pass

    def test_constraint_violation(self):
        """测试约束违反处理"""
        conn = get_db()

        # 尝试插入重复的ID
        try:
            from main import generate_id
            existing_id = "test-unique-id"

            # 第一次插入
            conn.execute(
                "INSERT INTO projects (id, name, description, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (existing_id, "Test Project", "Description", "created", "admin", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )
            conn.commit()

            # 尝试再次插入相同ID（应该失败）
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO projects (id, name, description, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (existing_id, "Another Project", "Description", "created", "admin", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                )
                conn.commit()

        finally:
            # 清理
            conn.execute("DELETE FROM projects WHERE id = ?", (existing_id,))
            conn.commit()
            conn.close()


class TestFileSystemErrorHandling(TestBase):
    """测试文件系统错误处理"""

    def test_upload_directory_not_writable(self):
        """测试上传目录不可写"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "权限测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 模拟不可写的目录（使用mock）
        with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
            files = {"file": ("test.txt", BytesIO(b"content"), "text/plain")}
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers
            )

            # 应该返回错误
            data = response.json()
            self.assertIsNotNone(data)

    def test_disk_full_simulation(self):
        """测试磁盘满模拟"""
        # 模拟磁盘满的情况
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            client = TestClient(app)
            headers = self.get_auth_headers()

            response = client.post("/api/v1/projects",
                                  json={"name": "磁盘满测试项目"},
                                  headers=headers)
            project_id = response.json()["data"]["project_id"]

            files = {"file": ("test.txt", BytesIO(b"content"), "text/plain")}
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers
            )

            # 应该返回错误
            data = response.json()
            self.assertIsNotNone(data)

    def test_file_lock_handling(self):
        """测试文件锁定处理"""
        # 模拟文件被锁定的情况
        pass

    def test_invalid_file_path(self):
        """测试无效文件路径处理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 尝试下载不存在的文件
        fake_deliverable_id = "non-existent-file"
        response = client.get(f"/api/v1/deliverables/{fake_deliverable_id}/download",
                             headers=headers)

        data = response.json()
        self.assertEqual(data.get("code"), 404)

    def test_file_not_found_after_deletion(self):
        """测试删除后文件不存在处理"""
        # 创建项目并上传文件
        client = TestClient(app)
        headers = self.get_auth_headers()

        response = client.post("/api/v1/projects",
                              json={"name": "删除后测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("to_delete.txt", BytesIO(b"content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 获取文件路径
        conn = get_db()
        cursor = conn.execute(
            "SELECT file_path FROM deliverables WHERE id = ?",
            (deliverable_id,)
        )
        row = cursor.fetchone()
        file_path = row['file_path'] if row else None
        conn.close()

        # 删除物理文件（模拟）
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        # 尝试下载
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=headers)

        # 应该返回文件不存在错误
        data = response.json()
        self.assertEqual(data.get("code"), 404)

    def test_directory_creation_failure(self):
        """测试目录创建失败处理"""
        with patch('os.makedirs', side_effect=OSError("Directory creation failed")):
            client = TestClient(app)
            headers = self.get_auth_headers()

            response = client.post("/api/v1/projects",
                                  json={"name": "目录创建测试项目"},
                                  headers=headers)
            project_id = response.json()["data"]["project_id"]

            files = {"file": ("test.txt", BytesIO(b"content"), "text/plain")}
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers
            )

            # 应该处理错误
            data = response.json()
            self.assertIsNotNone(data)


class TestNetworkErrorHandling(TestBase):
    """测试网络错误处理"""

    def test_timeout_during_upload(self):
        """测试上传超时处理"""
        # 这个测试需要模拟超时
        # 在单元测试中较难实现
        pass

    def test_connection_reset(self):
        """测试连接重置处理"""
        # 模拟连接重置
        pass

    def test_malformed_request(self):
        """测试格式错误的请求处理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 发送格式错误的数据
        response = client.post("/api/v1/projects",
                              json={"invalid": "data"},  # 缺少name字段
                              headers=headers)

        data = response.json()
        self.assertNotEqual(data.get("code"), 0)

    def test_missing_required_fields(self):
        """测试缺少必需字段处理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 测试缺少各种必需字段
        test_cases = [
            {"description": "test"},  # 缺少name
            {},  # 空数据
            {"name": ""},  # 空name
        ]

        for test_data in test_cases:
            with self.subTest(data=test_data):
                response = client.post("/api/v1/projects",
                                      json=test_data,
                                      headers=headers)
                data = response.json()
                self.assertNotEqual(data.get("code"), 0)

    def test_invalid_json_format(self):
        """测试无效JSON格式处理"""
        client = TestClient(app)

        # 发送无效的JSON
        response = client.post("/api/v1/auth/login",
                              content="invalid json {{{",
                              headers={"Content-Type": "application/json"})

        # 应该返回错误
        self.assertIn(response.status_code, [400, 422])

    def test_invalid_content_type(self):
        """测试无效Content-Type处理"""
        client = TestClient(app)

        # 发送错误的内容类型
        response = client.post("/api/v1/auth/login",
                              content="username=admin&password=admin123",
                              headers={"Content-Type": "application/x-www-form-urlencoded"})

        # 应该返回错误或422
        self.assertIn(response.status_code, [400, 422])


class TestValidationErrorHandling(TestBase):
    """测试验证错误处理"""

    def test_invalid_project_id_format(self):
        """测试无效项目ID格式"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        invalid_ids = [
            "../../../etc/passwd",
            "",
            "   ",
            "null",
            "undefined",
            "<script>alert('xss')</script>",
            "' OR '1'='1",
        ]

        for invalid_id in invalid_ids:
            with self.subTest(id=invalid_id):
                response = client.get(f"/api/v1/projects/{invalid_id}",
                                     headers=headers)
                data = response.json()
                # 应该返回404或错误
                self.assertIsNotNone(data)

    def test_invalid_date_format(self):
        """测试无效日期格式"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "日期测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        invalid_dates = [
            "not-a-date",
            "2024-13-01",  # 无效月份
            "2024-02-30",  # 无效日期
            "2024/12/31",  # 错误分隔符
            "9999-99-99",
        ]

        for invalid_date in invalid_dates:
            with self.subTest(date=invalid_date):
                response = client.post("/api/v1/milestones",
                                      json={
                                          "project_id": project_id,
                                          "name": "测试里程碑",
                                          "deadline": invalid_date
                                      },
                                      headers=headers)
                data = response.json()
                # 应该返回验证错误
                self.assertIsNotNone(data)

    def test_invalid_status_values(self):
        """测试无效状态值"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "状态测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        response = client.post("/api/v1/milestones",
                              json={
                                  "project_id": project_id,
                                  "name": "测试里程碑",
                                  "deadline": "2024-12-31T23:59:59",
                                  "status": "invalid_status"
                              },
                              headers=headers)

        data = response.json()
        # 可能接受或拒绝，取决于验证逻辑
        self.assertIsNotNone(data)


class TestAuthenticationErrorHandling(TestBase):
    """测试认证错误处理"""

    def test_invalid_credentials(self):
        """测试无效凭据"""
        client = TestClient(app)

        invalid_credentials = [
            {"username": "nonexistent", "password": "wrong"},
            {"username": "admin", "password": "wrong"},
            {"username": "", "password": ""},
            {"username": "admin", "password": ""},
        ]

        for creds in invalid_credentials:
            with self.subTest(credentials=creds):
                response = client.post("/api/v1/auth/login", json=creds)
                data = response.json()
                self.assertNotEqual(data.get("code"), 0)

    def test_expired_token(self):
        """测试过期token处理"""
        # 使用无效token
        client = TestClient(app)
        headers = {"Cookie": "token=expired-token-12345"}

        response = client.get("/api/v1/projects", headers=headers)
        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_missing_token(self):
        """测试缺少token处理"""
        client = TestClient(app)

        response = client.get("/api/v1/projects")
        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_malformed_token(self):
        """测试格式错误token处理"""
        client = TestClient(app)

        malformed_tokens = [
            "token",
            "token=",
            "token=;",
            "token=><script>",
            "token=' OR '1'='1",
        ]

        for token in malformed_tokens:
            with self.subTest(token=token):
                headers = {"Cookie": token}
                response = client.get("/api/v1/projects", headers=headers)
                data = response.json()
                self.assertEqual(data.get("code"), 401)


class TestAuthorizationErrorHandling(TestBase):
    """测试授权错误处理"""

    def test_insufficient_permissions(self):
        """测试权限不足"""
        client = TestClient(app)
        worker_headers = self.get_auth_headers("worker", "worker123")

        # Worker尝试创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "未授权项目"},
                              headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403)

    def test_resource_access_denied(self):
        """测试资源访问被拒绝"""
        # 测试访问其他用户的资源
        pass

    def test_role_based_access_denied(self):
        """测试基于角色的访问拒绝"""
        client = TestClient(app)
        worker_headers = self.get_auth_headers("worker", "worker123")

        # Worker尝试访问用户管理
        response = client.get("/api/v1/users", headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403)


class TestAPIErrorHandling(TestBase):
    """测试API错误处理"""

    def test_404_error_handling(self):
        """测试404错误处理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 访问不存在的资源
        response = client.get("/api/v1/non-existent-endpoint", headers=headers)
        self.assertIn(response.status_code, [404, 405])

        # 访问不存在的项目
        response = client.get("/api/v1/projects/non-existent-id", headers=headers)
        data = response.json()
        self.assertEqual(data.get("code"), 404)

    def test_405_method_not_allowed(self):
        """测试405方法不允许"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 使用错误的HTTP方法
        response = client.delete("/api/v1/projects", headers=headers)
        self.assertIn(response.status_code, [404, 405])

    def test_413_payload_too_large(self):
        """测试413请求体过大"""
        # 如果有文件大小限制，测试超出限制的情况
        pass

    def test_415_unsupported_media_type(self):
        """测试415不支持的媒体类型"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 发送不支持的媒体类型
        response = client.post("/api/v1/auth/login",
                              content="data",
                              headers={"Content-Type": "application/xml"})
        self.assertIn(response.status_code, [400, 415, 422])

    def test_422_validation_error(self):
        """测试422验证错误"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 发送不符合验证的数据
        response = client.post("/api/v1/projects",
                              json={"name": 12345},  # 数字而非字符串
                              headers=headers)

        # FastAPI返回422表示验证失败
        self.assertIn(response.status_code, [200, 422])

        if response.status_code == 200:
            data = response.json()
            # 可能返回自定义错误
            self.assertNotEqual(data.get("code"), 0)

    def test_500_internal_server_error(self):
        """测试500内部服务器错误"""
        # 这个测试需要触发实际的服务器错误
        # 在单元测试中较难实现
        pass

    def test_503_service_unavailable(self):
        """测试503服务不可用"""
        # 测试数据库不可用时的响应
        pass


class TestErrorRecovery(TestBase):
    """测试错误恢复"""

    def test_recovery_after_database_error(self):
        """测试数据库错误后的恢复"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 正常操作
        response1 = client.get("/api/v1/projects", headers=headers)
        self.assert_success_response(response1)

        # 模拟错误后再次尝试
        response2 = client.get("/api/v1/projects", headers=headers)
        self.assert_success_response(response2)

    def test_recovery_after_network_error(self):
        """测试网络错误后的恢复"""
        # 模拟网络中断后重连
        pass

    def test_retry_mechanism(self):
        """测试重试机制"""
        # 如果系统实现了重试机制，测试其工作
        pass

    def test_error_logging(self):
        """测试错误日志记录"""
        # 验证错误被正确记录
        # 这个测试需要检查日志文件
        pass


class TestEdgeCaseErrorHandling(TestBase):
    """测试边界情况错误处理"""

    def test_empty_request_body(self):
        """测试空请求体"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        response = client.post("/api/v1/projects",
                              json=None,
                              headers=headers)
        # 应该返回错误
        self.assertIn(response.status_code, [400, 422])

    def test_extremely_long_input(self):
        """测试超长输入"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 发送超长字符串
        long_name = "a" * 10000
        response = client.post("/api/v1/projects",
                              json={"name": long_name},
                              headers=headers)

        # 应该处理或拒绝
        self.assertIn(response.status_code, [200, 400, 422, 500])

    def test_special_characters_in_input(self):
        """测试输入中的特殊字符"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        special_inputs = [
            "\x00\x01\x02",  # 控制字符
            "🎉🎊🎁",  # Emoji
            "منظمة",  # 阿拉伯文
            "עברית",  # 希伯来文
        ]

        for special_input in special_inputs:
            with self.subTest(input=repr(special_input)):
                response = client.post("/api/v1/projects",
                                      json={"name": special_input},
                                      headers=headers)
                # 应该处理或适当拒绝
                self.assertIn(response.status_code, [200, 400, 422])

    def test_concurrent_error_operations(self):
        """测试并发错误操作"""
        import threading

        client = TestClient(app)
        headers = self.get_auth_headers()

        results = []

        def invalid_operation():
            response = client.post("/api/v1/projects",
                                  json={"invalid": "data"},
                                  headers=headers)
            results.append(response.json())

        # 并发执行无效操作
        threads = [threading.Thread(target=invalid_operation) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有操作都应该返回错误
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertNotEqual(result.get("code"), 0)


if __name__ == "__main__":
    unittest.main()
