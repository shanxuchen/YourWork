"""
YourWork - 端到端系统测试
测试完整的业务流程和用户场景
"""

import unittest
import time

from test.test_base import APITestBase
from test.test_data_generator import random_user, random_project


class TestCompleteProjectLifecycle(APITestBase):
    """测试项目从创建到完成的完整生命周期"""

    def test_project_from_start_to_finish(self):
        """测试项目从开始到完成的完整流程"""
        admin_headers = self.get_auth_headers("admin", "admin123")
        manager_headers = self.get_auth_headers("manager", "manager123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        print("\n[端到端测试] 项目完整生命周期")

        # ===== 阶段1: 项目初始化 =====
        print("[1/8] 创建项目...")
        project_response = self.client.post("/api/v1/projects",
                                          json={
                                              "name": "企业级CRM系统",
                                              "description": "开发一套完整的客户关系管理系统"
                                          },
                                          headers=admin_headers)
        project_data = self.assert_success_response(project_response)
        project_id = project_data["data"]["project_id"]
        print(f"      项目创建成功: {project_data['data']['project_no']}")

        # ===== 阶段2: 组建团队 =====
        print("[2/8] 添加项目成员...")
        manager_id = self.get_user_id("manager")
        worker_id = self.get_user_id("worker")

        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={
                            "user_id": manager_id,
                            "display_name": "项目经理",
                            "roles": ["项目管理"]
                        },
                        headers=admin_headers)

        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={
                            "user_id": worker_id,
                            "display_name": "开发工程师",
                            "roles": ["开发"]
                        },
                        headers=admin_headers)
        print("      团队组建完成")

        # ===== 阶段3: 创建里程碑 =====
        print("[3/8] 创建项目里程碑...")
        milestones = [
            {"name": "需求分析", "description": "完成详细需求文档", "days": 7},
            {"name": "系统设计", "description": "完成系统架构设计", "days": 14},
            {"name": "开发实现", "description": "完成核心功能开发", "days": 30},
            {"name": "测试验收", "description": "完成系统测试", "days": 45},
            {"name": "上线部署", "description": "生产环境部署", "days": 50}
        ]

        created_milestones = []
        for ms in milestones:
            response = self.client.post("/api/v1/milestones",
                                       json={
                                           "project_id": project_id,
                                           "name": ms["name"],
                                           "description": ms["description"],
                                           "type": "milestone"
                                       },
                                       headers=admin_headers)
            data = self.assert_success_response(response)
            created_milestones.append(data["data"]["milestone_id"])
        print(f"      创建了 {len(created_milestones)} 个里程碑")

        # ===== 阶段4: 开始第一个里程碑 =====
        print("[4/8] 启动需求分析阶段...")
        self.client.put(f"/api/v1/milestones/{created_milestones[0]}",
                       json={"status": "waiting"},
                       headers=admin_headers)

        # 添加操作日志
        self.client.post(f"/api/v1/milestones/{created_milestones[0]}/logs",
                        json={
                            "action": "开始需求调研",
                            "description": "与业务部门进行需求访谈"
                        },
                        headers=admin_headers)
        print("      需求分析阶段启动")

        # ===== 阶段5: 完成需求分析 =====
        print("[5/8] 完成需求分析...")
        self.client.put(f"/api/v1/milestones/{created_milestones[0]}",
                       json={"status": "completed"},
                       headers=admin_headers)

        # 上传需求文档
        from io import BytesIO
        doc_content = b"PRD - CRM System Requirements"
        files = {"file": ("PRD.docx", BytesIO(doc_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        self.client.post(f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={created_milestones[0]}",
                        files=files,
                        headers=admin_headers)
        print("      需求分析完成，产出物已上传")

        # ===== 阶段6: 进行系统设计 =====
        print("[6/8] 进行系统设计...")
        self.client.put(f"/api/v1/milestones/{created_milestones[1]}",
                       json={"status": "waiting"},
                       headers=admin_headers)

        self.client.put(f"/api/v1/milestones/{created_milestones[1]}",
                       json={"status": "completed"},
                       headers=admin_headers)

        # 上传设计文档
        design_content = b"System Architecture Design"
        design_files = {"file": ("Design.docx", BytesIO(design_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        self.client.post(f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={created_milestones[1]}",
                        files=design_files,
                        headers=admin_headers)
        print("      系统设计完成")

        # ===== 阶段7: 项目进度检查 =====
        print("[7/8] 检查项目进度...")
        project_detail = self.client.get(f"/api/v1/projects/{project_id}",
                                        headers=admin_headers)
        detail_data = self.assert_success_response(project_detail)

        completed_count = sum(1 for ms in detail_data["data"]["milestones"]
                             if ms["status"] == "completed")
        total_count = len(detail_data["data"]["milestones"])
        progress = (completed_count / total_count * 100) if total_count > 0 else 0
        print(f"      项目进度: {completed_count}/{total_count} ({progress:.1f}%)")

        # ===== 阶段8: 项目完成 =====
        print("[8/8] 完成所有里程碑...")
        for milestone_id in created_milestones[2:]:  # 完成剩余里程碑
            self.client.put(f"/api/v1/milestones/{milestone_id}",
                           json={"status": "completed"},
                           headers=admin_headers)

        # 更新项目状态为已完成
        self.client.put(f"/api/v1/projects/{project_id}/status",
                       json={"status": "completed"},
                       headers=admin_headers)

        # 验证最终状态
        final_project = self.client.get(f"/api/v1/projects/{project_id}",
                                       headers=admin_headers)
        final_data = self.assert_success_response(final_project)
        self.assertEqual(final_data["data"]["project"]["status"], "completed")
        print("      项目已完成！")

        print("[端到端测试] 测试通过")


class TestNewUserOnboardingFlow(APITestBase):
    """测试新用户入职流程"""

    def test_new_user_registration_and_first_project(self):
        """测试新用户注册到参与第一个项目的完整流程"""
        print("\n[端到端测试] 新用户入职流程")

        # ===== 步骤1: 用户注册 =====
        print("[1/5] 新用户注册...")
        new_user = random_user()
        register_response = self.client.post("/api/v1/auth/register",
                                           json={
                                               "username": new_user["username"],
                                               "password": new_user["password"],
                                               "display_name": new_user["display_name"],
                                               "email": new_user["email"]
                                           })
        self.assert_success_response(register_response)
        print(f"      用户 {new_user['display_name']} 注册成功")

        # ===== 步骤2: 用户登录 =====
        print("[2/5] 用户登录...")
        login_response = self.client.post("/api/v1/auth/login",
                                         json={
                                             "username": new_user["username"],
                                             "password": new_user["password"]
                                         })
        login_data = self.assert_success_response(login_response)
        user_token = login_data["data"]["id"]
        user_headers = {"Cookie": f"token={user_token}"}
        print("      登录成功")

        # ===== 步骤3: 查看仪表盘 =====
        print("[3/5] 查看仪表盘...")
        dashboard_response = self.client.get("/", headers=user_headers)
        self.assertEqual(dashboard_response.status_code, 200)
        print("      仪表盘加载成功")

        # 获取统计数据
        projects_response = self.client.get("/api/v1/projects", headers=user_headers)
        projects_data = projects_response.json()
        # 新用户应该没有项目
        print(f"      当前项目数: {projects_data['data']['total'] if projects_data['code'] == 0 else 0}")

        # ===== 步骤4: 管理员添加用户到项目 =====
        print("[4/5] 被添加到项目...")
        admin_headers = self.get_auth_headers("admin", "admin123")

        # 创建项目
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "新员工培训项目"},
                                          headers=admin_headers)
        project_id = project_response.json()["data"]["project_id"]

        # 获取新用户ID
        profile_response = self.client.get("/api/v1/auth/profile", headers=user_headers)
        new_user_id = profile_response.json()["data"]["id"]

        # 添加到项目
        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={
                            "user_id": new_user_id,
                            "display_name": new_user["display_name"]
                        },
                        headers=admin_headers)
        print("      已添加到项目")

        # ===== 步骤5: 用户访问项目 =====
        print("[5/5] 访问项目...")
        project_detail_response = self.client.get(f"/api/v1/projects/{project_id}",
                                                 headers=user_headers)
        self.assert_success_response(project_detail_response)
        print("      成功访问项目")

        print("[端到端测试] 测试通过")


class TestMultiProjectManagementFlow(APITestBase):
    """测试多项目管理流程"""

    def test_manage_multiple_projects_concurrently(self):
        """测试同时管理多个项目"""
        print("\n[端到端测试] 多项目管理流程")

        admin_headers = self.get_auth_headers("admin", "admin123")

        # ===== 创建多个项目 =====
        print("[1/4] 创建多个项目...")
        projects = []
        project_names = ["CRM系统", "ERP系统", "OA系统", "BI系统"]

        for name in project_names:
            response = self.client.post("/api/v1/projects",
                                      json={"name": name, "description": f"{name}开发项目"},
                                      headers=admin_headers)
            data = self.assert_success_response(response)
            projects.append({
                "id": data["data"]["project_id"],
                "name": name
            })
        print(f"      创建了 {len(projects)} 个项目")

        # ===== 为每个项目创建里程碑 =====
        print("[2/4] 为各项目创建里程碑...")
        for project in projects:
            response = self.client.post("/api/v1/milestones",
                                      json={
                                          "project_id": project["id"],
                                          "name": f"{project['name']}-第一阶段",
                                          "type": "milestone"
                                      },
                                      headers=admin_headers)
            self.assert_success_response(response)
        print("      里程碑创建完成")

        # ===== 查看所有项目概览 =====
        print("[3/4] 查看项目概览...")
        all_projects_response = self.client.get("/api/v1/projects?status=in_progress",
                                              headers=admin_headers)
        all_projects_data = self.assert_success_response(all_projects_response)
        print(f"      进行中的项目: {len(all_projects_data['data']['items'])} 个")

        # ===== 统计管理 =====
        print("[4/4] 项目统计...")
        total_milestones = 0
        for project in projects:
            detail_response = self.client.get(f"/api/v1/projects/{project['id']}",
                                             headers=admin_headers)
            detail_data = self.assert_success_response(detail_response)
            total_milestones += len(detail_data["data"]["milestones"])
        print(f"      总里程碑数: {total_milestones}")

        print("[端到端测试] 测试通过")


class TestProjectCollaborationFlow(APITestBase):
    """测试项目协作流程"""

    def test_team_collaboration_on_project(self):
        """测试团队协作完成项目"""
        print("\n[端到端测试] 团队协作流程")

        admin_headers = self.get_auth_headers("admin", "admin123")
        manager_headers = self.get_auth_headers("manager", "manager123")
        worker_headers = self.get_auth_headers("worker", "worker123")

        # ===== 管理员创建项目 =====
        print("[1/6] 管理员创建项目...")
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "团队协作项目"},
                                          headers=admin_headers)
        project_id = project_response.json()["data"]["project_id"]
        print("      项目创建成功")

        # ===== 经理创建工作计划 =====
        print("[2/6] 经理创建工作计划...")
        manager_id = self.get_user_id("manager")
        worker_id = self.get_user_id("worker")

        # 添加团队成员
        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": worker_id, "display_name": "开发人员"},
                        headers=admin_headers)

        # 经理创建里程碑
        for i in range(3):
            self.client.post("/api/v1/milestones",
                           json={
                               "project_id": project_id,
                               "name": f"任务{i+1}",
                               "description": f"第{i+1}个任务",
                               "type": "milestone"
                           },
                           headers=manager_headers)
        print("      工作计划创建完成")

        # ===== 员工领取任务 =====
        print("[3/6] 员工查看并领取任务...")
        milestones_response = self.client.get(f"/api/v1/projects/{project_id}/milestones",
                                             headers=worker_headers)
        milestones_data = self.assert_success_response(milestones_response)
        print(f"      找到 {len(milestones_data['data'])} 个任务")

        # 员工开始第一个任务
        first_milestone_id = milestones_data["data"][0]["id"]
        self.client.put(f"/api/v1/milestones/{first_milestone_id}",
                       json={"status": "waiting"},
                       headers=worker_headers)
        print("      任务已领取")

        # ===== 员工提交工作成果 =====
        print("[4/6] 员工提交工作成果...")
        from io import BytesIO
        work_content = b"Work deliverable content"
        files = {"file": ("work.txt", BytesIO(work_content), "text/plain")}
        self.client.post(f"/api/v1/projects/{project_id}/deliverables/upload?milestone_id={first_milestone_id}",
                        files=files,
                        headers=worker_headers)

        self.client.put(f"/api/v1/milestones/{first_milestone_id}",
                       json={"status": "completed"},
                       headers=worker_headers)
        print("      工作已提交")

        # ===== 经理审核 =====
        print("[5/6] 经理审核工作...")
        milestone_detail = self.client.get(f"/api/v1/milestones/{first_milestone_id}",
                                          headers=manager_headers)
        detail_data = self.assert_success_response(milestone_detail)
        self.assertEqual(detail_data["data"]["status"], "completed")
        print("      审核通过")

        # ===== 查看协作记录 =====
        print("[6/6] 查看协作记录...")
        logs_response = self.client.get(f"/api/v1/milestones/{first_milestone_id}/logs",
                                       headers=manager_headers)
        logs_data = self.assert_success_response(logs_response)
        print(f"      协作记录: {len(logs_data['data'])} 条")

        print("[端到端测试] 测试通过")


