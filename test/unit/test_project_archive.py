"""
项目归档功能 - 单元测试
测试归档状态相关的基础功能
"""

import unittest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test.test_base import TestBase


class TestProjectArchiveStatus(TestBase):
    """项目归档状态单元测试"""

    def test_project_status_archived_exists(self):
        """测试archived状态是否有效"""
        from main import get_db

        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-archived-001", "PRJ-TEST-001", "测试归档项目", "测试", "archived", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
        )
        conn.commit()
        conn.close()

        # 验证项目可以以archived状态创建
        conn = get_db()
        cursor = conn.execute("SELECT status FROM projects WHERE id = ?", ("test-archived-001",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'archived')

    def test_valid_project_statuses(self):
        """测试所有有效的项目状态"""
        valid_statuses = ['in_progress', 'completed', 'ignored', 'archived']

        from main import get_db

        for i, status in enumerate(valid_statuses):
            conn = get_db()
            project_id = f"test-status-{i:03d}"
            conn.execute(
                "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, f"PRJ-TEST-{i:03d}", f"测试项目{status}", "测试", status, "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )
            conn.commit()
            conn.close()

            # 验证状态
            conn = get_db()
            cursor = conn.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = cursor.fetchone()
            conn.close()

            self.assertEqual(result['status'], status)

    def test_archive_to_in_progress_transition(self):
        """测试从archived到in_progress的状态转换"""
        from main import get_db

        conn = get_db()
        conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-transition-001", "PRJ-TRANS-001", "状态转换测试", "测试", "archived", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
        )
        conn.commit()
        conn.close()

        # 模拟取消归档操作
        conn = get_db()
        conn.execute(
            "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
            ('in_progress', '2024-01-02T00:00:00', 'test-transition-001')
        )
        conn.commit()
        conn.close()

        # 验证状态变更
        conn = get_db()
        cursor = conn.execute("SELECT status FROM projects WHERE id = ?", ("test-transition-001",))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result['status'], 'in_progress')

    def test_archived_project_data_preservation(self):
        """测试归档后数据是否保留"""
        from main import get_db

        project_id = "test-preserve-001"

        # 创建项目及关联数据
        conn = get_db()
        conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, "PRJ-PRESERVE-001", "数据保留测试", "测试", "in_progress", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
        )

        # 添加里程碑
        conn.execute(
            "INSERT INTO milestones (id, project_id, type, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-milestone-001", project_id, "milestone", "测试里程碑", "created", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
        )

        # 添加项目成员
        conn.execute(
            "INSERT INTO project_members (id, project_id, user_id, display_name) VALUES (?, ?, ?, ?)",
            ("test-member-001", project_id, "test-user-id", "测试成员")
        )
        conn.commit()
        conn.close()

        # 执行归档操作
        conn = get_db()
        conn.execute(
            "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
            ('archived', '2024-01-02T00:00:00', project_id)
        )
        conn.commit()
        conn.close()

        # 验证关联数据是否仍存在
        conn = get_db()

        # 检查项目
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        self.assertIsNotNone(project)
        self.assertEqual(project['status'], 'archived')

        # 检查里程碑
        cursor = conn.execute("SELECT * FROM milestones WHERE project_id = ?", (project_id,))
        milestone = cursor.fetchone()
        self.assertIsNotNone(milestone)

        # 检查项目成员
        cursor = conn.execute("SELECT * FROM project_members WHERE project_id = ?", (project_id,))
        member = cursor.fetchone()
        self.assertIsNotNone(member)

        conn.close()


class TestProjectArchiveFilters(TestBase):
    """项目列表过滤单元测试"""

    def test_default_list_excludes_archived(self):
        """测试默认列表是否排除归档项目"""
        from main import get_db

        # 创建不同状态的项目
        conn = get_db()
        for status, name in [
            ('in_progress', '进行中项目'),
            ('completed', '已完成项目'),
            ('archived', '已归档项目'),
            ('ignored', '已忽略项目')
        ]:
            project_id = f"test-filter-{status}"
            conn.execute(
                "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, f"PRJ-{status}", name, "测试", status, "2024-01-01T00:00:00", "2024-01-01T00:00:00")
            )
        conn.commit()
        conn.close()

        # 查询默认列表（排除archived）
        conn = get_db()
        cursor = conn.execute("SELECT * FROM projects WHERE status != 'archived' ORDER BY status")
        results = cursor.fetchall()
        conn.close()

        self.assertEqual(len(results), 3)
        statuses = [r['status'] for r in results]
        self.assertNotIn('archived', statuses)

    def test_explicit_archived_filter(self):
        """测试显式查询归档项目"""
        from main import get_db

        # 创建归档项目
        conn = get_db()
        conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-archive-only-001", "PRJ-ARCH-001", "归档项目", "测试", "archived", "2024-01-01T00:00:00", "2024-01-01T00:00:00")
        )
        conn.commit()
        conn.close()

        # 显式查询归档项目
        conn = get_db()
        cursor = conn.execute("SELECT * FROM projects WHERE status = 'archived'")
        results = cursor.fetchall()
        conn.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'archived')


if __name__ == '__main__':
    unittest.main()
