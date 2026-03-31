"""
YourWork - 数据库初始化脚本
创建所有数据表并插入初始数据
"""

import sqlite3
import logging
import os
import uuid
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = "data/yourwork.db"


def generate_id():
    """生成唯一ID"""
    return str(uuid.uuid4())


def get_db():
    """获取数据库连接"""
    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_tables(db_path=None):
    """初始化所有数据表"""
    global DB_PATH

    if db_path:
        original_db_path = DB_PATH
        DB_PATH = db_path

    logger.info("开始创建数据表...")

    conn = get_db()

    # 创建所有表
    conn.executescript("""
        -- ===== 用户相关表 =====

        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT,
            email TEXT,
            avatar TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );

        -- 角色表
        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            description TEXT,
            is_system INTEGER DEFAULT 0
        );

        -- 用户角色关联表
        CREATE TABLE IF NOT EXISTS user_roles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );

        -- ===== 项目相关表 =====

        -- 项目表
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            project_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'in_progress',
            resources TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        -- 项目成员表
        CREATE TABLE IF NOT EXISTS project_members (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            roles TEXT,
            display_name TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ===== 里程碑相关表 =====

        -- 里程碑表
        CREATE TABLE IF NOT EXISTS milestones (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            type TEXT DEFAULT 'milestone',
            name TEXT NOT NULL,
            description TEXT,
            deliverables TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'created',
            document TEXT,
            parent_id TEXT,
            execution_result TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        -- 里程碑依赖表
        CREATE TABLE IF NOT EXISTS milestone_dependencies (
            id TEXT PRIMARY KEY,
            milestone_id TEXT NOT NULL,
            depends_on_id TEXT NOT NULL,
            FOREIGN KEY (milestone_id) REFERENCES milestones(id),
            FOREIGN KEY (depends_on_id) REFERENCES milestones(id)
        );

        -- 里程碑执行记录表
        CREATE TABLE IF NOT EXISTS milestone_logs (
            id TEXT PRIMARY KEY,
            milestone_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (milestone_id) REFERENCES milestones(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 里程碑行动项表
        CREATE TABLE IF NOT EXISTS milestone_items (
            id TEXT PRIMARY KEY,
            milestone_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            sort_order INTEGER DEFAULT 0,
            assignee_id TEXT,
            deadline TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            is_auto_created INTEGER DEFAULT 0,
            source_type TEXT DEFAULT 'manual',
            FOREIGN KEY (milestone_id) REFERENCES milestones(id),
            FOREIGN KEY (assignee_id) REFERENCES users(id)
        );

        -- ===== 产出物表 =====

        -- 产出物表
        CREATE TABLE IF NOT EXISTS deliverables (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            project_id TEXT NOT NULL,
            milestone_id TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        -- ===== 消息表 =====

        -- 消息表
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            type TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            related_id TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ===== WebSocket 日志表 =====

        -- WebSocket 操作日志表
        CREATE TABLE IF NOT EXISTS ws_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            request_id TEXT NOT NULL,
            request_data TEXT,
            response_code INTEGER,
            response_message TEXT,
            error_message TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- ===== 会话管理表 =====

        -- 会话表
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_revoked BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);
        CREATE INDEX IF NOT EXISTS idx_milestones_status ON milestones(status);
        CREATE INDEX IF NOT EXISTS idx_milestone_items_milestone ON milestone_items(milestone_id);
        CREATE INDEX IF NOT EXISTS idx_milestone_items_status ON milestone_items(status);
        CREATE INDEX IF NOT EXISTS idx_deliverables_project ON deliverables(project_id);
        CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_is_read ON messages(is_read);
        CREATE INDEX IF NOT EXISTS idx_ws_logs_user ON ws_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_ws_logs_action ON ws_logs(action);
        CREATE INDEX IF NOT EXISTS idx_ws_logs_created ON ws_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
    """)

    conn.commit()
    conn.close()
    logger.info("数据表创建完成")


