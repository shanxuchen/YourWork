"""
项目归档功能 - 系统级流程测试
测试完整的归档生命周期场景
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test.test_base import TestBase


class TestProjectArchiveLifecycle(TestBase):
    """项目归档生命周期系统测试"""

    def setUp(self):
        """测试前设置"""
        super().setUp()
        # 使用headers传递cookie（通过Cookie头）
        self.admin_headers = self.get_auth_headers("admin", "admin123")
        self.manager_headers = self.get_auth_headers("manager", "manager123")
        self.worker_headers = self.get_auth_headers("worker", "worker123")

    def test_complete_archive_lifecycle(self):
        """测试完整的归档生命周期流程

        场景：
        1. 管理员创建项目
        2. 添加成员和里程碑
        3. 上传产出物
        4. 完成所有任务
        5. 归档项目
        6. 验证数据保留
        7. 取消归档
        8. 恢复工作
        """
        # 步骤1: 创建项目
        project_response = self.client.post(
            "/api/v1/projects",
            json={
                "name": "完整生命周期测试项目",
                "description": "用于测试归档全流程"
            },
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()['data']['id']

        # 步骤2: 添加项目成员
        member_response = self.client.post(
            f"/api/v1/projects/{project_id}/members",
            json={
                "user_id": self.get_user_id("test_worker"),
                "display_name": "测试员工",
                "roles": ["WORKER"]
            },
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(member_response.status_code, 200)

        # 步骤3: 创建里程碑
        milestone_response = self.client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "name": "第一阶段",
                "type": "milestone",
                "description": "项目第一阶段",
                "deadline": "2024-12-31T23:59:59"
            },
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(milestone_response.status_code, 200)
        milestone_id = milestone_response.json()['data']['id']

        # 步骤4: 完成里程碑
        self.client.put(
            f"/api/v1/milestones/{milestone_id}",
            json={"status": "completed"},
            cookies={"session_token": self.admin_headers}
        )

        # 步骤5: 更新项目状态为已完成
        self.client.put(
            f"/api/v1/projects/{project_id}/status",
            json={"status": "completed"},
            cookies={"session_token": self.admin_headers}
        )

        # 步骤6: 归档项目
        archive_response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(archive_response.status_code, 200)
        archive_data = archive_response.json()
        self.assertEqual(archive_data['code'], 0)
        self.assertEqual(archive_data['data']['status'], 'archived')

        # 步骤7: 验证归档后数据保留
        # 检查项目详情
        project_detail = self.client.get(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(project_detail.json()['data']['status'], 'archived')

        # 检查里程碑仍存在
        milestone_detail = self.client.get(
            f"/api/v1/milestones/{milestone_id}",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(milestone_detail.json()['code'], 0)

        # 检查项目成员仍存在
        members = self.client.get(
            f"/api/v1/projects/{project_id}/members",
            cookies={"session_token": self.admin_headers}
        )
        self.assertGreater(len(members.json()['data']), 0)

        # 步骤8: 验证归档项目不在默认列表
        project_list = self.client.get(
            "/api/v1/projects",
            cookies={"session_token": self.admin_headers}
        )
        items = project_list.json()['data']['items']
        project_ids = [p['id'] for p in items]
        self.assertNotIn(project_id, project_ids)

        # 步骤9: 显式查询归档项目
        archived_list = self.client.get(
            "/api/v1/projects?status=archived",
            cookies={"session_token": self.admin_headers}
        )
        archived_items = archived_list.json()['data']['items']
        archived_ids = [p['id'] for p in archived_items]
        self.assertIn(project_id, archived_ids)

        # 步骤10: 取消归档
        unarchive_response = self.client.put(
            f"/api/v1/projects/{project_id}/unarchive",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(unarchive_response.status_code, 200)
        unarchive_data = unarchive_response.json()
        self.assertEqual(unarchive_data['data']['status'], 'in_progress')

        # 步骤11: 验证项目恢复后可正常操作
        project_list_after = self.client.get(
            "/api/v1/projects",
            cookies={"session_token": self.admin_headers}
        )
        items_after = project_list_after.json()['data']['items']
        project_ids_after = [p['id'] for p in items_after]
        self.assertIn(project_id, project_ids_after)

        # 步骤12: 恢复工作 - 创建新里程碑
        new_milestone = self.client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "name": "第二阶段",
                "type": "milestone",
                "description": "项目恢复后的新阶段"
            },
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(new_milestone.status_code, 200)

    def test_archive_with_active_milestones(self):
        """测试归档有进行中里程碑的项目"""
        project_id = self.create_test_project("活跃里程碑项目")

        # 创建进行中的里程碑
        milestone_response = self.client.post(
            f"/api/v1/projects/{project_id}/milestones",
            json={
                "name": "进行中的里程碑",
                "type": "milestone",
                "status": "in_progress"
            },
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(milestone_response.status_code, 200)

        # 归档项目（应该允许）
        archive_response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(archive_response.json()['code'], 0)

        # 验证里程碑状态保持不变
        milestones = self.client.get(
            f"/api/v1/projects/{project_id}/milestones",
            cookies={"session_token": self.admin_headers}
        )
        milestone_data = milestones.json()['data']['items'][0]
        self.assertEqual(milestone_data['status'], 'in_progress')

    def test_batch_archive_projects(self):
        """测试批量归档多个项目"""
        project_ids = []

        # 创建多个已完成的项目
        for i in range(3):
            project_id = self.create_test_project(f"批量归档项目{i+1}")
            project_ids.append(project_id)

            # 标记为已完成
            self.client.put(
                f"/api/v1/projects/{project_id}/status",
                json={"status": "completed"},
                cookies={"session_token": self.admin_headers}
            )

        # 批量归档
        archived_count = 0
        for project_id in project_ids:
            response = self.client.delete(
                f"/api/v1/projects/{project_id}",
                cookies={"session_token": self.admin_headers}
            )
            if response.json()['code'] == 0:
                archived_count += 1

        self.assertEqual(archived_count, 3)

        # 验证所有项目已归档
        archived_list = self.client.get(
            "/api/v1/projects?status=archived",
            cookies={"session_token": self.admin_headers}
        )
        archived_items = archived_list.json()['data']['items']
        archived_ids = [p['id'] for p in archived_items]

        for project_id in project_ids:
            self.assertIn(project_id, archived_ids)

    def test_archive_permission_scenarios(self):
        """测试不同角色的归档权限场景"""
        project_id = self.create_test_project("权限测试项目")

        # 场景1: SYSTEM_ADMIN可以归档
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.admin_headers}
        )
        self.assertEqual(response.json()['code'], 0)

        # 取消归档用于后续测试
        self.client.put(
            f"/api/v1/projects/{project_id}/unarchive",
            cookies={"session_token": self.admin_headers}
        )

        # 场景2: ADMIN可以归档
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.manager_headers}
        )
        self.assertEqual(response.json()['code'], 0)

        # 取消归档用于后续测试
        self.client.put(
            f"/api/v1/projects/{project_id}/unarchive",
            cookies={"session_token": self.admin_headers}
        )

        # 场景3: WORKER不能归档
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            cookies={"session_token": self.worker_headers}
        )
        self.assertEqual(response.json()['code'], 403)

        # 场景4: 未登录用户不能归档
        response = self.client.delete(f"/api/v1/projects/{project_id}")
        self.assertEqual(response.json()['code'], 401)

    def test_archive_search_and_filter(self):
        """测试归档项目的搜索和过滤功能"""
        # 创建不同状态的项目
        for status in ['in_progress', 'completed', 'archived', 'ignored']:
            self.create_test_project(f"{status}项目")

        # 将其中一个项目归档
        response = self.client.get("/api/v1/projects", cookies={"session_token": self.admin_headers})
        for project in response.json()['data']['items']:
            if 'archived' in project['name']:
                self.client.delete(
                    f"/api/v1/projects/{project['id']}",
                    cookies={"session_token": self.admin_headers}
                )
                break

        # 测试1: 默认列表不包含归档项目
        default_list = self.client.get(
            "/api/v1/projects",
            cookies={"session_token": self.admin_headers}
        )
        items = default_list.json()['data']['items']
        for item in items:
            self.assertNotEqual(item['status'], 'archived')

        # 测试2: 按状态过滤
        archived_only = self.client.get(
            "/api/v1/projects?status=archived",
            cookies={"session_token": self.admin_headers}
        )
        self.assertGreater(len(archived_only.json()['data']['items']), 0)

        # 测试3: 关键词搜索（包括归档项目）
        keyword_search = self.client.get(
            "/api/v1/projects?keyword=archived&status=archived",
            cookies={"session_token": self.admin_headers}
        )
        self.assertGreater(len(keyword_search.json()['data']['items']), 0)

    # 辅助方法
    def create_test_project(self, name):
        """创建测试项目"""
        response = self.client.post(
            "/api/v1/projects",
            json={"name": name, "description": "测试项目"},
            cookies={"session_token": self.admin_headers}
        )
        return response.json()['data']['id']

    def get_user_id(self, username):
        """获取用户ID"""
        # 从test_base创建的测试用户中获取
        from main import get_db
        conn = get_db()
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result['id'] if result else None


if __name__ == '__main__':
    unittest.main()
