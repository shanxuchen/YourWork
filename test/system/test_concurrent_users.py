"""
YourWork - 并发用户系统测试
测试大量并发用户访问系统
"""

import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from test.test_base import APITestBase


class TestConcurrentUsers(APITestBase):
    """测试并发用户访问"""

    def test_10_concurrent_login(self):
        """测试10个并发登录"""
        results = []
        errors = []

        def user_login(username, password):
            try:
                start_time = time.time()
                response = self.client.post("/api/v1/auth/login",
                                          json={"username": username, "password": password})
                elapsed = time.time() - start_time
                results.append({
                    "username": username,
                    "response": response.json(),
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"username": username, "error": str(e)})

        # 10个并发登录
        credentials = [
            ("admin", "admin123"),
            ("manager", "manager123"),
            ("worker", "worker123"),
            ("admin", "admin123"),
            ("manager", "manager123"),
            ("worker", "worker123"),
            ("admin", "admin123"),
            ("manager", "manager123"),
            ("worker", "worker123"),
            ("admin", "admin123"),
        ]

        start_time = time.time()
        threads = [threading.Thread(target=user_login, args=(u, p)) for u, p in credentials]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"10个并发登录耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0, f"发生错误: {errors}")
        self.assertEqual(len(results), 10)

        success_count = sum(1 for r in results if r["response"].get("code") == 0)
        self.assertEqual(success_count, 10, "所有登录都应该成功")

        # 平均响应时间应合理
        avg_time = sum(r["time"] for r in results) / len(results)
        print(f"平均登录响应时间: {avg_time:.3f}秒")
        self.assertLess(avg_time, 5.0, "平均登录时间应小于5秒")

    def test_50_concurrent_login(self):
        """测试50个并发登录"""
        results = []
        errors = []

        def user_login(index):
            try:
                start_time = time.time()
                response = self.client.post("/api/v1/auth/login",
                                          json={"username": "admin", "password": "admin123"})
                elapsed = time.time() - start_time
                results.append({
                    "index": index,
                    "response": response.json(),
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(user_login, i) for i in range(50)]
            for future in as_completed(futures):
                pass
        total_time = time.time() - start_time

        print(f"50个并发登录耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 50)

    def test_100_concurrent_read_operations(self):
        """测试100个并发读取操作"""
        headers = self.get_auth_headers()

        # 创建一些测试数据
        for i in range(5):
            self.client.post("/api/v1/projects",
                            json={"name": f"并发测试项目{i}"},
                            headers=headers)

        results = []
        errors = []

        def read_projects(index):
            try:
                start_time = time.time()
                response = self.client.get("/api/v1/projects", headers=headers)
                elapsed = time.time() - start_time
                results.append({
                    "index": index,
                    "status": response.status_code,
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        start_time = time.time()
        threads = [threading.Thread(target=read_projects, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"100个并发读取耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 100)

        success_count = sum(1 for r in results if r["status"] == 200)
        self.assertEqual(success_count, 100)

        avg_time = sum(r["time"] for r in results) / len(results)
        print(f"平均读取响应时间: {avg_time:.3f}秒")

    def test_concurrent_project_access(self):
        """测试并发项目访问"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "并发访问测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        results = []
        errors = []

        def access_project(index):
            try:
                start_time = time.time()
                response = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
                elapsed = time.time() - start_time
                results.append({
                    "index": index,
                    "response": response.json(),
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        # 50个并发访问同一项目
        start_time = time.time()
        threads = [threading.Thread(target=access_project, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"50个并发访问同一项目耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 50)

        success_count = sum(1 for r in results if r["response"].get("code") == 0)
        self.assertEqual(success_count, 50)

    def test_concurrent_milestone_creation(self):
        """测试并发创建里程碑"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "并发里程碑测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        results = []
        errors = []

        def create_milestone(index):
            try:
                start_time = time.time()
                response = self.client.post("/api/v1/milestones",
                                          json={
                                              "project_id": project_id,
                                              "name": f"并发里程碑{index}",
                                              "deadline": "2024-12-31T23:59:59"
                                          },
                                          headers=headers)
                elapsed = time.time() - start_time
                results.append({
                    "index": index,
                    "response": response.json(),
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        # 20个并发创建里程碑
        start_time = time.time()
        threads = [threading.Thread(target=create_milestone, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"20个并发创建里程碑耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 20)

        success_count = sum(1 for r in results if r["response"].get("code") == 0)
        self.assertEqual(success_count, 20)

        # 验证所有里程碑都创建成功
        response = self.client.get(f"/api/v1/projects/{project_id}/milestones", headers=headers)
        data = response.json()
        if data.get("code") == 0:
            milestone_count = len(data["data"]["milestones"])
            self.assertEqual(milestone_count, 20)


class TestConcurrentWriteOperations(APITestBase):
    """测试并发写操作"""

    def test_concurrent_project_creation(self):
        """测试并发创建项目"""
        headers = self.get_auth_headers()

        results = []
        errors = []

        def create_project(index):
            try:
                start_time = time.time()
                response = self.client.post("/api/v1/projects",
                                          json={"name": f"并发项目{index}"},
                                          headers=headers)
                elapsed = time.time() - start_time
                results.append({
                    "index": index,
                    "response": response.json(),
                    "time": elapsed
                })
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        # 10个并发创建项目
        start_time = time.time()
        threads = [threading.Thread(target=create_project, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"10个并发创建项目耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)

        success_count = sum(1 for r in results if r["response"].get("code") == 0)
        self.assertEqual(success_count, 10)

        # 验证项目ID都唯一
        project_ids = [r["response"]["data"]["project_id"] for r in results if r["response"].get("code") == 0]
        self.assertEqual(len(project_ids), len(set(project_ids)), "项目ID应该唯一")

    def test_concurrent_milestone_updates(self):
        """测试并发更新里程碑"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        response = self.client.post("/api/v1/projects",
                                   json={"name": "并发更新测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        response = self.client.post("/api/v1/milestones",
                                   json={
                                       "project_id": project_id,
                                       "name": "测试里程碑",
                                       "status": "created",
                                       "deadline": "2024-12-31T23:59:59"
                                   },
                                   headers=headers)
        milestone_id = response.json()["data"]["milestone_id"]

        results = []
        errors = []

        def update_milestone(index):
            try:
                response = self.client.put(f"/api/v1/milestones/{milestone_id}",
                                         json={"status": "in_progress"},
                                         headers=headers)
                results.append(response.json())
            except Exception as e:
                errors.append(str(e))

        # 10个并发更新
        threads = [threading.Thread(target=update_milestone, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证至少有一些更新成功
        self.assertEqual(len(errors), 0)
        success_count = sum(1 for r in results if r.get("code") == 0)
        self.assertGreater(success_count, 0)

    def test_concurrent_project_member_addition(self):
        """测试并发添加项目成员"""
        admin_headers = self.get_auth_headers("admin", "admin123")

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "成员并发测试项目"},
                                   headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        # 创建测试用户
        user_ids = []
        for i in range(10):
            from main import generate_id, hash_password
            from test.test_base import get_db
            conn = get_db()
            user_id = generate_id()
            conn.execute(
                """INSERT INTO users (id, username, password, display_name, email, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, f"concurrentuser{i}", hash_password("password123"), f"用户{i}", f"user{i}@test.com", 1, "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )
            conn.commit()
            conn.close()
            user_ids.append(user_id)

        results = []
        errors = []

        def add_member(user_id):
            try:
                response = self.client.post(f"/api/v1/projects/{project_id}/members",
                                          json={"user_id": user_id},
                                          headers=admin_headers)
                results.append(response.json())
            except Exception as e:
                errors.append(str(e))

        # 并发添加成员
        threads = [threading.Thread(target=add_member, args=(uid,)) for uid in user_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)

        success_count = sum(1 for r in results if r.get("code") == 0)
        self.assertGreater(success_count, 0)


class TestMixedConcurrentOperations(APITestBase):
    """测试混合并发操作"""

    def test_concurrent_read_write(self):
        """测试并发读写操作"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "读写混合测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        read_results = []
        write_results = []
        errors = []

        def read_operation():
            try:
                response = self.client.get("/api/v1/projects", headers=headers)
                read_results.append(response.status_code)
            except Exception as e:
                errors.append(f"Read error: {str(e)}")

        def write_operation():
            try:
                response = self.client.post("/api/v1/milestones",
                                          json={
                                              "project_id": project_id,
                                              "name": f"里程碑{time.time()}",
                                              "deadline": "2024-12-31T23:59:59"
                                          },
                                          headers=headers)
                write_results.append(response.json().get("code"))
            except Exception as e:
                errors.append(f"Write error: {str(e)}")

        # 混合读写操作
        threads = []
        for i in range(10):
            threads.append(threading.Thread(target=read_operation))
            threads.append(threading.Thread(target=write_operation))

        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"20个混合并发操作(10读10写)耗时: {total_time:.2f}秒")

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(read_results), 10)
        self.assertEqual(len(write_results), 10)

        read_success = sum(1 for r in read_results if r == 200)
        write_success = sum(1 for w in write_results if w == 0)

        self.assertEqual(read_success, 10)
        self.assertEqual(write_success, 10)

    def test_concurrent_different_users(self):
        """测试不同用户的并发操作"""
        results = []
        errors = []

        def user_operations(username, password):
            try:
                # 登录
                login_response = self.client.post("/api/v1/auth/login",
                                                json={"username": username, "password": password})
                login_data = login_response.json()

                if login_data.get("code") != 0:
                    results.append({"user": username, "success": False})
                    return

                headers = {"Cookie": f"token={login_data['data']['id']}"}

                # 获取项目列表
                projects_response = self.client.get("/api/v1/projects", headers=headers)

                # 创建项目（如果权限允许）
                create_response = self.client.post("/api/v1/projects",
                                                 json={"name": f"{username}的项目"},
                                                 headers=headers)

                results.append({
                    "user": username,
                    "login_success": login_data.get("code") == 0,
                    "projects_success": projects_response.json().get("code") == 0,
                    "create_success": create_response.json().get("code") == 0
                })
            except Exception as e:
                errors.append({"user": username, "error": str(e)})

        # 不同用户并发操作
        users = [
            ("admin", "admin123"),
            ("manager", "manager123"),
            ("worker", "worker123"),
        ]

        threads = [threading.Thread(target=user_operations, args=(u, p)) for u, p in users]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 3)


class TestConcurrentSessions(APITestBase):
    """测试并发会话管理"""

    def test_multiple_simultaneous_sessions(self):
        """测试多个同时会话"""
        # 模拟同一用户多个会话
        headers = self.get_auth_headers()

        results = []

        def session_operation(session_id):
            response = self.client.get("/api/v1/projects", headers=headers)
            results.append({
                "session_id": session_id,
                "status": response.status_code
            })

        # 10个"会话"（实际是同一个token）
        threads = [threading.Thread(target=session_operation, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        for r in results:
            self.assertEqual(r["status"], 200)

    def test_session_isolation(self):
        """测试会话隔离"""
        # 创建不同用户会话
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        results = []

        def admin_operations():
            response = self.client.get("/api/v1/users", headers=admin_headers)
            results.append({
                "user": "admin",
                "endpoint": "/api/v1/users",
                "code": response.json().get("code")
            })

        def worker_operations():
            response = self.client.get("/api/v1/users", headers=worker_headers)
            results.append({
                "user": "worker",
                "endpoint": "/api/v1/users",
                "code": response.json().get("code")
            })

        # 并发执行
        threads = [
            threading.Thread(target=admin_operations),
            threading.Thread(target=admin_operations),
            threading.Thread(target=worker_operations),
            threading.Thread(target=worker_operations),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证权限隔离
        admin_results = [r for r in results if r["user"] == "admin"]
        worker_results = [r for r in results if r["user"] == "worker"]

        # Admin应该能访问
        for r in admin_results:
            self.assertEqual(r["code"], 0)

        # Worker不应该能访问
        for r in worker_results:
            self.assertEqual(r["code"], 403)


class TestStressScenarios(APITestBase):
    """测试压力场景"""

    def test_rapid_successive_requests(self):
        """测试快速连续请求"""
        headers = self.get_auth_headers()

        start_time = time.time()
        for i in range(100):
            response = self.client.get("/api/v1/projects", headers=headers)
            if response.status_code != 200:
                self.fail(f"请求{i}失败")
        total_time = time.time() - start_time

        print(f"100个连续请求耗时: {total_time:.2f}秒")
        print(f"平均每个请求: {total_time/100:.3f}秒")

        # 验证性能
        self.assertLess(total_time, 30, "100个请求应在30秒内完成")

    def test_burst_traffic(self):
        """测试突发流量"""
        headers = self.get_auth_headers()

        results = []

        def burst_request(batch_id):
            batch_results = []
            for i in range(10):
                response = self.client.get("/api/v1/projects", headers=headers)
                batch_results.append(response.status_code)
            results.append({
                "batch_id": batch_id,
                "results": batch_results
            })

        # 10个批次，每批10个请求
        threads = [threading.Thread(target=burst_request, args=(i,)) for i in range(10)]
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.time() - start_time

        print(f"100个突发请求(10批次×10)耗时: {total_time:.2f}秒")

        # 验证所有请求都成功
        for batch in results:
            for status in batch["results"]:
                self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
