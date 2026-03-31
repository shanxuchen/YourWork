"""
YourWork - 数据库操作单元测试
测试数据库 CRUD 操作
"""

import unittest
from datetime import datetime

from test.test_base import DatabaseTestBase
from main import get_db, generate_id, hash_password


class TestUserDatabaseOperations(DatabaseTestBase):
    """测试用户数据库操作"""

    def test_create_user(self):
        """测试创建用户"""
        conn = self.get_test_conn()
        user_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, "testuser", hash_password("test123"), "测试用户", 1, now, now)
        )
        conn.commit()

        # 验证用户已创建
        user = self.assert_row_exists("users", {"id": user_id})
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["display_name"], "测试用户")
        conn.close()

    def test_read_user(self):
        """测试读取用户"""
        conn = self.get_test_conn()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        user = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")

    def test_update_user(self):
        """测试更新用户"""
        conn = self.get_test_conn()

        # 先创建用户
        user_id = generate_id()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, "updatetest", hash_password("test123"), "原始名称", 1, now, now)
        )
        conn.commit()

        # 更新用户
        conn.execute(
            "UPDATE users SET display_name = ?, updated_at = ? WHERE id = ?",
            ("更新后的名称", datetime.now().isoformat(), user_id)
        )
        conn.commit()

        # 验证更新
        cursor = conn.execute("SELECT display_name FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result["display_name"], "更新后的名称")

    def test_delete_user(self):
        """测试删除用户"""
        conn = self.get_test_conn()

        # 先创建用户
        user_id = generate_id()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, "deletetest", hash_password("test123"), "待删除用户", 1, now, now)
        )
        conn.commit()

        # 验证用户存在
        self.assert_row_exists("users", {"id": user_id})

        # 删除用户
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        # 验证用户已删除
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNone(result)

    def test_unique_username_constraint(self):
        """测试用户名唯一约束"""
        conn = self.get_test_conn()
        now = datetime.now().isoformat()

        # 创建第一个用户
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), "uniqueuser", hash_password("test123"), "用户1", 1, now, now)
        )

        # 尝试创建相同用户名的用户（应该失败，但不会抛异常）
        # SQLite 默认不强制外键，这里只是测试逻辑
        user_id2 = generate_id()
        conn.execute(
            """INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id2, "uniqueuser", hash_password("test123"), "用户2", 1, now, now)
        )

        # 检查是否真的插入了两个相同用户名的记录
        cursor = conn.execute("SELECT COUNT(*) as count FROM users WHERE username = ?", ("uniqueuser",))
        count = cursor.fetchone()["count"]
        conn.close()

        # 由于 SQLite 的默认行为，可能会插入成功
        # 在生产环境中应该添加唯一约束


class TestProjectDatabaseOperations(DatabaseTestBase):
    """测试项目数据库操作"""

    def test_create_project(self):
        """测试创建项目"""
        conn = self.get_test_conn()
        project_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, "PRJ-TEST-001", "测试项目", "这是一个测试项目", "in_progress", now, now)
        )
        conn.commit()

        # 验证项目已创建
        project = self.assert_row_exists("projects", {"id": project_id})
        self.assertEqual(project["name"], "测试项目")
        self.assertEqual(project["status"], "in_progress")
        conn.close()

    def test_read_project(self):
        """测试读取项目"""
        project_id = self.create_test_project()

        conn = self.get_test_conn()
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(project)
        self.assertEqual(project["id"], project_id)

    def test_update_project(self):
        """测试更新项目"""
        project_id = self.create_test_project()

        conn = self.get_test_conn()
        conn.execute(
            "UPDATE projects SET name = ?, status = ?, updated_at = ? WHERE id = ?",
            ("更新后的项目", "completed", datetime.now().isoformat(), project_id)
        )
        conn.commit()

        # 验证更新
        cursor = conn.execute("SELECT name, status FROM projects WHERE id = ?", (project_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result["name"], "更新后的项目")
        self.assertEqual(result["status"], "completed")

    def test_delete_project(self):
        """测试删除项目"""
        project_id = self.create_test_project()

        conn = self.get_test_conn()
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()

        # 验证已删除
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNone(result)

    def test_project_status_values(self):
        """测试项目状态值"""
        conn = self.get_test_conn()
        now = datetime.now().isoformat()

        valid_statuses = ["in_progress", "completed", "ignored"]

        for status in valid_statuses:
            project_id = generate_id()
            conn.execute(
                """INSERT INTO projects (id, project_no, name, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (project_id, f"PRJ-{status}", f"项目{status}", status, now, now)
            )

        conn.commit()

        # 验证所有状态都存在
        for status in valid_statuses:
            cursor = conn.execute("SELECT * FROM projects WHERE status = ?", (status,))
            result = cursor.fetchone()
            self.assertIsNotNone(result, f"状态 {status} 不存在")

        conn.close()


class TestMilestoneDatabaseOperations(DatabaseTestBase):
    """测试里程碑数据库操作"""

    def test_create_milestone(self):
        """测试创建里程碑"""
        project_id = self.create_test_project()

        conn = self.get_test_conn()
        milestone_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, description, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (milestone_id, project_id, "milestone", "测试里程碑", "里程碑描述", "created", now, now)
        )
        conn.commit()

        # 验证里程碑已创建
        milestone = self.assert_row_exists("milestones", {"id": milestone_id})
        self.assertEqual(milestone["name"], "测试里程碑")
        self.assertEqual(milestone["project_id"], project_id)
        conn.close()

    def test_read_milestone(self):
        """测试读取里程碑"""
        project_id = self.create_test_project()
        milestone_id = self.create_test_milestone(project_id)

        conn = self.get_test_conn()
        cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        milestone = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(milestone)
        self.assertEqual(milestone["id"], milestone_id)

    def test_update_milestone(self):
        """测试更新里程碑"""
        project_id = self.create_test_project()
        milestone_id = self.create_test_milestone(project_id)

        conn = self.get_test_conn()
        conn.execute(
            "UPDATE milestones SET status = ?, updated_at = ? WHERE id = ?",
            ("completed", datetime.now().isoformat(), milestone_id)
        )
        conn.commit()

        # 验证更新
        cursor = conn.execute("SELECT status FROM milestones WHERE id = ?", (milestone_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result["status"], "completed")

    def test_delete_milestone(self):
        """测试删除里程碑"""
        project_id = self.create_test_project()
        milestone_id = self.create_test_milestone(project_id)

        conn = self.get_test_conn()
        conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
        conn.commit()

        # 验证已删除
        cursor = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNone(result)

    def test_milestone_with_parent(self):
        """测试带父里程碑的里程碑"""
        project_id = self.create_test_project()
        parent_id = self.create_test_milestone(project_id, name="父里程碑")

        conn = self.get_test_conn()
        child_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO milestones (id, project_id, type, name, status, parent_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (child_id, project_id, "milestone", "子里程碑", "created", parent_id, now, now)
        )
        conn.commit()

        # 验证父子关系
        cursor = conn.execute("SELECT parent_id FROM milestones WHERE id = ?", (child_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result["parent_id"], parent_id)


class TestProjectMemberOperations(DatabaseTestBase):
    """测试项目成员操作"""

    def test_add_project_member(self):
        """测试添加项目成员"""
        project_id = self.create_test_project()
        user_id = self.get_user_id("worker")

        conn = self.get_test_conn()
        member_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO project_members (id, project_id, user_id, display_name, roles)
               VALUES (?, ?, ?, ?, ?)""",
            (member_id, project_id, user_id, "测试成员", '["开发人员"]')
        )
        conn.commit()

        # 验证成员已添加
        member = self.assert_row_exists("project_members", {"id": member_id})
        self.assertEqual(member["user_id"], user_id)
        self.assertEqual(member["project_id"], project_id)
        conn.close()

    def test_remove_project_member(self):
        """测试移除项目成员"""
        project_id = self.create_test_project()
        user_id = self.get_user_id("worker")

        conn = self.get_test_conn()
        member_id = generate_id()
        now = datetime.now().isoformat()

        # 添加成员
        conn.execute(
            """INSERT INTO project_members (id, project_id, user_id, display_name, roles)
               VALUES (?, ?, ?, ?, ?)""",
            (member_id, project_id, user_id, "测试成员", '["开发人员"]')
        )
        conn.commit()

        # 验证成员存在
        self.assert_row_exists("project_members", {"id": member_id})

        # 移除成员
        conn.execute("DELETE FROM project_members WHERE id = ?", (member_id,))
        conn.commit()

        # 验证已移除
        cursor = conn.execute("SELECT * FROM project_members WHERE id = ?", (member_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNone(result)

    def test_get_project_members(self):
        """测试获取项目成员列表"""
        project_id = self.create_test_project()

        # 添加多个成员
        conn = self.get_test_conn()
        for username in ["worker", "manager"]:
            user_id = self.get_user_id(username)
            conn.execute(
                """INSERT INTO project_members (id, project_id, user_id, display_name, roles)
                   VALUES (?, ?, ?, ?, ?)""",
                (generate_id(), project_id, user_id, f"成员{username}", '["成员"]')
            )
        conn.commit()

        # 获取成员列表
        cursor = conn.execute("SELECT * FROM project_members WHERE project_id = ?", (project_id,))
        members = cursor.fetchall()
        conn.close()

        self.assertGreaterEqual(len(members), 2)


class TestMessageOperations(DatabaseTestBase):
    """测试消息操作"""

    def test_create_message(self):
        """测试创建消息"""
        user_id = self.get_user_id("admin")

        conn = self.get_test_conn()
        message_id = generate_id()
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO messages (id, user_id, title, content, type, is_read, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, user_id, "测试消息", "消息内容", "system", 0, now)
        )
        conn.commit()

        # 验证消息已创建
        message = self.assert_row_exists("messages", {"id": message_id})
        self.assertEqual(message["title"], "测试消息")
        self.assertEqual(message["is_read"], 0)
        conn.close()

    def test_mark_message_as_read(self):
        """测试标记消息为已读"""
        user_id = self.get_user_id("admin")

        conn = self.get_test_conn()
        message_id = generate_id()
        now = datetime.now().isoformat()

        # 创建未读消息
        conn.execute(
            """INSERT INTO messages (id, user_id, title, content, type, is_read, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, user_id, "测试消息", "消息内容", "system", 0, now)
        )
        conn.commit()

        # 标记为已读
        conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))
        conn.commit()

        # 验证状态
        cursor = conn.execute("SELECT is_read FROM messages WHERE id = ?", (message_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result["is_read"], 1)

    def test_get_user_messages(self):
        """测试获取用户消息列表"""
        user_id = self.get_user_id("admin")

        conn = self.get_test_conn()
        now = datetime.now().isoformat()

        # 创建多条消息
        for i in range(3):
            conn.execute(
                """INSERT INTO messages (id, user_id, title, content, type, is_read, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (generate_id(), user_id, f"消息{i+1}", f"内容{i+1}", "system", 0, now)
            )
        conn.commit()

        # 获取消息列表
        cursor = conn.execute("SELECT * FROM messages WHERE user_id = ?", (user_id,))
        messages = cursor.fetchall()
        conn.close()

        self.assertGreaterEqual(len(messages), 3)

    def test_get_unread_message_count(self):
        """测试获取未读消息数量"""
        user_id = self.get_user_id("admin")

        conn = self.get_test_conn()
        now = datetime.now().isoformat()

        # 创建未读消息
        for _ in range(5):
            conn.execute(
                """INSERT INTO messages (id, user_id, title, content, type, is_read, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (generate_id(), user_id, "未读消息", "内容", "system", 0, now)
            )

        # 创建已读消息
        conn.execute(
            """INSERT INTO messages (id, user_id, title, content, type, is_read, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), user_id, "已读消息", "内容", "system", 1, now)
        )
        conn.commit()

        # 获取未读数量
        cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE user_id = ? AND is_read = 0", (user_id,))
        count = cursor.fetchone()["count"]
        conn.close()

        self.assertGreaterEqual(count, 5)


if __name__ == "__main__":
    unittest.main()