class TestProjectHandoverFlow(APITestBase):
    """测试项目交接流程"""

    def test_project_handover_between_users(self):
        """测试项目在不同用户间交接"""
        print("\n[端到端测试] 项目交接流程")

        admin_headers = self.get_auth_headers("admin", "admin123")
        manager_headers = self.get_auth_headers("manager", "manager123")

        # ===== 管理员创建项目 =====
        print("[1/4] 管理员创建项目...")
        project_response = self.client.post("/api/v1/projects",
                                          json={"name": "待交接项目"},
                                          headers=admin_headers)
        project_id = project_response.json()["data"]["project_id"]
        print("      项目创建成功")

        # ===== 添加初始成员 =====
        print("[2/4] 添加初始成员...")
        worker_id = self.get_user_id("worker")
        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": worker_id, "display_name": "原负责人"},
                        headers=admin_headers)
        print("      成员已添加")

        # ===== 移除原成员，添加新成员 =====
        print("[3/4] 执行交接...")
        self.client.delete(f"/api/v1/projects/{project_id}/members/{worker_id}",
                         headers=admin_headers)

        new_user = random_user()
        self.client.post("/api/v1/auth/register",
                        json={
                            "username": new_user["username"],
                            "password": new_user["password"],
                            "display_name": new_user["display_name"]
                        })
        new_login = self.client.post("/api/v1/auth/login",
                                    json={"username": new_user["username"], "password": new_user["password"]})
        new_user_id = new_login.json()["data"]["id"]

        self.client.post(f"/api/v1/projects/{project_id}/members",
                        json={"user_id": new_user_id, "display_name": "新负责人"},
                        headers=admin_headers)
        print("      交接完成")

        # ===== 验证新成员可以访问 =====
        print("[4/4] 验证交接结果...")
        new_user_headers = {"Cookie": f"token={new_user_id}"}
        access_response = self.client.get(f"/api/v1/projects/{project_id}",
                                        headers=new_user_headers)
        self.assert_success_response(access_response)
        print("      新成员可以访问项目")

        print("[端到端测试] 测试通过")


if __name__ == "__main__":
    unittest.main()
