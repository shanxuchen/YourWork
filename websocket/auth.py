"""
WebSocket 鉴权中间件
"""
import sqlite3
import logging
from typing import Optional, Tuple
from fastapi import WebSocket, status

logger = logging.getLogger(__name__)

# 从会话模块导入验证函数（避免循环导入）
from session import validate_session


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect("data/yourwork.db", timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def authenticate_websocket(websocket: WebSocket, token: Optional[str]) -> Tuple[bool, Optional[dict]]:
    """
    验证 WebSocket 连接的会话令牌

    Args:
        websocket: WebSocket 连接对象
        token: 会话令牌

    Returns:
        (是否验证成功, 用户信息字典)
    """
    if not token:
        return False, None

    try:
        # 使用会话验证函数
        user_dict = validate_session(token)

        if user_dict:
            logger.info(f"WebSocket 鉴权成功: user={user_dict['username']}")
            return True, user_dict
        else:
            logger.warning(f"WebSocket 鉴权失败: token={token[:16]}... (无效或已过期)")
            return False, None

    except Exception as e:
        logger.error(f"WebSocket 鉴权异常: {str(e)}")
        return False, None


async def verify_connection_active(connection) -> bool:
    """
    验证连接是否活跃（未超时）

    Args:
        connection: WebSocket 连接对象

    Returns:
        是否活跃
    """
    if not hasattr(connection, 'last_active_time'):
        return False

    from websocket.schemas import WS_SESSION_TIMEOUT
    import time

    elapsed = time.time() - connection.last_active_time
    return elapsed < WS_SESSION_TIMEOUT
