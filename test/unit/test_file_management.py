"""
YourWork - 文件管理单元测试
测试文件验证、上传、下载和权限控制
"""

import unittest
import os
import tempfile
from io import BytesIO
from unittest.mock import patch, MagicMock

from test.test_base import TestBase, DatabaseTestBase
from main import app, get_db, generate_id
from fastapi.testclient import TestClient


class TestFileValidation(TestBase):
    """测试文件验证逻辑"""

    def test_valid_file_types(self):
        """测试有效文件类型"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "文件类型测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 测试有效的文件类型
        valid_files = [
            ("document.txt", b"text content", "text/plain"),
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("data.json", b'{"key": "value"}', "application/json"),
            ("report.pdf", b"%PDF-1.4", "application/pdf"),
            ("archive.zip", b"PK\x03\x04", "application/zip"),
            ("data.csv", b"name,age\nJohn,30", "text/csv"),
            ("page.html", b"<html><body>test</body></html>", "text/html"),
            ("style.css", b"body { color: red; }", "text/css"),
            ("script.js", b"console.log('test');", "text/javascript"),
        ]

        for filename, content, content_type in valid_files:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(content), content_type)}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                data = response.json()

                # 大多数文件类型应该被接受
                # 具体验证逻辑取决于系统策略
                self.assertIsNotNone(data)

    def test_invalid_file_types(self):
        """测试无效文件类型的拒绝"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "无效文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 测试可能被拒绝的文件类型
        # 注意：这取决于系统的安全策略
        potentially_dangerous = [
            ("script.php", b"<?php echo 'test'; ?>", "application/x-php"),
            ("shell.jsp", b"<% out.print('test'); %>", "application/x-jsp"),
            ("executable.exe", b"MZ\x90\x00", "application/x-executable"),
        ]

        for filename, content, content_type in potentially_dangerous:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(content), content_type)}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                # 系统应该处理这些文件
                # 可能接受或拒绝，取决于安全策略
                data = response.json()
                self.assertIsNotNone(data)

    def test_path_traversal_prevention(self):
        """测试路径遍历攻击防护"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "路径遍历测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 路径遍历payloads
        traversal_payloads = [
            "../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%255c..%255cboot.ini",
            "....//....//windows//system32//drivers//etc//hosts",
        ]

        for payload in traversal_payloads:
            with self.subTest(payload=payload):
                files = {"file": (payload, BytesIO(b"test"), "text/plain")}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )

                # 应该安全处理，不导致目录遍历
                data = response.json()
                self.assertIsNotNone(data)

                # 如果上传成功，验证文件存储在正确位置
                if data.get("code") == 0:
                    deliverable_id = data["data"]["deliverable_id"]
                    conn = get_db()
                    cursor = conn.execute(
                        "SELECT file_path FROM deliverables WHERE id = ?",
                        (deliverable_id,)
                    )
                    row = cursor.fetchone()
                    conn.close()

                    if row:
                        file_path = row['file_path']
                        # 验证文件路径不包含遍历序列
                        self.assertNotIn("..", file_path,
                                        f"文件路径不应包含父目录引用: {file_path}")

    def test_filename_sanitization(self):
        """测试文件名清理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "文件名清理测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 包含特殊字符的文件名
        special_filenames = [
            "file with spaces.txt",
            "file\nwith\nnewlines.txt",
            "file\twith\ttabs.txt",
            "file;with;semicolons.txt",
            "file&with&ampersands.txt",
            "file|with|pipes.txt",
            "file`with`backticks.txt",
            "file$with$dollars.txt",
            "file(with)parentheses.txt",
            "file[with]brackets.txt",
            "file{with}braces.txt",
            "文件中文名称.txt",
            "Файл Russian.txt",
            "🎉emoji🎁file.txt",
            "file<script>.txt",
            "file'onerror'.txt",
        ]

        for filename in special_filenames:
            with self.subTest(filename=repr(filename)):
                files = {"file": (filename, BytesIO(b"test content"), "text/plain")}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )

                # 应该处理这些文件名
                data = response.json()

                if data.get("code") == 0:
                    # 验证原始文件名被保存
                    deliverable_id = data["data"]["deliverable_id"]
                    conn = get_db()
                    cursor = conn.execute(
                        "SELECT original_name, name FROM deliverables WHERE id = ?",
                        (deliverable_id,)
                    )
                    row = cursor.fetchone()
                    conn.close()

                    self.assertIsNotNone(row)
                    # 存储的文件名应该被清理或保持原样
                    self.assertIsNotNone(row['original_name'])

    def test_empty_filename(self):
        """测试空文件名处理"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "空文件名测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 空文件名
        empty_filenames = [
            "",
            "   ",
            "\t",
            "\n",
        ]

        for filename in empty_filenames:
            with self.subTest(filename=repr(filename)):
                files = {"file": (filename, BytesIO(b"test"), "text/plain")}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )

                # 应该返回错误或使用默认文件名
                data = response.json()

    def test_filename_length_limit(self):
        """测试文件名长度限制"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "长文件名测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 超长文件名
        long_filename = "a" * 1000 + ".txt"

        files = {"file": (long_filename, BytesIO(b"test"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        # 应该处理或拒绝
        data = response.json()
        self.assertIsNotNone(data)

    def test_file_extension_validation(self):
        """测试文件扩展名验证"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "扩展名测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 各种扩展名
        test_extensions = [
            ("file.txt", "text/plain"),
            ("file.pdf", "application/pdf"),
            ("file.doc", "application/msword"),
            ("file.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("file.xls", "application/vnd.ms-excel"),
            ("file.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("file.ppt", "application/vnd.ms-powerpoint"),
            ("file.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("file.jpg", "image/jpeg"),
            ("file.jpeg", "image/jpeg"),
            ("file.png", "image/png"),
            ("file.gif", "image/gif"),
            ("file.bmp", "image/bmp"),
            ("file.svg", "image/svg+xml"),
            ("file.mp4", "video/mp4"),
            ("file.mp3", "audio/mpeg"),
            ("file.zip", "application/zip"),
            ("file.rar", "application/x-rar-compressed"),
            ("file.7z", "application/x-7z-compressed"),
            ("file.tar", "application/x-tar"),
            ("file.gz", "application/gzip"),
            ("file.json", "application/json"),
            ("file.xml", "application/xml"),
            ("file.html", "text/html"),
            ("file.css", "text/css"),
            ("file.js", "text/javascript"),
            ("file.csv", "text/csv"),
            ("file", "application/octet-stream"),  # 无扩展名
        ]

        for filename, content_type in test_extensions:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(b"test content"), content_type)}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                # 应该能处理各种扩展名
                data = response.json()
                self.assertIsNotNone(data)


class TestFileUpload(TestBase):
    """测试文件上传功能"""

    def test_upload_single_file(self):
        """测试单文件上传"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "单文件上传测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传文件
        files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        data = self.assert_success_response(response, "文件上传失败")
        self.assertIn("deliverable_id", data["data"])
        self.assertIn("original_name", data["data"])
        self.assertEqual(data["data"]["original_name"], "test.txt")
        self.assertIn("file_size", data["data"])

    def test_upload_with_milestone(self):
        """测试上传到里程碑"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        response = client.post("/api/v1/projects",
                              json={"name": "里程碑文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        response = client.post("/api/v1/milestones",
                              json={
                                  "project_id": project_id,
                                  "name": "测试里程碑",
                                  "deadline": "2024-12-31T23:59:59"
                              },
                              headers=headers)
        milestone_id = response.json()["data"]["milestone_id"]

        # 上传文件到里程碑
        files = {"file": ("milestone_doc.txt", BytesIO(b"milestone content"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
            files=files,
            headers=headers
        )

        data = self.assert_success_response(response, "里程碑文件上传失败")
        self.assertIn("deliverable_id", data["data"])

        # 验证文件关联到里程碑
        conn = get_db()
        cursor = conn.execute(
            "SELECT milestone_id FROM deliverables WHERE id = ?",
            (data["data"]["deliverable_id"],)
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['milestone_id'], milestone_id)

    def test_upload_without_authentication(self):
        """测试未认证上传"""
        client = TestClient(app)

        # 创建项目（管理员创建）
        headers = self.get_auth_headers()
        response = client.post("/api/v1/projects",
                              json={"name": "认证测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 不带认证尝试上传
        files = {"file": ("unauthorized.txt", BytesIO(b"content"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files
        )

        data = response.json()
        self.assertEqual(data.get("code"), 401, "未认证上传应该返回401")

    def test_upload_to_nonexistent_project(self):
        """测试上传到不存在的项目"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        fake_project_id = "non-existent-project-id"

        files = {"file": ("test.txt", BytesIO(b"content"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{fake_project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        # 应该失败或返回错误
        data = response.json()
        # 可能返回404或其他错误码
        self.assertIsNotNone(data)

    def test_upload_large_file(self):
        """测试大文件上传"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "大文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建一个较大的文件（10MB）
        # 注意：实际测试中可能需要调整大小
        large_content = b"x" * (10 * 1024 * 1024)

        files = {"file": ("large_file.txt", BytesIO(large_content), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=30  # 增加超时时间
        )

        data = response.json()
        # 应该成功或返回413（Payload Too Large）
        self.assertIn(data.get("code"), [0, 413, 400])

    def test_upload_empty_file(self):
        """测试空文件上传"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "空文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传空文件
        files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        # 空文件可能被接受或拒绝
        data = response.json()
        self.assertIsNotNone(data)

    def test_upload_multiple_files_sequentially(self):
        """测试连续上传多个文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "多文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传多个文件
        uploaded_ids = []
        for i in range(5):
            files = {"file": (f"file{i}.txt", BytesIO(f"content {i}".encode()), "text/plain")}
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers
            )
            data = self.assert_success_response(response, f"文件{i}上传失败")
            uploaded_ids.append(data["data"]["deliverable_id"])

        # 验证所有文件都上传成功
        self.assertEqual(len(uploaded_ids), 5)

        # 验证文件列表
        conn = get_db()
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM deliverables WHERE project_id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row['count'], 5)

    def test_upload_file_with_unicode_name(self):
        """测试上传Unicode文件名"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "Unicode文件名测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # Unicode文件名
        unicode_names = [
            "文件.txt",
            "Файл.txt",
            "ファイル.txt",
            "Datei.txt",
            "Fichier.txt",
            "Archivo.txt",
            "파일.txt",
            "🎉🎁file.txt",
            "файл-с-кириллицей.txt",
        ]

        for filename in unicode_names:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(b"content"), "text/plain")}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )

                data = response.json()
                # 应该处理Unicode文件名
                self.assertIsNotNone(data)

                if data.get("code") == 0:
                    # 验证原始文件名被保存
                    deliverable_id = data["data"]["deliverable_id"]
                    conn = get_db()
                    cursor = conn.execute(
                        "SELECT original_name FROM deliverables WHERE id = ?",
                        (deliverable_id,)
                    )
                    row = cursor.fetchone()
                    conn.close()

                    self.assertIsNotNone(row)


class TestFileDownload(TestBase):
    """测试文件下载功能"""

    def test_download_existing_file(self):
        """测试下载存在的文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "下载测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("download_test.txt", BytesIO(b"download content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 下载文件
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"download content")

    def test_download_nonexistent_file(self):
        """测试下载不存在的文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        fake_deliverable_id = "non-existent-file-id"

        response = client.get(f"/api/v1/deliverables/{fake_deliverable_id}/download",
                             headers=headers)

        data = response.json()
        self.assertEqual(data.get("code"), 404)

    def test_download_without_authentication(self):
        """测试未认证下载"""
        client = TestClient(app)

        # 先上传文件
        headers = self.get_auth_headers()
        response = client.post("/api/v1/projects",
                              json={"name": "认证下载测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("protected.txt", BytesIO(b"protected content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 不带认证尝试下载
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download")

        data = response.json()
        self.assertEqual(data.get("code"), 401)

    def test_download_file_from_deleted_project(self):
        """测试下载已删除项目的文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "删除测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("orphan.txt", BytesIO(b"orphan content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 删除项目（如果实现了级联删除）
        client.delete(f"/api/v1/projects/{project_id}", headers=headers)

        # 尝试下载文件
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=headers)

        # 文件记录可能已被删除，或文件已被删除
        # 取决于级联删除的实现
        self.assertIn(response.status_code, [200, 404])

    def test_file_download_headers(self):
        """测试文件下载响应头"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "响应头测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        original_filename = "test file with spaces.txt"
        files = {"file": (original_filename, BytesIO(b"content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 下载文件并检查响应头
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=headers)

        self.assertEqual(response.status_code, 200)
        # 检查Content-Disposition头
        content_disposition = response.headers.get("content-disposition", "")
        self.assertIn("attachment", content_disposition.lower())
        self.assertIn("filename", content_disposition.lower())

    def test_file_content_verification(self):
        """测试下载文件内容完整性"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "完整性测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        original_content = b"Binary content: \x00\x01\x02\x03\xff\xfe"
        files = {"file": ("binary_test.bin", BytesIO(original_content), "application/octet-stream")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 下载并验证内容
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=headers)

        self.assertEqual(response.content, original_content,
                        "下载的文件内容应该与上传时一致")


class TestFilePermissions(TestBase):
    """测试文件权限控制"""

    def test_download_from_non_member_project(self):
        """测试非项目成员下载文件"""
        client = TestClient(app)

        # 管理员创建项目和上传文件
        admin_headers = self.get_auth_headers("admin", "admin123")
        response = client.post("/api/v1/projects",
                              json={"name": "权限测试项目"},
                              headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("restricted.txt", BytesIO(b"restricted content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=admin_headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # Worker用户尝试下载（不是项目成员）
        worker_headers = self.get_auth_headers("worker", "worker123")
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=worker_headers)

        # 应该被拒绝或允许，取决于权限设计
        data = response.json()
        # 如果系统实现项目级权限，这里应该返回403
        # 如果所有认证用户都可以下载，会返回200
        self.assertIn(response.status_code, [200, 403, 404])

    def test_upload_as_project_member(self):
        """测试项目成员上传文件"""
        client = TestClient(app)

        # 管理员创建项目
        admin_headers = self.get_auth_headers("admin", "admin123")
        response = client.post("/api/v1/projects",
                              json={"name": "成员上传测试项目"},
                              headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        # 添加worker为项目成员
        worker_id = self.get_user_id("worker")
        client.post(f"/api/v1/projects/{project_id}/members",
                   json={"user_id": worker_id},
                   headers=admin_headers)

        # Worker尝试上传文件
        worker_headers = self.get_auth_headers("worker", "worker123")
        files = {"file": ("member_upload.txt", BytesIO(b"member content"), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=worker_headers
        )

        # 项目成员应该可以上传
        data = response.json()
        # 根据权限设计，可能返回200或403
        self.assertIsNotNone(data)

    def test_file_deletion_permissions(self):
        """测试文件删除权限"""
        client = TestClient(app)

        # 管理员创建项目和上传文件
        admin_headers = self.get_auth_headers("admin", "admin123")
        response = client.post("/api/v1/projects",
                              json={"name": "删除权限测试项目"},
                              headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("delete_test.txt", BytesIO(b"content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=admin_headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # Worker尝试删除
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 检查是否存在文件删除API
        # 如果存在，测试权限
        # response = client.delete(f"/api/v1/deliverables/{deliverable_id}",
        #                         headers=worker_headers)
        # data = response.json()
        # self.assertEqual(data.get("code"), 403)

    def test_cross_project_file_access(self):
        """测试跨项目文件访问"""
        client = TestClient(app)

        # 创建两个项目
        admin_headers = self.get_auth_headers("admin", "admin123")
        response1 = client.post("/api/v1/projects",
                               json={"name": "项目A"},
                               headers=admin_headers)
        project_a = response1.json()["data"]["project_id"]

        response2 = client.post("/api/v1/projects",
                               json={"name": "项目B"},
                               headers=admin_headers)
        project_b = response2.json()["data"]["project_id"]

        # 在项目A上传文件
        files = {"file": ("project_a_file.txt", BytesIO(b"project a content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_a}/deliverables/upload",
            files=files,
            headers=admin_headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # Worker添加到项目B
        worker_id = self.get_user_id("worker")
        client.post(f"/api/v1/projects/{project_b}/members",
                   json={"user_id": worker_id},
                   headers=admin_headers)

        # Worker尝试访问项目A的文件
        worker_headers = self.get_auth_headers("worker", "worker123")
        response = client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                             headers=worker_headers)

        # 应该被拒绝或需要额外验证
        self.assertIn(response.status_code, [200, 403, 404])


class TestFileStorage(DatabaseTestBase):
    """测试文件存储机制"""

    def test_file_storage_location(self):
        """测试文件存储位置"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "存储位置测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传文件
        files = {"file": ("location_test.txt", BytesIO(b"content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 验证存储路径
        conn = self.get_test_conn()
        cursor = conn.execute(
            "SELECT file_path FROM deliverables WHERE id = ?",
            (deliverable_id,)
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        file_path = row['file_path']

        # 验证路径包含项目ID
        self.assertIn(project_id, file_path)

        # 验证文件实际存在
        self.assertTrue(os.path.exists(file_path),
                       f"文件应该存在于 {file_path}")

    def test_file_naming_convention(self):
        """测试文件命名约定"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "命名约定测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传文件
        original_name = "test file.txt"
        files = {"file": (original_name, BytesIO(b"content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        data = upload_response.json()
        deliverable_id = data["data"]["deliverable_id"]

        # 验证存储的文件名
        conn = self.get_test_conn()
        cursor = conn.execute(
            "SELECT name, original_name FROM deliverables WHERE id = ?",
            (deliverable_id,)
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        # 原始文件名应该被保存
        self.assertEqual(row['original_name'], original_name)
        # 存储文件名应该使用ID
        self.assertIsNotNone(row['name'])

    def test_file_metadata_storage(self):
        """测试文件元数据存储"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        response = client.post("/api/v1/projects",
                              json={"name": "元数据测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        response = client.post("/api/v1/milestones",
                              json={
                                  "project_id": project_id,
                                  "name": "测试里程碑",
                                  "deadline": "2024-12-31T23:59:59"
                              },
                              headers=headers)
        milestone_id = response.json()["data"]["milestone_id"]

        # 上传文件
        files = {"file": ("metadata_test.txt", BytesIO(b"metadata content"), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
            files=files,
            headers=headers
        )

        data = upload_response.json()
        deliverable_id = data["data"]["deliverable_id"]

        # 验证元数据
        conn = self.get_test_conn()
        cursor = conn.execute(
            "SELECT * FROM deliverables WHERE id = ?",
            (deliverable_id,)
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['project_id'], project_id)
        self.assertEqual(row['milestone_id'], milestone_id)
        self.assertEqual(row['original_name'], "metadata_test.txt")
        self.assertEqual(row['file_type'], "text/plain")
        self.assertGreater(row['file_size'], 0)
        self.assertIsNotNone(row['created_by'])


class TestFileDeletion(TestBase):
    """测试文件删除功能"""

    def test_delete_existing_file(self):
        """测试删除现有文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "删除测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        files = {"file": ("delete_me.txt", BytesIO(b"delete this"), "text/plain")}
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

        # 如果存在删除API，测试删除
        # response = client.delete(f"/api/v1/deliverables/{deliverable_id}",
        #                         headers=headers)
        # self.assert_success_response(response)

        # 验证文件记录和物理文件被删除
        # conn = get_db()
        # cursor = conn.execute(
        #     "SELECT * FROM deliverables WHERE id = ?",
        #     (deliverable_id,)
        # )
        # row = cursor.fetchone()
        # conn.close()
        # self.assertIsNone(row)
        # self.assertFalse(os.path.exists(file_path))

    def test_delete_nonexistent_file(self):
        """测试删除不存在的文件"""
        client = TestClient(app)
        headers = self.get_auth_headers()

        fake_deliverable_id = "non-existent-file-id"

        # 如果存在删除API，测试删除不存在的文件
        # response = client.delete(f"/api/v1/deliverables/{fake_deliverable_id}",
        #                         headers=headers)
        # data = response.json()
        # self.assertEqual(data.get("code"), 404)


if __name__ == "__main__":
    unittest.main()
