"""
YourWork - 测试数据生成器
生成各种测试场景所需的模拟数据
"""

import random
import string
from datetime import datetime, timedelta
from main import generate_id


class TestDataGenerator:
    """测试数据生成器"""

    # 随机字符串池
    CHINESE_CHARS = "项目需求设计开发测试验收里程碑完成进行中挂起文档报告"
    ENGLISH_CHARS = string.ascii_lowercase

    # 常用词汇
    PROJECT_NAMES = [
        "企业级CRM系统", "电商管理平台", "数据分析系统",
        "移动应用开发", "网站重构项目", "API接口开发",
        "内部管理系统", "客户服务系统", "订单管理系统"
    ]

    PROJECT_DESCRIPTIONS = [
        "这是一个综合性的企业级项目",
        "用于提升业务效率的数字化解决方案",
        "针对市场需求的快速响应系统",
        "优化现有业务流程的技术改造项目"
    ]

    MILESTONE_NAMES = [
        "需求分析", "系统设计", "前端开发", "后端开发",
        "数据库设计", "接口对接", "系统测试", "用户验收",
        "上线部署", "项目验收"
    ]

    MILESTONE_DESCRIPTIONS = [
        "完成详细的需求文档",
        "设计系统架构和技术方案",
        "完成前端页面开发",
        "完成后端API开发",
        "设计数据库表结构",
        "完成前后端接口对接",
        "进行全面系统测试",
        "用户验收测试",
        "生产环境部署",
        "项目最终验收"
    ]

    USER_NAMES = [
        "张三", "李四", "王五", "赵六", "钱七",
        "孙八", "周九", "吴十", "郑十一", "王十二"
    ]

    @classmethod
    def random_string(cls, length=10, chars=None):
        """生成随机字符串"""
        if chars is None:
            chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @classmethod
    def random_chinese(cls, length=5):
        """生成随机中文字符串"""
        return ''.join(random.choice(cls.CHINESE_CHARS) for _ in range(length))

    @classmethod
    def random_email(cls, username=None):
        """生成随机邮箱"""
        if username is None:
            username = cls.random_string(8, cls.ENGLISH_CHARS)
        domains = ["test.com", "example.com", "demo.com"]
        return f"{username}@{random.choice(domains)}"

    @classmethod
    def random_phone(cls):
        """生成随机手机号"""
        return f"13{random.randint(0, 9)}{random.randint(10000000, 99999999)}"

    @classmethod
    def random_date(cls, start_days=0, end_days=365):
        """生成随机日期"""
        start = datetime.now() + timedelta(days=start_days)
        end = datetime.now() + timedelta(days=end_days)
        random_days = random.randint(0, (end - start).days)
        return (start + timedelta(days=random_days)).isoformat()

    @classmethod
    def random_project_name(cls):
        """生成随机项目名称"""
        prefix = random.choice(["Q1", "Q2", "Q3", "Q4", "年度", "季度"])
        name = random.choice(cls.PROJECT_NAMES)
        suffix = random.choice(["项目", "系统", "平台", "工程"])
        return f"{prefix}{name}{suffix}"

    @classmethod
    def random_project_description(cls):
        """生成随机项目描述"""
        return random.choice(cls.PROJECT_DESCRIPTIONS)

    @classmethod
    def random_milestone_name(cls):
        """生成随机里程碑名称"""
        prefix = random.choice(["第一阶段", "第二阶段", "第三阶段", "最终"])
        name = random.choice(cls.MILESTONE_NAMES)
        return f"{prefix}-{name}"

    @classmethod
    def random_milestone_description(cls):
        """生成随机里程碑描述"""
        return random.choice(cls.MILESTONE_DESCRIPTIONS)

    @classmethod
    def generate_project_data(cls, **kwargs):
        """生成项目数据"""
        return {
            "name": kwargs.get("name", cls.random_project_name()),
            "description": kwargs.get("description", cls.random_project_description())
        }

    @classmethod
    def generate_milestone_data(cls, project_id, **kwargs):
        """生成里程碑数据"""
        return {
            "project_id": project_id,
            "name": kwargs.get("name", cls.random_milestone_name()),
            "description": kwargs.get("description", cls.random_milestone_description()),
            "type": kwargs.get("type", random.choice(["milestone", "acceptance"])),
            "deadline": kwargs.get("deadline", cls.random_date(7, 180))
        }

    @classmethod
    def generate_user_data(cls, **kwargs):
        """生成用户数据"""
        username = kwargs.get("username") or cls.random_string(8, cls.ENGLISH_CHARS)
        return {
            "username": username,
            "password": kwargs.get("password", "test123456"),
            "display_name": kwargs.get("display_name", random.choice(cls.USER_NAMES)),
            "email": kwargs.get("email", cls.random_email(username))
        }

    @classmethod
    def generate_message_data(cls, user_id, **kwargs):
        """生成消息数据"""
        msg_types = ["system", "project", "milestone", "reminder"]
        titles = {
            "system": ["系统通知", "账户提醒"],
            "project": ["项目更新", "项目状态变更"],
            "milestone": ["里程碑提醒", "里程碑状态更新"],
            "reminder": ["待办提醒", "到期通知"]
        }

        msg_type = kwargs.get("type", random.choice(msg_types))
        return {
            "user_id": user_id,
            "title": kwargs.get("title", random.choice(titles[msg_type])),
            "content": kwargs.get("content", f"这是一条{msg_type}类型的测试消息"),
            "type": msg_type,
            "is_read": kwargs.get("is_read", 0)
        }

    @classmethod
    def generate_batch_projects(cls, count=5):
        """批量生成项目数据"""
        return [cls.generate_project_data() for _ in range(count)]

    @classmethod
    def generate_batch_milestones(cls, project_id, count=3):
        """批量生成里程碑数据"""
        return [cls.generate_milestone_data(project_id) for _ in range(count)]

    @classmethod
    def generate_batch_messages(cls, user_id, count=10):
        """批量生成消息数据"""
        return [cls.generate_message_data(user_id) for _ in range(count)]


