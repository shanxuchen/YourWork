"""
YourWork - 里程碑管理流程集成测试
测试完整的里程碑管理流程，包括创建、更新、日志记录等
"""

import unittest

from test.test_base import APITestBase


class TestMilestoneLifecycleFlow(APITestBase):
    """测试里程碑完整生命周期"""

    def test_create_update_complete_milestone_flow(self):
        """测试里程碑的完整流程：创建 -> 更新 -> 完成"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "里程碑测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建里程碑
        create_response = self.client.post("/api/v1/milestones",
                                          json={
                                              "project_id": project_id,
                                              "name": "需求分析",
                                              "description": "完成需求文档",
                                              "type": "milestone",
                                              "deadline": "2024-12-31T23:59:59"
                                          },
                                          headers=headers)
        create_data = self.assert_success_response(create_response, "创建里程碑失败")
        milestone_id = create_data["data"]["milestone_id"]

        # 读取里程碑详情
        read_response = self.client.get(f"/api/v1/milestones/{milestone_id}",
                                       headers=headers)
        read_data = self.assert_success_response(read_response, "读取里程碑失败")
        self.assertEqual(read_data["data"]["name"], "需求分析")
        self.assertEqual(read_data["data"]["status"], "created")

        # 更新里程碑
        update_response = self.client.put(f"/api/v1/milestones/{milestone_id}",
                                         json={
                                             "name": "需求分析（更新）",
                                             "description": "完成详细需求文档",
                                             "status": "waiting"
                                         },
                                         headers=headers)
        self.assert_success_response(update_response, "更新里程碑失败")

        # 验证更新
        verify_response = self.client.get(f"/api/v1/milestones/{milestone_id}",
                                         headers=headers)
        verify_data = self.assert_success_response(verify_response)
        self.assertEqual(verify_data["data"]["name"], "需求分析（更新）")
        self.assertEqual(verify_data["data"]["status"], "waiting")

        # 完成里程碑
        complete_response = self.client.put(f"/api/v1/milestones/{milestone_id}",
                                           json={
                                               "name": "需求分析（更新）",
                                               "description": "完成详细需求文档",
                                               "status": "completed"
                                           },
                                           headers=headers)
        self.assert_success_response(complete_response, "完成里程碑失败")

    def test_create_milestone_with_all_types(self):
        """测试创建不同类型的里程碑"""
        headers = self.get_auth_headers()

        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "类型测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建里程碑
        milestone_response = self.client.post("/api/v1/milestones",
                                            json={
                                                "project_id": project_id,
                                                "name": "开发里程碑",
                                                "type": "milestone"
                                            },
                                            headers=headers)
        milestone_data = self.assert_success_response(milestone_response)
        milestone_id = milestone_data["data"]["milestone_id"]

        # 验证类型
        detail_response = self.client.get(f"/api/v1/milestones/{milestone_id}",
                                         headers=headers)
        detail_data = self.assert_success_response(detail_response)
        self.assertEqual(detail_data["data"]["type"], "milestone")

        # 创建验收目标
        acceptance_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "第一阶段验收",
                                                 "type": "acceptance"
                                             },
                                             headers=headers)
        acceptance_data = self.assert_success_response(acceptance_response)
        acceptance_id = acceptance_data["data"]["milestone_id"]

        # 验证类型
        acceptance_detail = self.client.get(f"/api/v1/milestones/{acceptance_id}",
                                           headers=headers)
        acceptance_detail_data = self.assert_success_response(acceptance_detail)
        self.assertEqual(acceptance_detail_data["data"]["type"], "acceptance")

    def test_milestone_status_transitions(self):
        """测试里程碑状态转换"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "状态转换测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 状态转换：created -> waiting
        self.client.put(f"/api/v1/milestones/{milestone_id}",
                       json={"status": "waiting"},
                       headers=headers)

        # 状态转换：waiting -> paused
        self.client.put(f"/api/v1/milestones/{milestone_id}",
                       json={"status": "paused"},
                       headers=headers)

        # 状态转换：paused -> completed
        self.client.put(f"/api/v1/milestones/{milestone_id}",
                       json={"status": "completed"},
                       headers=headers)

        # 验证最终状态
        final_response = self.client.get(f"/api/v1/milestones/{milestone_id}",
                                        headers=headers)
        final_data = self.assert_success_response(final_response)
        self.assertEqual(final_data["data"]["status"], "completed")


