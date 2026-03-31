"""
会话管理模块
提供会话创建、验证、撤销等功能
"""
import sqlite3
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 配置常量
SESSION_TOKEN_LENGTH = 64
SESSION_DEFAULT_DURATION_HOURS = 24


def get_db_path():
    """动态获取数据库路径"""
    try:
        from main import DB_PATH
        return DB_PATH
    except ImportError:
        return "data/yourwork.db"


def get_db():
    """获取数据库连接"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def generate_session_token() -> str:
    """生成随机会话令牌"""
    return secrets.token_hex(SESSION_TOKEN_LENGTH // 2)


def create_session(user_id: str, duration_hours: int = SESSION_DEFAULT_DURATION_HOURS) -> str:
    """
    创建用户会话

    Args:
        user_id: 用户ID
        duration_hours: 会话有效期（小时）

    Returns:
        会话令牌
    """
    import uuid
    conn = get_db()
    session_id = str(uuid.uuid4())
    token = generate_session_token()
    now = datetime.now()
    expires_at = now + timedelta(hours=duration_hours)

    try:
        conn.execute(
            """INSERT INTO sessions (id, user_id, token, expires_at, created_at, last_used_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, token, expires_at.isoformat(), now.isoformat(), now.isoformat())
        )
        conn.commit()
        logger.info(f"创建会话: user_id={user_id}, token={token[:16]}..., expires_at={expires_at.isoformat()}")
        return token
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def validate_session(token: str) -> Optional[Dict]:
    """
    验证会话令牌

    Args:
        token: 会话令牌

    Returns:
        用户信息字典，如果令牌无效则返回 None
    """
    if not token:
        return None

    conn = get_db()
    try:
        now = datetime.now()

        # 查询有效的会话
        cursor = conn.execute(
            """SELECT s.*, u.* FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.token = ? AND s.is_revoked = 0 AND u.is_active = 1""",
            (token,)
        )
        session = cursor.fetchone()

        if not session:
            logger.warning(f"会话验证失败: token={token[:16]}... (不存在或已撤销)")
            return None

        session_dict = dict(session)

        # 检查是否过期
        expires_at = datetime.fromisoformat(session_dict['expires_at'])
        if now > expires_at:
            logger.warning(f"会话验证失败: token={token[:16]}... (已过期)")
            return None

        # 更新最后使用时间
        conn.execute(
            "UPDATE sessions SET last_used_at = ? WHERE token = ?",
            (now.isoformat(), token)
        )
        conn.commit()

        # 返回用户信息（移除密码和会话相关字段）
        user_info = {
            'id': session_dict['user_id'],
            'username': session_dict['username'],
            'display_name': session_dict.get('display_name'),
            'email': session_dict.get('email'),
            'avatar': session_dict.get('avatar'),
            'is_active': session_dict['is_active'],
            'created_at': session_dict.get('created_at'),
            'updated_at': session_dict.get('updated_at')
        }

        logger.info(f"会话验证成功: user_id={user_info['id']}, username={user_info['username']}")
        return user_info

    except Exception as e:
        logger.error(f"会话验证异常: {str(e)}")
        return None
    finally:
        conn.close()


def revoke_session(token: str) -> bool:
    """
    撤销会话令牌

    Args:
        token: 会话令牌

    Returns:
        是否成功撤销
    """
    if not token:
        return False

    conn = get_db()
    try:
        cursor = conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"会话已撤销: token={token[:16]}...")
            return True
        else:
            logger.warning(f"撤销会话失败: token={token[:16]}... (不存在)")
            return False
    except Exception as e:
        logger.error(f"撤销会话异常: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()


def cleanup_expired_sessions() -> int:
    """
    清理过期会话

    Returns:
        清理的会话数量
    """
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "DELETE FROM sessions WHERE expires_at < ? OR is_revoked = 1",
            (now,)
        )
        conn.commit()

        deleted_count = cursor.rowcount
        if deleted_count > 0:
            logger.info(f"清理过期会话: 删除 {deleted_count} 条记录")

        return deleted_count
    except Exception as e:
        logger.error(f"清理过期会话异常: {str(e)}")
        conn.rollback()
        return 0
    finally:
        conn.close()
