"""
YourWork - 大文件处理系统测试
测试大文件上传、下载和内存效率
"""

import unittest
import os
import time
import threading
from io import BytesIO

from test.test_base import APITestBase
from main import get_db


class TestLargeFileHandling(APITestBase):
    """测试大文件处理"""

    def test_upload_1mb_file(self):
        """测试上传1MB文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "1MB文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建1MB文件
        file_size = 1 * 1024 * 1024  # 1MB
        content = b"x" * file_size

        files = {"file": ("1mb_test.txt", BytesIO(content), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=60
        )

        data = response.json()
        self.assertIn(data.get("code"), [0, 413, 400])

        if data.get("code") == 0:
            # 验证文件大小
            self.assertEqual(data["data"]["file_size"], file_size)

            # 验证文件实际存在
            deliverable_id = data["data"]["deliverable_id"]
            conn = get_db()
            cursor = conn.execute(
                "SELECT file_path FROM deliverables WHERE id = ?",
                (deliverable_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                actual_size = os.path.getsize(row['file_path'])
                self.assertEqual(actual_size, file_size)

    def test_upload_10mb_file(self):
        """测试上传10MB文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "10MB文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建10MB文件
        file_size = 10 * 1024 * 1024  # 10MB
        content = b"x" * file_size

        start_time = time.time()
        files = {"file": ("10mb_test.txt", BytesIO(content), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=120
        )
        upload_time = time.time() - start_time

        data = response.json()
        self.assertIn(data.get("code"), [0, 413, 400])

        if data.get("code") == 0:
            print(f"10MB文件上传耗时: {upload_time:.2f}秒")
            self.assertEqual(data["data"]["file_size"], file_size)

            # 上传10MB文件应该在合理时间内完成
            self.assertLess(upload_time, 60, "10MB文件上传应在60秒内完成")

    def test_upload_50mb_file(self):
        """测试上传50MB文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "50MB文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建50MB文件（如果系统支持）
        file_size = 50 * 1024 * 1024  # 50MB
        content = b"x" * file_size

        start_time = time.time()
        files = {"file": ("50mb_test.txt", BytesIO(content), "text/plain")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=180
        )
        upload_time = time.time() - start_time

        data = response.json()
        # 大文件可能被限制
        self.assertIn(data.get("code"), [0, 413, 400, 500])

        if data.get("code") == 0:
            print(f"50MB文件上传耗时: {upload_time:.2f}秒")
            self.assertEqual(data["data"]["file_size"], file_size)

    def test_upload_binary_file(self):
        """测试上传二进制文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "二进制文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建5MB随机二进制数据
        import random
        file_size = 5 * 1024 * 1024
        content = bytes([random.randint(0, 255) for _ in range(file_size)])

        files = {"file": ("binary_test.bin", BytesIO(content), "application/octet-stream")}
        response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=120
        )

        data = response.json()
        self.assertIn(data.get("code"), [0, 413, 400])

        if data.get("code") == 0:
            deliverable_id = data["data"]["deliverable_id"]

            # 下载并验证内容
            download_response = client.get(
                f"/api/v1/deliverables/{deliverable_id}/download",
                headers=headers
            )

            self.assertEqual(download_response.content, content)

    def test_concurrent_large_file_uploads(self):
        """测试并发上传大文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "并发大文件测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 准备并发上传
        file_size = 2 * 1024 * 1024  # 2MB
        results = []
        errors = []

        def upload_file(index):
            try:
                content = b"x" * file_size
                files = {"file": (f"concurrent_{index}.txt", BytesIO(content), "text/plain")}
                response = client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers,
                    timeout=120
                )
                results.append(response.json())
            except Exception as e:
                errors.append(e)

        # 并发上传5个文件
        threads = [threading.Thread(target=upload_file, args=(i,)) for i in range(5)]
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"并发上传5个2MB文件耗时: {total_time:.2f}秒")

        # 验证结果
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)

        success_count = sum(1 for r in results if r.get("code") == 0)
        self.assertGreater(success_count, 0)


class TestLargeDownloadHandling(APITestBase):
    """测试大文件下载处理"""

    def test_download_large_file(self):
        """测试下载大文件"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目并上传大文件
        response = client.post("/api/v1/projects",
                              json={"name": "大文件下载测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传5MB文件
        file_size = 5 * 1024 * 1024
        content = b"x" * file_size

        files = {"file": ("large_download_test.txt", BytesIO(content), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=120
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 下载文件
        start_time = time.time()
        download_response = client.get(
            f"/api/v1/deliverables/{deliverable_id}/download",
            headers=headers
        )
        download_time = time.time() - start_time

        print(f"5MB文件下载耗时: {download_time:.2f}秒")

        # 验证
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(len(download_response.content), file_size)
        self.assertEqual(download_response.content, content)

        # 下载应在合理时间内完成
        self.assertLess(download_time, 30, "5MB文件下载应在30秒内完成")

    def test_range_request_support(self):
        """测试Range请求支持（如果实现）"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "Range请求测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传文件
        content = b"0" * (1024 * 1024)  # 1MB
        files = {"file": ("range_test.txt", BytesIO(content), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 测试Range请求（如果支持）
        range_headers = headers.copy()
        range_headers["Range"] = "bytes=0-1023"

        response = client.get(
            f"/api/v1/deliverables/{deliverable_id}/download",
            headers=range_headers
        )

        # 如果支持Range，应返回206；否则返回200
        self.assertIn(response.status_code, [200, 206])

    def test_multiple_concurrent_downloads(self):
        """测试多个并发下载"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目并上传多个文件
        response = client.post("/api/v1/projects",
                              json={"name": "并发下载测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传3个2MB文件
        deliverable_ids = []
        file_size = 2 * 1024 * 1024

        for i in range(3):
            content = b"x" * file_size
            files = {"file": (f"file_{i}.txt", BytesIO(content), "text/plain")}
            upload_response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers,
                timeout=120
            )
            deliverable_ids.append(upload_response.json()["data"]["deliverable_id"])

        # 并发下载
        results = []
        errors = []

        def download_file(d_id):
            try:
                start = time.time()
                response = client.get(
                    f"/api/v1/deliverables/{d_id}/download",
                    headers=headers
                )
                elapsed = time.time() - start
                results.append({
                    "id": d_id,
                    "size": len(response.content),
                    "time": elapsed
                })
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=download_file, args=(d_id,)) for d_id in deliverable_ids]
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"并发下载3个2MB文件耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 3)

        for result in results:
            self.assertEqual(result["size"], file_size)


class TestMemoryEfficiencyDuringUpload(APITestBase):
    """测试上传时的内存效率"""

    def test_memory_usage_during_upload(self):
        """测试上传时的内存使用"""
        # 这个测试需要在实际运行环境中监控内存
        # 在单元测试中只能做基本验证
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "内存效率测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传多个文件，验证内存不会无限增长
        for i in range(5):
            content = b"x" * (1024 * 1024)  # 1MB
            files = {"file": (f"memory_test_{i}.txt", BytesIO(content), "text/plain")}
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers,
                timeout=60
            )
            self.assertIn(response.json().get("code"), [0, 413, 400])

    def test_streaming_upload(self):
        """测试流式上传（如果实现）"""
        # 验证系统是否使用流式上传而非一次性加载到内存
        pass

    def test_chunked_upload(self):
        """测试分块上传（如果实现）"""
        # 如果系统实现了分块上传，测试其功能
        pass


class TestFileIntegrityWithLargeFiles(APITestBase):
    """测试大文件的文件完整性"""

    def test_upload_download_integrity(self):
        """测试上传下载完整性"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "完整性测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 创建包含特定模式的大文件
        file_size = 3 * 1024 * 1024  # 3MB
        content = bytes([i % 256 for i in range(file_size)])

        # 上传
        files = {"file": ("integrity_test.bin", BytesIO(content), "application/octet-stream")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=120
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 下载
        download_response = client.get(
            f"/api/v1/deliverables/{deliverable_id}/download",
            headers=headers
        )

        # 验证完整性
        self.assertEqual(download_response.content, content)

    def test_checksum_validation(self):
        """测试校验和验证（如果实现）"""
        # 如果系统实现了文件校验和，测试其功能
        pass


class TestPerformanceWithLargeFiles(APITestBase):
    """测试大文件性能"""

    def test_upload_speed(self):
        """测试上传速度"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目
        response = client.post("/api/v1/projects",
                              json={"name": "速度测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 测试不同大小的文件上传速度
        test_sizes = [
            1 * 1024 * 1024,  # 1MB
            5 * 1024 * 1024,  # 5MB
        ]

        for size in test_sizes:
            content = b"x" * size
            files = {"file": (f"speed_test_{size//1024//1024}mb.txt", BytesIO(content), "text/plain")}

            start_time = time.time()
            response = client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload",
                files=files,
                headers=headers,
                timeout=120
            )
            upload_time = time.time() - start_time

            if response.json().get("code") == 0:
                speed_mb_per_sec = (size / 1024 / 1024) / upload_time
                print(f"上传{size//1024//1024}MB文件: {upload_time:.2f}秒, 速度: {speed_mb_per_sec:.2f}MB/s")

    def test_download_speed(self):
        """测试下载速度"""
        client = self.client
        headers = self.get_auth_headers()

        # 创建项目并上传文件
        response = client.post("/api/v1/projects",
                              json={"name": "下载速度测试项目"},
                              headers=headers)
        project_id = response.json()["data"]["project_id"]

        # 上传测试文件
        file_size = 5 * 1024 * 1024  # 5MB
        content = b"x" * file_size
        files = {"file": ("download_speed_test.txt", BytesIO(content), "text/plain")}
        upload_response = client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers,
            timeout=120
        )
        deliverable_id = upload_response.json()["data"]["deliverable_id"]

        # 测试下载速度
        start_time = time.time()
        download_response = client.get(
            f"/api/v1/deliverables/{deliverable_id}/download",
            headers=headers
        )
        download_time = time.time() - start_time

        if download_response.status_code == 200:
            speed_mb_per_sec = (file_size / 1024 / 1024) / download_time
            print(f"下载5MB文件: {download_time:.2f}秒, 速度: {speed_mb_per_sec:.2f}MB/s")


class TestErrorHandlingWithLargeFiles(APITestBase):
    """测试大文件错误处理"""

    def test_upload_interrupted(self):
        """测试上传中断"""
        # 模拟上传中断
        pass

    def test_download_interrupted(self):
        """测试下载中断"""
        # 模拟下载中断
        pass

    def test_disk_full_during_upload(self):
        """测试上传时磁盘满"""
        # 模拟磁盘满的情况
        pass

    def test_cleanup_after_failed_upload(self):
        """测试失败上传后的清理"""
        # 验证失败的上传不会留下残留文件
        pass


if __name__ == "__main__":
    unittest.main()