class TestMilestoneLogsFlow(APITestBase):
    """测试里程碑操作日志流程"""

    def test_create_milestone_with_auto_log(self):
        """测试创建里程碑时自动记录日志"""
        headers = self.get_auth_headers()

        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "日志测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建里程碑（应该自动创建日志）
        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "带日志的里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 获取操作日志
        logs_response = self.client.get(f"/api/v1/milestones/{milestone_id}/logs",
                                       headers=headers)
        logs_data = self.assert_success_response(logs_response)
        self.assertGreater(len(logs_data["data"]), 0, "应该有自动创建的日志")

    def test_add_manual_milestone_log(self):
        """测试手动添加里程碑日志"""
        headers = self.get_auth_headers()

        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "手动日志测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 手动添加日志
        add_log_response = self.client.post(f"/api/v1/milestones/{milestone_id}/logs",
                                           json={
                                               "action": "更新状态",
                                               "description": "将状态改为进行中"
                                           },
                                           headers=headers)
        self.assert_success_response(add_log_response, "添加日志失败")

        # 验证日志已添加
        logs_response = self.client.get(f"/api/v1/milestones/{milestone_id}/logs",
                                       headers=headers)
        logs_data = self.assert_success_response(logs_response)
        log_actions = [log["action"] for log in logs_data["data"]]
        self.assertIn("更新状态", log_actions)

    def test_milestone_logs_chronological_order(self):
        """测试里程碑日志按时间顺序排列"""
        headers = self.get_auth_headers()

        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "日志顺序测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 添加多条日志
        for i in range(3):
            self.client.post(f"/api/v1/milestones/{milestone_id}/logs",
                            json={
                                "action": f"操作{i+1}",
                                "description": f"第{i+1}次操作"
                            },
                            headers=headers)

        # 获取日志并验证顺序
        logs_response = self.client.get(f"/api/v1/milestones/{milestone_id}/logs",
                                       headers=headers)
        logs_data = self.assert_success_response(logs_response)
        logs = logs_data["data"]

        # 验证日志按创建时间倒序排列（最新的在前）
        for i in range(len(logs) - 1):
            self.assertGreaterEqual(logs[i]["created_at"], logs[i+1]["created_at"])


class TestMilestoneWithDeliverablesFlow(APITestBase):
    """测试里程碑与产出物的集成流程"""

    def test_milestone_with_multiple_deliverables(self):
        """测试里程碑关联多个产出物"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "文档测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "需求分析",
                                                 "type": "milestone"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 上传多个产出物
        from io import BytesIO
        deliverable_ids = []

        for i in range(3):
            file_content = f"Document {i+1} content".encode()
            files = {"file": (f"doc{i+1}.txt", BytesIO(file_content), "text/plain")}
            upload_response = self.client.post(
                f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
                files=files,
                headers=headers)
            upload_data = self.assert_success_response(upload_response)
            deliverable_ids.append(upload_data["data"]["deliverable_id"])

        # 获取该里程碑的产出物
        deliverables_response = self.client.get(
            f"/api/v1/projects/{project_id}/deliverables?milestone_id={milestone_id}",
            headers=headers)
        deliverables_data = self.assert_success_response(deliverables_response)
        self.assertGreaterEqual(len(deliverables_data["data"]), 3)

    def test_deliverable_download_after_upload(self):
        """测试上传后下载产出物"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "下载测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 上传文件
        from io import BytesIO
        file_content = b"Test content for download"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        upload_response = self.client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
            files=files,
            headers=headers)
        upload_data = self.assert_success_response(upload_response)
        deliverable_id = upload_data["data"]["deliverable_id"]

        # 下载文件（注意：这是重定向到文件，不是 JSON 响应）
        download_response = self.client.get(f"/api/v1/deliverables/{deliverable_id}/download",
                                           headers=headers)
        self.assertIn(download_response.status_code, [200, 307])  # 307 是临时重定向


class TestMilestoneParentChildFlow(APITestBase):
    """测试里程碑父子关系流程"""

    def test_parent_child_milestones(self):
        """测试父子里程碑关系"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "父子里程碑测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建父里程碑
        parent_response = self.client.post("/api/v1/milestones",
                                         json={
                                             "project_id": project_id,
                                             "name": "父阶段",
                                             "type": "milestone"
                                         },
                                         headers=headers)
        parent_id = parent_response.json()["data"]["milestone_id"]

        # 创建子里程碑（需要在数据库中直接设置 parent_id）
        # 因为 API 可能没有直接支持，这里我们验证数据结构
        from main import get_db, generate_id
        conn = get_db()
        child_id = generate_id()
        from datetime import datetime
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, parent_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (child_id, project_id, "milestone", "子阶段1", "created", parent_id, now, now)
        )
        conn.commit()
        conn.close()

        # 验证子里程碑
        child_response = self.client.get(f"/api/v1/milestones/{child_id}",
                                        headers=headers)
        child_data = self.assert_success_response(child_response)
        self.assertEqual(child_data["data"]["parent_id"], parent_id)

    def test_nested_milestones_hierarchy(self):
        """测试多层嵌套里程碑"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "嵌套里程碑测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建三级里程碑
        from main import get_db, generate_id
        from datetime import datetime
        conn = get_db()
        now = datetime.now().isoformat()

        # 第一级
        level1_id = generate_id()
        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (level1_id, project_id, "milestone", "第一级", "created", now, now)
        )

        # 第二级
        level2_id = generate_id()
        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, parent_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (level2_id, project_id, "milestone", "第二级", "created", level1_id, now, now)
        )

        # 第三级
        level3_id = generate_id()
        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, parent_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (level3_id, project_id, "milestone", "第三级", "created", level2_id, now, now)
        )

        conn.commit()
        conn.close()

        # 验证层级关系
        level3_response = self.client.get(f"/api/v1/milestones/{level3_id}",
                                        headers=headers)
        level3_data = self.assert_success_response(level3_response)
        self.assertEqual(level3_data["data"]["parent_id"], level2_id)


if __name__ == "__main__":
    unittest.main()
