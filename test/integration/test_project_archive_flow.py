"""
项目归档功能 - 集成测试
测试归档相关的API接口
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test.test_base import TestBase


class TestProjectArchiveAPI(TestBase):
    """项目归档API集成测试"""

    def setUp(self):
        """每个测试前的设置"""
        super().setUp()
        # 以管理员身份登录（使用headers传递cookie）
        self.admin_headers = self.get_auth_headers("admin", "admin123")
        self.manager_headers = self.get_auth_headers("manager", "manager123")
        self.worker_headers = self.get_auth_headers("worker", "worker123")

    def test_archive_project_api(self):
        """测试归档项目API"""
        # 创建测试项目
        project_id = self.create_test_project("待归档项目")

        # 归档项目
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 0)
        self.assertEqual(data['data']['status'], 'archived')

    def test_archive_nonexistent_project(self):
        """测试归档不存在的项目"""
        response = self.client.delete(
            "/api/v1/projects/nonexistent-id",
            headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 404)
        self.assertIn('不存在', data['message'])

    def test_archive_already_archived_project(self):
        """测试归档已归档的项目"""
        # 创建并归档项目
        project_id = self.create_test_project("重复归档测试")
        self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )

        # 再次尝试归档
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 400)
        self.assertIn('已经是归档', data['message'])

    def test_unarchive_project_api(self):
        """测试取消归档API"""
        # 创建并归档项目
        project_id = self.create_test_project("取消归档测试")
        self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )

        # 取消归档
        response = self.client.put(
            f"/api/v1/projects/{project_id}/unarchive",
            headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 0)
        self.assertEqual(data['data']['status'], 'in_progress')

    def test_unarchive_nonexistent_project(self):
        """测试取消归档不存在的项目"""
        response = self.client.put(
            "/api/v1/projects/nonexistent-id/unarchive",
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 404)

    def test_unarchive_non_archived_project(self):
        """测试取消归档非归档状态的项目"""
        project_id = self.create_test_project("进行中项目")

        response = self.client.put(
            f"/api/v1/projects/{project_id}/unarchive",
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 400)
        self.assertIn('只有归档状态', data['message'])

    def test_project_list_excludes_archived_by_default(self):
        """测试项目列表默认排除归档项目"""
        # 创建不同状态的项目
        for status in ['in_progress', 'completed', 'archived']:
            self.create_test_project(f"{status}_项目")

        # 获取项目列表（默认）
        response = self.client.get(
            "/api/v1/projects",
            headers=self.admin_headers
        )

        data = response.json()
        projects = data['data']['items']
        statuses = [p['status'] for p in projects]

        # 验证归档项目不在列表中
        self.assertNotIn('archived', statuses)

    def test_project_list_with_archived_filter(self):
        """测试显式查询归档项目"""
        # 创建归档项目
        self.create_test_project("归档项目1")
        self.create_test_project("归档项目2")

        # 归档这两个项目
        response = self.client.get("/api/v1/projects", headers=self.admin_headers)
        projects = response.json()['data']['items']
        for project in projects:
            if '归档' in project['name']:
                self.client.delete(
                    f"/api/v1/projects/{project['id']}",
                    headers=self.admin_headers
                )

        # 显式查询归档项目
        response = self.client.get(
            "/api/v1/projects?status=archived",
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 0)
        self.assertGreater(len(data['data']['items']), 0)

    def test_worker_cannot_archive(self):
        """测试普通员工无权归档项目"""
        project_id = self.create_test_project("员工归档测试")

        # 尝试归档
        response = self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.worker_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 403)
        self.assertIn('无权限', data['message'])

    def test_archived_project_data_accessible(self):
        """测试归档后数据仍可访问"""
        # 创建项目并添加数据
        project_id = self.create_test_project("数据访问测试")

        # 添加里程碑（使用正确的API端点）
        response = self.client.post(
            "/api/v1/milestones",
            json={
                "project_id": project_id,
                "name": "测试里程碑",
                "type": "milestone",
                "description": "测试"
            },
            headers=self.admin_headers
        )
        milestone_id = response.json()['data']['milestone_id']

        # 归档项目
        self.client.delete(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )

        # 验证里程碑仍可查询
        response = self.client.get(
            f"/api/v1/milestones/{milestone_id}",
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 0)
        self.assertEqual(data['data']['name'], "测试里程碑")

    def test_update_status_to_archived(self):
        """测试通过状态更新接口归档项目"""
        project_id = self.create_test_project("状态更新归档")

        response = self.client.put(
            f"/api/v1/projects/{project_id}/status",
            json={"status": "archived"},
            headers=self.admin_headers
        )

        data = response.json()
        self.assertEqual(data['code'], 0)

        # 验证状态（项目详情API返回结构是 data.project.status）
        response = self.client.get(
            f"/api/v1/projects/{project_id}",
            headers=self.admin_headers
        )
        project = response.json()['data']
        self.assertEqual(project['project']['status'], 'archived')

    # 辅助方法
    def create_test_project(self, name):
        """创建测试项目"""
        response = self.client.post(
            "/api/v1/projects",
            json={
                "name": name,
                "description": "测试项目"
            },
            headers=self.admin_headers
        )
        return response.json()['data']['project_id']


if __name__ == '__main__':
    unittest.main()