def insert_roles():
    """插入初始角色数据"""
    logger.info("插入初始角色数据...")

    conn = get_db()
    now = datetime.now().isoformat()

    roles = [
        {
            "id": generate_id(),
            "name": "系统管理员",
            "code": "SYSTEM_ADMIN",
            "description": "系统最高权限，可管理所有项目和用户",
            "is_system": 1
        },
        {
            "id": generate_id(),
            "name": "管理员",
            "code": "ADMIN",
            "description": "可创建和管理项目",
            "is_system": 1
        },
        {
            "id": generate_id(),
            "name": "工作人员",
            "code": "WORKER",
            "description": "可参与项目工作",
            "is_system": 1
        }
    ]

    for role in roles:
        try:
            conn.execute(
                "INSERT INTO roles (id, name, code, description, is_system) VALUES (?, ?, ?, ?, ?)",
                (role["id"], role["name"], role["code"], role["description"], role["is_system"])
            )
            logger.info(f"  创建角色: {role['name']} ({role['code']})")
        except sqlite3.IntegrityError:
            logger.warning(f"  角色已存在: {role['code']}")

    conn.commit()
    conn.close()
    logger.info("角色数据插入完成")


def insert_admin_user():
    """插入默认管理员用户（首次安装时交互式输入）"""
    conn = get_db()
    now = datetime.now().isoformat()

    # 检查是否已存在管理员
    cursor = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if cursor.fetchone():
        logger.info("  管理员用户已存在，跳过创建")
        conn.close()
        return

    # 检查是否是交互式终端
    import sys
    is_interactive = sys.stdin.isatty()

    if is_interactive:
        # 交互式输入管理员凭证
        print("=" * 50)
        print("首次安装 - 创建管理员账号")
        print("=" * 50)

        while True:
            username = input("请输入管理员用户名: ").strip()
            if not username:
                print("错误：用户名不能为空")
                continue
            # 验证用户名格式
            if len(username) < 3:
                print("错误：用户名至少3个字符")
                continue
            # 检查用户名是否已存在
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                print("错误：该用户名已被使用")
                continue
            break

        while True:
            password = input("请输入管理员密码（至少8位，建议包含字母、数字、符号）: ").strip()
            if len(password) < 8:
                print("错误：密码至少8个字符")
                continue
            # 检查密码强度
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            if not (has_letter and has_digit):
                print("错误：密码必须包含字母和数字")
                continue
            confirm = input("请再次输入密码确认: ").strip()
            if password != confirm:
                print("错误：两次输入的密码不一致")
                continue
            break

        display_name = input("请输入显示名称（可选，直接回车跳过）: ").strip() or username

        # 创建管理员用户
        import hashlib
        admin_id = generate_id()
        admin_password = hashlib.sha256(password.encode()).hexdigest()

        conn.execute(
            "INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (admin_id, username, admin_password, display_name, 1, now, now)
        )

        # 分配系统管理员角色
        cursor = conn.execute("SELECT id FROM roles WHERE code = ?", ("SYSTEM_ADMIN",))
        role = cursor.fetchone()

        if role:
            conn.execute(
                "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                (generate_id(), admin_id, role["id"])
            )

        conn.commit()
        conn.close()

        print("=" * 50)
        print("管理员账号创建成功！")
        print("=" * 50)
        print(f"用户名: {username}")
        print(f"显示名称: {display_name}")
        print(f"密码: {'*' * len(password)}")
        print("=" * 50)
        logger.info("管理员用户创建完成")
    else:
        # 非交互式环境（如脚本执行），生成随机密码
        import hashlib
        import secrets
        import string

        admin_id = generate_id()
        # 生成强随机密码：16位，包含大小写字母、数字、符号
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        admin_password = ''.join(secrets.choice(alphabet) for _ in range(16))
        admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

        conn.execute(
            "INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (admin_id, "admin", admin_password_hash, "系统管理员", 1, now, now)
        )

        # 分配系统管理员角色
        cursor = conn.execute("SELECT id FROM roles WHERE code = ?", ("SYSTEM_ADMIN",))
        role = cursor.fetchone()

        if role:
            conn.execute(
                "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                (generate_id(), admin_id, role["id"])
            )

        conn.commit()
        conn.close()

        # 输出到文件，避免日志暴露
        import os
        admin_cred_file = "ADMIN_CREDENTIALS.txt"
        with open(admin_cred_file, "w", encoding="utf-8") as f:
            f.write(f"YourWork 管理员凭证\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 40 + "\n")
            f.write(f"用户名: admin\n")
            f.write(f"密码: {admin_password}\n")
            f.write("=" * 40 + "\n")
            f.write("重要：请妥善保管此文件，登录后请立即删除或移动到安全位置！\n")

        logger.info("  管理员用户创建完成")
        logger.info(f"  密码已保存到: {admin_cred_file}")

        # 设置文件权限（仅所有者可读写）
        try:
            os.chmod(admin_cred_file, 0o600)
        except:
            pass


def insert_test_data():
    """插入测试数据"""
    logger.info("插入测试数据...")

    conn = get_db()
    now = datetime.now().isoformat()

    # 获取系统管理员角色
    cursor = conn.execute("SELECT id FROM roles WHERE code = ?", ("SYSTEM_ADMIN",))
    admin_role_id = cursor.fetchone()["id"]

    # 创建测试用户
    test_users = [
        {"username": "testuser1", "display_name": "测试用户1", "password": "test123"},
        {"username": "testuser2", "display_name": "测试用户2", "password": "test123"},
        {"username": "manager", "display_name": "项目管理员", "password": "manager123", "role": "ADMIN"},
        {"username": "worker", "display_name": "普通员工", "password": "worker123", "role": "WORKER"}
    ]

    user_ids = {}
    import hashlib

    for user_data in test_users:
        try:
            user_id = generate_id()
            password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()

            conn.execute(
                "INSERT INTO users (id, username, password, display_name, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, user_data["username"], password_hash, user_data["display_name"], 1, now, now)
            )

            # 根据用户的role属性分配角色，默认为WORKER
            role_code = user_data.get("role", "WORKER")
            cursor = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,))
            role_row = cursor.fetchone()

            if role_row:
                conn.execute(
                    "INSERT INTO user_roles (id, user_id, role_id) VALUES (?, ?, ?)",
                    (generate_id(), user_id, role_row["id"])
                )

            user_ids[user_data["username"]] = user_id
            logger.info(f"  创建测试用户: {user_data['username']}")
        except sqlite3.IntegrityError:
            logger.warning(f"  用户已存在: {user_data['username']}")

    # 创建测试项目
    test_projects = [
        {"name": "示例项目 - 网站开发", "description": "这是一个示例项目"},
        {"name": "示例项目 - 移动应用", "description": "另一个示例项目"}
    ]

    project_ids = {}

    for i, project_data in enumerate(test_projects):
        project_id = generate_id()
        project_no = f"PRJ-{datetime.now().strftime('%Y%m%d')}-{project_id[:8]}"

        conn.execute(
            "INSERT INTO projects (id, project_no, name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, project_no, project_data["name"], project_data["description"], "in_progress", now, now)
        )

        project_ids[f"project{i+1}"] = project_id
        logger.info(f"  创建测试项目: {project_data['name']} ({project_no})")

        # 添加项目成员
        if user_ids:
            member_user_id = list(user_ids.values())[0]
            conn.execute(
                "INSERT INTO project_members (id, project_id, user_id, display_name) VALUES (?, ?, ?, ?)",
                (generate_id(), project_id, member_user_id, "测试成员")
            )

    # 创建测试里程碑
    if project_ids:
        project_id = list(project_ids.values())[0]

        milestone_data = [
            {"name": "需求分析", "type": "milestone", "status": "completed"},
            {"name": "系统设计", "type": "milestone", "status": "in_progress"},
            {"name": "开发实现", "type": "milestone", "status": "created"}
        ]

        for ms in milestone_data:
            milestone_id = generate_id()
            conn.execute(
                "INSERT INTO milestones (id, project_id, type, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (milestone_id, project_id, ms["type"], ms["name"], ms["status"], now, now)
            )
            logger.info(f"  创建测试里程碑: {ms['name']}")

    conn.commit()
    conn.close()
    logger.info("测试数据插入完成")


def init_database(db_path=None):
    """初始化数据库（用于测试）"""
    global DB_PATH
    original_db_path = DB_PATH

    if db_path:
        DB_PATH = db_path

    init_tables()
    insert_roles()
    insert_admin_user()

    # 恢复原始路径
    DB_PATH = original_db_path


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("YourWork 数据库初始化")
    logger.info("=" * 50)

    # 创建数据表
    init_tables()

    # 插入角色数据
    insert_roles()

    # 插入管理员用户
    insert_admin_user()

    # 插入测试数据
    insert_test_data()

    logger.info("=" * 50)
    logger.info("数据库初始化完成!")
    logger.info(f"数据库文件: {DB_PATH}")
    logger.info(f"默认账号: admin / admin123")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