class ScenarioDataGenerator:
    """场景数据生成器 - 生成特定测试场景的数据"""

    @classmethod
    def generate_full_project_scenario(cls):
        """生成完整项目场景数据"""
        project = cls.generate_project_data()

        # 生成项目里程碑
        milestones = []
        milestone_types = [
            ("milestone", "需求分析", "完成详细的需求文档", 7),
            ("milestone", "系统设计", "设计系统架构", 14),
            ("milestone", "开发阶段", "完成功能开发", 60),
            ("acceptance", "第一阶段验收", "完成功能验收", 70),
            ("milestone", "测试阶段", "完成系统测试", 85),
            ("acceptance", "最终验收", "项目交付验收", 90)
        ]

        for i, (m_type, name, desc, days) in enumerate(milestone_types):
            milestones.append({
                "type": m_type,
                "name": f"{i+1}.{name}",
                "description": desc,
                "deadline": cls.random_date(days, days+7)
            })

        return {
            "project": project,
            "milestones": milestones
        }

    @classmethod
    def generate_overdue_scenario(cls):
        """生成逾期项目场景"""
        return {
            "project": {
                "name": "紧急项目-已逾期",
                "description": "这是一个已经逾期的紧急项目"
            },
            "milestones": [
                {
                    "type": "milestone",
                    "name": "已逾期的里程碑",
                    "description": "这个里程碑已经逾期",
                    "deadline": (datetime.now() - timedelta(days=10)).isoformat()
                },
                {
                    "type": "milestone",
                    "name": "即将逾期的里程碑",
                    "description": "这个里程碑即将逾期",
                    "deadline": (datetime.now() + timedelta(days=2)).isoformat()
                }
            ]
        }

    @classmethod
    def generate_multi_member_scenario(cls, member_count=5):
        """生成多成员项目场景"""
        return {
            "project": cls.generate_project_data(),
            "members": [
                {
                    "username": f"member{i}",
                    "display_name": f"成员{i}",
                    "roles": ["开发人员"]
                }
                for i in range(1, member_count + 1)
            ]
        }


# 便捷函数
def random_str(length=10):
    """生成随机字符串"""
    return TestDataGenerator.random_string(length)


def random_project():
    """生成随机项目数据"""
    return TestDataGenerator.generate_project_data()


def random_milestone(project_id):
    """生成随机里程碑数据"""
    return TestDataGenerator.generate_milestone_data(project_id)


def random_user():
    """生成随机用户数据"""
    return TestDataGenerator.generate_user_data()
