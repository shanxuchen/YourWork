"""
YourWork - 项目管理流程集成测试
测试完整的项目管理流程，包括创建、更新、成员管理等
"""

import unittest

from test.test_base import APITestBase
from test.test_data_generator import random_project


class TestProjectLifecycleFlow(APITestBase):
    """测试项目完整生命周期"""

    def test_create_read_update_delete_project_flow(self):
        """测试项目的完整 CRUD 流程"""
        headers = self.get_auth_headers()

        # 1. 创建项目
        create_response = self.client.post("/api/v1/projects",
                                          json={"name": "测试项目", "description": "项目描述"},
                                          headers=headers)
        create_data = self.assert_success_response(create_response, "创建项目失败")
        project_id = create_data["data"]["project_id"]
        self.assertIsNotNone(project_id)

        # 2. 读取项目详情
        read_response = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
        read_data = self.assert_success_response(read_response, "读取项目失败")
        self.assertEqual(read_data["data"]["project"]["name"], "测试项目")
        self.assertEqual(read_data["data"]["project"]["status"], "in_progress")

        # 3. 更新项目
        update_response = self.client.put(f"/api/v1/projects/{project_id}",
                                         json={"name": "更新后的项目", "description": "更新后的描述"},
                                         headers=headers)
        self.assert_success_response(update_response, "更新项目失败")

        # 4. 验证更新
        verify_response = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
        verify_data = self.assert_success_response(verify_response)
        self.assertEqual(verify_data["data"]["project"]["name"], "更新后的项目")

        # 5. 更新项目状态为已完成
        status_response = self.client.put(f"/api/v1/projects/{project_id}/status",
                                         json={"status": "completed"},
                                         headers=headers)
        self.assert_success_response(status_response, "更新状态失败")

        # 6. 验证状态更新
        status_verify_response = self.client.get(f"/api/v1/projects/{project_id}", headers=headers)
        status_verify_data = self.assert_success_response(status_verify_response)
        self.assertEqual(status_verify_data["data"]["project"]["status"], "completed")

    def test_project_list_pagination(self):
        """测试项目列表分页"""
        headers = self.get_auth_headers()

        # 创建多个项目
        for i in range(5):
            self.client.post("/api/v1/projects",
                            json={"name": f"项目{i}", "description": f"描述{i}"},
                            headers=headers)

        # 获取第一页
        page1_response = self.client.get("/api/v1/projects?page=1&page_size=2",
                                        headers=headers)
        page1_data = self.assert_success_response(page1_response)
        self.assertEqual(len(page1_data["data"]["items"]), 2)
        self.assertEqual(page1_data["data"]["page"], 1)
        self.assertGreaterEqual(page1_data["data"]["total"], 5)

        # 获取第二页
        page2_response = self.client.get("/api/v1/projects?page=2&page_size=2",
                                        headers=headers)
        page2_data = self.assert_success_response(page2_response)
        self.assertEqual(len(page2_data["data"]["items"]), 2)
        self.assertEqual(page2_data["data"]["page"], 2)

    def test_project_search_and_filter(self):
        """测试项目搜索和过滤"""
        headers = self.get_auth_headers()

        # 创建不同状态的项目
        self.client.post("/api/v1/projects",
                        json={"name": "进行中的项目", "description": "测试"},
                        headers=headers)

        self.client.post("/api/v1/projects",
                        json={"name": "已完成的项目", "description": "测试"},
                        headers=headers)

        # 更新第二个项目为已完成
        projects_response = self.client.get("/api/v1/projects", headers=headers)
        projects = projects_response.json()["data"]["items"]
        if len(projects) >= 2:
            project_id = projects[1]["id"]
            self.client.put(f"/api/v1/projects/{project_id}/status",
                           json={"status": "completed"},
                           headers=headers)

        # 按状态过滤
        filter_response = self.client.get("/api/v1/projects?status=in_progress",
                                         headers=headers)
        filter_data = self.assert_success_response(filter_response)
        for project in filter_data["data"]["items"]:
            self.assertEqual(project["status"], "in_progress")

        # 按关键词搜索
        search_response = self.client.get("/api/v1/projects?keyword=已完成",
                                        headers=headers)
        search_data = self.assert_success_response(search_response)
        for project in search_data["data"]["items"]:
            self.assertIn("已完成", project["name"])


