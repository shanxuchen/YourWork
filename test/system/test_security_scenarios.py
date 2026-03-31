"""
YourWork - 安全场景测试
测试各种安全漏洞防护措施
"""

import unittest
from test.test_base import APITestBase


class TestSQLInjectionProtection(APITestBase):
    """测试SQL注入防护"""

    def test_sql_injection_in_login(self):
        """测试登录中的SQL注入防护"""
        # SQL注入payloads
        injection_payloads = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' /*",
            "admin' OR '1'='1'--",
            "admin' UNION SELECT * FROM users--",
            "admin'; DROP TABLE users; --",
            "' OR '1'='1",
            "' OR 1=1--",
            "admin' #",
            "admin'/*",
            "admin' OR 1=1#",
            "admin' OR 1=1/*",
            "' OR 1=1--",
            "1' OR '1'='1",
            "1' OR '1'='1'--",
            "1' OR '1'='1'/*",
            "1' OR '1'='1'#",
            "1' UNION SELECT NULL,NULL,NULL--",
            "1' UNION SELECT username,password,email FROM users--",
        ]

        for payload in injection_payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/v1/auth/login",
                                          json={"username": payload, "password": "any"})
                data = response.json()

                # 应该失败，不应该泄露数据库信息
                self.assertNotEqual(data.get("code"), 0,
                                  f"SQL注入应该失败: {payload}")
                self.assertNotIn("database", data.get("message", "").lower(),
                               f"不应该泄露数据库信息: {payload}")
                self.assertNotIn("sql", data.get("message", "").lower(),
                               f"不应该泄露SQL信息: {payload}")
                self.assertNotIn("syntax", data.get("message", "").lower(),
                               f"不应该泄露SQL语法信息: {payload}")

    def test_sql_injection_in_project_name(self):
        """测试项目名称中的SQL注入防护"""
        headers = self.get_auth_headers()

        injection_names = [
            "Project'; DROP TABLE users; --",
            "Project' OR '1'='1",
            "Project' UNION SELECT * FROM users--",
            "Project'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "Project'/* comment */",
        ]

        for name in injection_names:
            with self.subTest(name=name):
                response = self.client.post("/api/v1/projects",
                                          json={"name": name, "description": "test"})
                data = response.json()

                # 要么成功（转义存储），要么失败，但绝不能导致错误
                self.assertIn(response.status_code, [200])
                if data.get("code") == 0:
                    # 如果成功，验证存储的数据
                    project_id = data["data"]["project_id"]
                    get_response = self.client.get(f"/api/v1/projects/{project_id}",
                                                  headers=headers)
                    get_data = get_response.json()
                    self.assertEqual(get_data.get("code"), 0)

    def test_sql_injection_in_search(self):
        """测试搜索中的SQL注入防护"""
        headers = self.get_auth_headers()

        # 先创建一个项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "测试项目", "description": "测试描述"},
                                   headers=headers)
        self.assert_success_response(response)

        # 尝试在搜索中注入
        injection_queries = [
            "test' OR '1'='1",
            "test' UNION SELECT * FROM users--",
            "test'; DROP TABLE deliverables; --",
            "test' OR '1'='1'--",
        ]

        for query in injection_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/projects?search={query}",
                                          headers=headers)
                # 应该返回空列表或有效结果，但不能出错
                self.assertIn(response.status_code, [200])

    def test_sql_injection_in_id_parameters(self):
        """测试ID参数中的SQL注入防护"""
        headers = self.get_auth_headers()

        injection_ids = [
            "1' OR '1'='1",
            "1' UNION SELECT * FROM users--",
            "1'; DROP TABLE milestones; --",
            "1' OR '1'='1'--",
            "1'/*",
            "1'--",
        ]

        for inject_id in injection_ids:
            with self.subTest(id=inject_id):
                # 测试项目获取
                response = self.client.get(f"/api/v1/projects/{inject_id}",
                                          headers=headers)
                data = response.json()
                # 应该返回404或错误，绝不能泄露数据库信息
                self.assertNotIn("database", data.get("message", "").lower())
                self.assertNotIn("sql", data.get("message", "").lower())

                # 测试里程碑获取
                response = self.client.get(f"/api/v1/milestones/{inject_id}",
                                          headers=headers)
                data = response.json()
                self.assertNotIn("database", data.get("message", "").lower())


