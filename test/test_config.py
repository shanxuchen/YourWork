"""
YourWork - 测试配置
定义测试相关的配置参数
"""

import os


class TestConfig:
    """测试配置类"""

    # 测试数据库配置
    TEST_DB_NAME = "test_yourwork.db"
    TEST_DB_PATH = os.path.join(os.path.dirname(__file__), TEST_DB_NAME)

    # 测试用户
    TEST_USERS = {
        "admin": {
            "username": "admin",
            "password": "admin123",
            "display_name": "系统管理员",
            "role": "SYSTEM_ADMIN"
        },
        "manager": {
            "username": "manager",
            "password": "manager123",
            "display_name": "项目经理",
            "role": "ADMIN"
        },
        "worker": {
            "username": "worker",
            "password": "worker123",
            "display_name": "普通员工",
            "role": "WORKER"
        },
        "inactive": {
            "username": "inactive",
            "password": "inactive123",
            "display_name": "禁用用户",
            "role": "WORKER",
            "is_active": 0
        }
    }

    # API 配置
    API_BASE_URL = "http://localhost:8000"
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"

    # 测试超时配置
    REQUEST_TIMEOUT = 30  # 秒
    ASYNC_TIMEOUT = 60   # 秒

    # 测试数据配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # 项目状态
    PROJECT_STATUS = {
        "IN_PROGRESS": "in_progress",
        "COMPLETED": "completed",
        "IGNORED": "ignored"
    }

    # 里程碑状态
    MILESTONE_STATUS = {
        "CREATED": "created",
        "WAITING": "waiting",
        "PAUSED": "paused",
        "COMPLETED": "completed"
    }

    # 里程碑类型
    MILESTONE_TYPE = {
        "MILESTONE": "milestone",
        "ACCEPTANCE": "acceptance"
    }

    # 消息类型
    MESSAGE_TYPE = {
        "SYSTEM": "system",
        "PROJECT": "project",
        "MILESTONE": "milestone",
        "REMINDER": "reminder"
    }

    # HTTP 状态码
    HTTP_STATUS = {
        "OK": 200,
        "CREATED": 201,
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "SERVER_ERROR": 500
    }

    # 业务状态码
    RESPONSE_CODE = {
        "SUCCESS": 0,
        "ERROR": 1,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "VALIDATION_ERROR": 400
    }

    # 测试标签
    TEST_TAGS = {
        "UNIT": "unit",
        "INTEGRATION": "integration",
        "SYSTEM": "system",
        "API": "api",
        "DATABASE": "database",
        "AUTH": "auth",
        "PROJECT": "project",
        "MILESTONE": "milestone",
        "MESSAGE": "message"
    }

    # 测试执行配置
    class Execution:
        """测试执行配置"""

        # 并行执行
        PARALLEL = False
        PARALLEL_WORKERS = 4

        # 重试配置
        MAX_RETRIES = 3
        RETRY_DELAY = 1  # 秒

        # 失败后继续
        FAIL_FAST = False

        # 详细输出
        VERBOSE = True

        # 输出格式
        OUTPUT_FORMAT = "text"  # text, json, html

    # 报告配置
    class Reporting:
        """测试报告配置"""

        # 报告目录
        REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")

        # 报告文件
        REPORT_FILE = "test_report.html"
        COVERAGE_FILE = "coverage.xml"
        JUNIT_FILE = "junit.xml"

        # 覆盖率配置
        COVERAGE_MIN = 80  # 最低覆盖率百分比

        # 报告详细程度
        REPORT_VERBOSE = True

    # 数据库测试配置
    class Database:
        """数据库测试配置"""

        # 测试前清理
        CLEAN_BEFORE = True

        # 测试后清理
        CLEAN_AFTER = True

        # 保留测试数据
        KEEP_DATA = False

        # 事务回滚
        USE_TRANSACTION = False

    # API 测试配置
    class API:
        """API 测试配置"""

        # 模拟请求头
        MOCK_HEADERS = {
            "User-Agent": "YourWork-Test/1.0",
            "Accept": "application/json"
        }

        # 忽略的验证字段
        IGNORE_FIELDS = ["id", "created_at", "updated_at"]

    # 性能测试配置
    class Performance:
        """性能测试配置"""

        # 最大响应时间 (毫秒)
        MAX_RESPONSE_TIME = 1000

        # 最大并发数
        MAX_CONCURRENT = 100

        # 压力测试持续时间 (秒)
        STRESS_DURATION = 60

    # 集成测试场景
    INTEGRATION_SCENARIOS = {
        "full_project_lifecycle": "完整项目生命周期测试",
        "user_registration_login": "用户注册登录流程测试",
        "multi_user_collaboration": "多用户协作测试",
        "milestone_workflow": "里程碑工作流测试",
        "message_notification": "消息通知测试"
    }

    # 系统测试场景
    SYSTEM_SCENARIOS = {
        "end_to_end_project": "端到端项目创建到完成测试",
        "concurrent_operations": "并发操作测试",
        "data_consistency": "数据一致性测试",
        "error_recovery": "错误恢复测试",
        "performance_under_load": "负载下性能测试"
    }


# 测试环境检查
def check_test_environment():
    """检查测试环境是否就绪"""
    checks = {
        "python_version": check_python_version(),
        "dependencies": check_dependencies(),
        "data_directory": check_data_directory(),
        "test_directory": check_test_directory()
    }

    all_passed = all(checks.values())

    return {
        "passed": all_passed,
        "checks": checks
    }


def check_python_version():
    """检查 Python 版本"""
    import sys
    version = sys.version_info
    return version.major >= 3 and version.minor >= 8


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import sqlite3
        return True
    except ImportError:
        return False


def check_data_directory():
    """检查数据目录是否存在"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    return os.path.exists(data_dir)


def check_test_directory():
    """检查测试目录是否存在"""
    test_dir = os.path.dirname(__file__)
    return os.path.exists(test_dir)