class TestProjectMemberFlow(APITestBase):
    """测试项目成员管理流程"""

    def test_add_and_remove_project_members(self):
        """测试添加和移除项目成员"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 管理员创建项目
        create_response = self.client.post("/api/v1/projects",
                                          json={"name": "成员测试项目"},
                                          headers=admin_headers)
        project_id = create_response.json()["data"]["project_id"]

        # 添加员工为项目成员
        worker_id = self.get_user_id("worker")
        add_response = self.client.post(f"/api/v1/projects/{project_id}/members",
                                       json={
                                           "user_id": worker_id,
                                           "display_name": "测试员工",
                                           "roles": ["开发人员"]
                                       },
                                       headers=admin_headers)
        self.assert_success_response(add_response, "添加成员失败")

        # 验证成员已添加
        project_response = self.client.get(f"/api/v1/projects/{project_id}",
                                          headers=admin_headers)
        project_data = project_response.json()
        member_ids = [m["user_id"] for m in project_data["data"]["members"]]
        self.assertIn(worker_id, member_ids)

        # 移除成员
        remove_response = self.client.delete(f"/api/v1/projects/{project_id}/members/{worker_id}",
                                           headers=admin_headers)
        self.assert_success_response(remove_response, "移除成员失败")

        # 验证成员已移除
        project_response2 = self.client.get(f"/api/v1/projects/{project_id}",
                                           headers=admin_headers)
        project_data2 = project_response2.json()
        member_ids2 = [m["user_id"] for m in project_data2["data"]["members"]]
        self.assertNotIn(worker_id, member_ids2)

    def test_member_permissions(self):
        """测试成员权限"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # 管理员创建项目
        create_response = self.client.post("/api/v1/projects",
                                          json={"name": "权限测试项目"},
                                          headers=admin_headers)
        project_id = create_response.json()["data"]["project_id"]

        # 员工尝试访问项目（没有成员关系，应该失败）
        access_response = self.client.get(f"/api/v1/projects/{project_id}",
                                         headers=worker_headers)
        access_data = access_response.json()
        # 普通员工不能访问非成员项目
        self.assertEqual(access_data.get("code"), 403)

        # 添加员工为项目成员
        worker_id = self.get_user_id("worker")
        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": worker_id, "display_name": "测试员工"},
                        headers=admin_headers)

        # 现在员工可以访问项目了
        access_response2 = self.client.get(f"/api/v1/projects/{project_id}",
                                          headers=worker_headers)
        access_data2 = self.assert_success_response(access_response2, "成员应该能访问项目")

    def test_multiple_members_collaboration(self):
        """测试多成员协作"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        manager_headers = self.get_auth_headers("manager", "manager123")

        # 创建项目
        create_response = self.client.post("/api/v1/projects",
                                          json={"name": "协作测试项目"},
                                          headers=admin_headers)
        project_id = create_response.json()["data"]["project_id"]

        # 添加多个成员
        manager_id = self.get_user_id("manager")
        worker_id = self.get_user_id("worker")

        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": manager_id, "display_name": "项目经理"},
                        headers=admin_headers)

        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": worker_id, "display_name": "开发人员"},
                        headers=admin_headers)

        # 验证所有成员都能访问项目
        admin_access = self.client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
        self.assert_success_response(admin_access)

        manager_access = self.client.get(f"/api/v1/projects/{project_id}", headers=manager_headers)
        self.assert_success_response(manager_access)


class TestProjectWithMilestonesFlow(APITestBase):
    """测试项目与里程碑的集成流程"""

    def test_project_with_milestones(self):
        """测试创建项目并添加里程碑"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "带里程碑的项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建多个里程碑
        milestone_names = ["需求分析", "系统设计", "开发实现", "测试验收"]
        created_milestones = []

        for name in milestone_names:
            milestone_response = self.client.post("/api/v1/milestones",
                                                 json={
                                                     "project_id": project_id,
                                                     "name": name,
                                                     "description": f"{name}阶段",
                                                     "type": "milestone"
                                                 },
                                                 headers=headers)
            milestone_data = self.assert_success_response(milestone_response, f"创建{name}失败")
            created_milestones.append(milestone_data["data"]["milestone_id"])

        # 获取项目详情，验证里程碑关联
        project_detail_response = self.client.get(f"/api/v1/projects/{project_id}",
                                                 headers=headers)
        project_detail_data = self.assert_success_response(project_detail_response)
        self.assertGreaterEqual(len(project_detail_data["data"]["milestones"]), 4)

    def test_milestone_status_affects_project(self):
        """测试里程碑状态对项目的影响"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "状态测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑",
                                                 "type": "milestone"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 更新里程碑状态
        self.client.put(f"/api/v1/milestones/{milestone_id}",
                       json={"status": "completed", "name": "测试里程碑"},
                       headers=headers)

        # 验证里程碑状态
        milestone_detail = self.client.get(f"/api/v1/milestones/{milestone_id}",
                                          headers=headers)
        milestone_data = self.assert_success_response(milestone_detail)
        self.assertEqual(milestone_data["data"]["status"], "completed")


class TestProjectDeliverablesFlow(APITestBase):
    """测试项目产出物管理流程"""

    def test_upload_deliverable_to_project(self):
        """测试上传项目产出物"""
        headers = self.get_auth_headers()

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "文档测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        # 创建测试文件
        from io import BytesIO
        file_content = b"Test document content"

        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        upload_response = self.client.post(f"/api/v1/projects/{project_id}/deliverables/upload",
                                         files=files,
                                         headers=headers)
        upload_data = self.assert_success_response(upload_response, "上传文件失败")

        # 验证文件已上传
        deliverable_id = upload_data["data"]["deliverable_id"]
        deliverables_response = self.client.get(f"/api/v1/projects/{project_id}/deliverables",
                                               headers=headers)
        deliverables_data = self.assert_success_response(deliverables_response)
        deliverable_ids = [d["id"] for d in deliverables_data["data"]]
        self.assertIn(deliverable_id, deliverable_ids)

    def test_deliverable_associated_with_milestone(self):
        """测试产出物关联到里程碑"""
        headers = self.get_auth_headers()

        # 创建项目和里程碑
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "关联测试项目"},
                                          headers=headers)
        project_id = project_response.json()["data"]["project_id"]

        milestone_response = self.client.post("/api/v1/milestones",
                                             json={
                                                 "project_id": project_id,
                                                 "name": "测试里程碑",
                                                 "type": "milestone"
                                             },
                                             headers=headers)
        milestone_id = milestone_response.json()["data"]["milestone_id"]

        # 上传关联到里程碑的文件
        from io import BytesIO
        file_content = b"Milestone document"

        files = {"file": ("milestone.txt", BytesIO(file_content), "text/plain")}
        upload_response = self.client.post(
            f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={milestone_id}",
            files=files,
            headers=headers)
        self.assert_success_response(upload_response)

        # 获取该里程碑的产出物
        deliverables_response = self.client.get(
            f"/api/v1/projects/{project_id}/deliverables?milestone_id={milestone_id}",
            headers=headers)
        deliverables_data = self.assert_success_response(deliverables_response)
        self.assertGreater(len(deliverables_data["data"]), 0)


if __name__ == "__main__":
    unittest.main()