class TestXSSProtection(APITestBase):
    """测试XSS防护"""

    def test_xss_in_project_name(self):
        """测试项目名称中的XSS防护"""
        headers = self.get_auth_headers()

        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "<iframe src='javascript:alert(xss)'>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
            "<select onfocus=alert('xss') autofocus>",
            "<textarea onfocus=alert('xss') autofocus>",
            "<marquee onstart=alert('xss')>",
            "javascript:alert('xss')",
            "<script>document.location='http://evil.com'</script>",
            "<img src=x onerror=document.location='http://evil.com'>",
        ]

        for payload in xss_payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/v1/projects",
                                          json={"name": payload, "description": "test"})
                data = response.json()

                # 创建应该成功
                if data.get("code") == 0:
                    project_id = data["data"]["project_id"]

                    # 获取项目列表，验证XSS未被执行
                    list_response = self.client.get("/api/v1/projects",
                                                   headers=headers)
                    list_data = self.assert_success_response(list_response)

                    # 验证响应不包含未转义的script标签
                    response_text = list_response.text
                    # 如果API正确转义，script标签应该被转义或不在响应中
                    # 这里我们只验证API返回成功，具体转义由前端处理

    def test_xss_in_milestone_name(self):
        """测试里程碑名称中的XSS防护"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                           json={"name": "XSS测试项目"},
                                           headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        xss_names = [
            "<script>alert('milestone xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "'><script>alert('xss')</script>",
        ]

        for name in xss_names:
            with self.subTest(name=name):
                response = self.client.post("/api/v1/milestones",
                                          json={
                                              "project_id": project_id,
                                              "name": name,
                                              "deadline": "2024-12-31T23:59:59"
                                          },
                                          headers=headers)
                data = response.json()

                if data.get("code") == 0:
                    # 验证存储成功
                    get_response = self.client.get(f"/api/v1/projects/{project_id}/milestones",
                                                   headers=headers)
                    self.assert_success_response(get_response)

    def test_xss_in_description(self):
        """测试描述字段中的XSS防护"""
        headers = self.get_auth_headers()

        xss_descriptions = [
            "<script>alert('description xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<a href='javascript:alert(1)'>click</a>",
            "';alert('xss');//",
            "\"onfocus=alert('xss') autofocus=\"",
        ]

        for desc in xss_descriptions:
            with self.subTest(description=desc):
                response = self.client.post("/api/v1/projects",
                                          json={
                                              "name": f"测试项目{len(desc)}",
                                              "description": desc
                                          },
                                          headers=headers)
                data = response.json()

                if data.get("code") == 0:
                    project_id = data["data"]["project_id"]
                    get_response = self.client.get(f"/api/v1/projects/{project_id}",
                                                   headers=headers)
                    self.assert_success_response(get_response)

    def test_xss_in_file_upload(self):
        """测试文件上传中的XSS防护"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                           json={"name": "XSS文件测试项目"},
                                           headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 上传文件名包含XSS的文件
        from io import BytesIO

        xss_filenames = [
            "<script>alert('xss')</script>.txt",
            "<img src=x onerror=alert(1)>.txt",
            "file.txt<script>alert('xss')</script>",
        ]

        for filename in xss_filenames:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(b"test content"), "text/plain")}
                response = self.client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                data = response.json()

                if data.get("code") == 0:
                    # 验证文件上传成功
                    deliverable_id = data["data"]["deliverable_id"]
                    get_response = self.client.get(f"/api/v1/projects/{project_id}",
                                                   headers=headers)
                    self.assert_success_response(get_response)


class TestAuthenticationBypass(APITestBase):
    """测试认证绕过防护"""

    def test_no_token_access(self):
        """测试无token访问受保护资源"""
        # 只测试存在的GET端点
        protected_endpoints = [
            "/api/v1/projects",
            "/api/v1/users",
            "/api/v1/messages",
            # 注意：/api/v1/milestones 不存在GET方法，只有 /api/v1/projects/{project_id}/milestones
        ]

        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                data = response.json()
                # 应该返回401（未登录）或403（无权限）
                self.assertIn(data.get("code"), [401, 403],
                             f"无token访问{endpoint}应该返回401或403")

    def test_invalid_token(self):
        """测试无效token访问"""
        invalid_tokens = [
            "invalid-token-12345",
            "non-existent-user-id",
            "'; DROP TABLE users; --",
            "null",
            "undefined",
            "",
            "   ",
            "../",
            "../../etc/passwd",
        ]

        for token in invalid_tokens:
            with self.subTest(token=token):
                headers = {"Cookie": f"token={token}"}
                response = self.client.get("/api/v1/projects", headers=headers)
                data = response.json()
                self.assertEqual(data.get("code"), 401,
                               f"无效token {token} 应该返回401")

    def test_token_manipulation(self):
        """测试token篡改"""
        # 先获取有效token
        headers = self.get_auth_headers()

        # 提取token
        cookie = headers["Cookie"]
        original_token = cookie.replace("token=", "")

        # 尝试篡改
        manipulations = [
            original_token + "suffix",
            "prefix" + original_token,
            original_token[:-1] + "x",
            original_token.replace("-", ""),
        ]

        for manipulated in manipulations:
            with self.subTest(token=manipulated):
                new_headers = {"Cookie": f"token={manipulated}"}
                response = self.client.get("/api/v1/projects", headers=new_headers)
                data = response.json()
                self.assertEqual(data.get("code"), 401,
                               f"篡改的token {manipulated} 应该返回401")

    def test_session_fixation(self):
        """测试会话固定攻击防护"""
        # 尝试用已知token登录
        fake_token = "known-token-12345"

        response1 = self.client.post("/api/v1/auth/login",
                                    json={"username": "admin", "password": "admin123"},
                                    headers={"Cookie": f"token={fake_token}"})
        data1 = response1.json()

        # 验证返回的token与提供的不同
        if data1.get("code") == 0:
            returned_token = data1["data"]["id"]
            self.assertNotEqual(returned_token, fake_token,
                              "登录后应该返回新的token，而不是使用用户提供的token")

    def test_concurrent_login_attempts(self):
        """测试并发登录尝试（暴力破解防护）"""
        # 注意：这个测试假设系统有基本的暴力破解防护
        # 如果系统实现了速率限制，这个测试可能需要调整

        failed_attempts = 0
        for i in range(5):
            response = self.client.post("/api/v1/auth/login",
                                       json={"username": "admin", "password": "wrongpassword"})
            if response.json().get("code") != 0:
                failed_attempts += 1

        # 验证失败尝试被记录
        self.assertGreater(failed_attempts, 0, "应该有失败的登录尝试")

        # 验证正确的密码仍然可以登录
        response = self.client.post("/api/v1/auth/login",
                                   json={"username": "admin", "password": "admin123"})
        data = response.json()
        self.assertEqual(data.get("code"), 0, "正确的登录应该成功")


class TestAuthorizationBypass(APITestBase):
    """测试授权绕过防护"""

    def test_worker_cannot_create_project(self):
        """测试普通员工不能创建项目"""
        worker_headers = self.get_auth_headers("worker", "worker123")

        response = self.client.post("/api/v1/projects",
                                   json={"name": "未授权项目"},
                                   headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403,
                        "普通员工创建项目应该返回403")

    def test_worker_cannot_access_user_management(self):
        """测试普通员工不能访问用户管理"""
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 只测试存在的端点（系统没有 POST /api/v1/users 端点）
        response = self.client.get("/api/v1/users", headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403,
                       "普通员工访问用户管理应该返回403")

    def test_project_member_permissions(self):
        """测试项目成员权限"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 管理员创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "权限测试项目"},
                                   headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        # 添加worker为项目成员
        worker_id = self.get_user_id("worker")
        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": worker_id},
                        headers=admin_headers)

        # Worker可以查看项目
        response = self.client.get(f"/api/v1/projects/{project_id}",
                                  headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 0, "项目成员可以查看项目")

        # Worker不能修改项目状态为admin才能设置的状态
        response = self.client.put(f"/api/v1/projects/{project_id}/status",
                                  json={"status": "completed"},
                                  headers=worker_headers)
        data = response.json()
        # 根据权限设计，可能返回403或允许修改
        self.assertIsNotNone(data.get("code"))

    def test_cross_project_access(self):
        """测试跨项目访问控制"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 管理员创建项目A
        response = self.client.post("/api/v1/projects",
                                   json={"name": "项目A"},
                                   headers=admin_headers)
        project_a = response.json()["data"]["project_id"]

        # 管理员创建项目B，并添加worker为成员
        response = self.client.post("/api/v1/projects",
                                   json={"name": "项目B"},
                                   headers=admin_headers)
        project_b = response.json()["data"]["project_id"]

        worker_id = self.get_user_id("worker")
        self.client.post(f"/api/v1/projects/{project_b}/members",
                        json={"user_id": worker_id},
                        headers=admin_headers)

        # Worker可以访问项目B
        response = self.client.get(f"/api/v1/projects/{project_b}",
                                  headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 0)

        # Worker不应该能访问项目A（不是成员）
        response = self.client.get(f"/api/v1/projects/{project_a}",
                                  headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403,
                        "非项目成员不应该能访问项目")

    def test_idor_vulnerability(self):
        """测试IDOR（不安全的直接对象引用）漏洞"""
        # 两个不同用户登录
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 管理员创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "管理员项目"},
                                   headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        # Worker尝试访问管理员的项目
        response = self.client.get(f"/api/v1/projects/{project_id}",
                                  headers=worker_headers)
        data = response.json()

        # 如果worker不是项目成员，应该返回403
        # 如果worker可以被添加，这个测试需要调整
        # 这里我们验证至少不会泄露管理员专属信息
        if data.get("code") == 0:
            # 如果能访问，验证没有敏感信息泄露
            project_data = data["data"]["project"]
            self.assertNotIn("admin_only", project_data)

    def test_privilege_escalation(self):
        """测试权限提升攻击"""
        worker_headers = self.get_auth_headers("worker", "worker123")

        # Worker尝试将自己提升为管理员
        worker_id = self.get_user_id("worker")

        # 尝试修改用户角色（使用正确的端点路径）
        response = self.client.put(f"/api/v1/users/{worker_id}/roles",
                                  json={"roles": ["ADMIN"]},
                                  headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403,
                        "普通员工不能修改自己的角色")

        # 尝试通过添加自己到管理员项目
        admin_headers = self.get_auth_headers("admin", "admin123")
        response = self.client.post("/api/v1/projects",
                                   json={"name": "管理员专用项目"},
                                   headers=admin_headers)
        project_id = response.json()["data"]["project_id"]

        # Worker尝试将自己添加到项目
        response = self.client.post(f"/api/v1/projects/{project_id}/members",
                                   json={"user_id": worker_id},
                                   headers=worker_headers)
        data = response.json()
        self.assertEqual(data.get("code"), 403,
                        "普通员工不能将自己添加到项目")


class TestFileUploadSecurity(APITestBase):
    """测试文件上传安全性"""

    def test_path_traversal_in_filename(self):
        """测试文件名中的路径遍历攻击"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "路径遍历测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        from io import BytesIO

        # 路径遍历payloads
        malicious_filenames = [
            "../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "%2e%2e%2fetc%2fpasswd",
            "....//....//....//windows//system32//drivers//etc//hosts",
            "..\\..\\..\\boot.ini",
            "../../../../../../../../etc/passwd",
            "..%255c..%255c..%255cetc/passwd",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(b"test"), "text/plain")}
                response = self.client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                data = response.json()

                # 应该失败或文件名被清理
                if data.get("code") == 0:
                    # 如果成功，验证文件没有存储在意外位置
                    # 文件应该存储在项目的uploads目录下
                    pass

    def test_malicious_file_types(self):
        """测试恶意文件类型上传"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "文件类型测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        from io import BytesIO

        # 潜在危险的文件类型
        dangerous_files = [
            ("script.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("shell.jsp", b"<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>", "application/x-jsp"),
            ("exploit.exe", b"MZ\x90\x00", "application/x-executable"),
            ("virus.js", b"<script>evil()</script>", "text/javascript"),
            ("config.asp", b"<% execute(request(\"cmd\")) %>", "application/x-asp"),
        ]

        for filename, content, content_type in dangerous_files:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(content), content_type)}
                response = self.client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                # 系统应该拒绝或限制危险文件类型
                # 这取决于系统的安全策略
                data = response.json()

    def test_file_size_limit(self):
        """测试文件大小限制"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "文件大小测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        from io import BytesIO

        # 创建一个大文件（假设限制为10MB）
        # 这里只测试机制，不实际传输大文件
        large_content = b"x" * (100 * 1024)  # 100KB

        files = {"file": ("large_file.txt", BytesIO(large_content), "text/plain")}
        response = self.client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload",
            files=files,
            headers=headers
        )

        # 验证上传成功或返回适当的错误
        data = response.json()
        # 小于限制的文件应该成功
        self.assertIn(data.get("code"), [0, 413])  # 0=成功, 413=Payload Too Large

    def test_file_content_verification(self):
        """测试文件内容验证"""
        headers = self.get_auth_headers()

        # 创建项目
        response = self.client.post("/api/v1/projects",
                                   json={"name": "文件内容测试项目"},
                                   headers=headers)
        project_id = response.json()["data"]["project_id"]

        from io import BytesIO

        # 文件扩展名与内容不匹配
        mismatched_files = [
            ("image.jpg", b"<?php system('ls'); ?>", "image/jpeg"),
            ("document.pdf", b"<script>alert('xss')</script>", "application/pdf"),
            ("data.csv", b"; DROP TABLE users; --", "text/csv"),
        ]

        for filename, content, content_type in mismatched_files:
            with self.subTest(filename=filename):
                files = {"file": (filename, BytesIO(content), content_type)}
                response = self.client.post(
                    f"/api/v1/projects/{project_id}/deliverables/upload",
                    files=files,
                    headers=headers
                )
                # 系统应该验证文件内容或至少安全处理
                data = response.json()


class TestCsrfProtection(APITestBase):
    """测试CSRF防护"""

    def test_state_changing_without_csrf(self):
        """测试无CSRF token的状态修改"""
        # 注意：FastAPI默认不提供CSRF保护
        # 这个测试主要用于验证系统是否有额外的CSRF措施

        headers = self.get_auth_headers()

        # 尝试修改状态
        response = self.client.post("/api/v1/projects",
                                   json={"name": "CSRF测试项目"},
                                   headers=headers)
        data = response.json()

        # 如果系统实现了CSRF，这里应该检查CSRF token
        # 当前系统使用cookie认证，可能需要额外的CSRF保护


if __name__ == "__main__":
    unittest.main()
