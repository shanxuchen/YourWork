"""
WebSocket 连接管理器
管理所有 WebSocket 连接，处理消息路由和会话超时
"""
import time
import logging
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket

from websocket.schemas import (
    WSMessage, WSResponse, WSNotification,
    WS_SESSION_TIMEOUT, WS_HEARTBEAT_INTERVAL
)
from websocket.auth import authenticate_websocket, verify_connection_active
from websocket.handlers import ACTION_HANDLERS
import sqlite3

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """WebSocket 连接包装类"""

    def __init__(self, websocket: WebSocket, user_id: str = None, user: dict = None):
        self.websocket = websocket
        self.user_id = user_id  # None 表示未认证
        self.user = user  # None 表示未认证
        self.last_active_time = time.time()
        self.session_token = None  # 登录后存储的token

    def update_active_time(self):
        """更新最后活跃时间"""
        self.last_active_time = time.time()

    def is_timeout(self) -> bool:
        """检查是否超时"""
        return (time.time() - self.last_active_time) > WS_SESSION_TIMEOUT


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> WebSocketConnection
        self.active_connections: Dict[str, WebSocketConnection] = {}
        # 启动心跳检测任务
        self._heartbeat_task = None

    async def connect(self, websocket: WebSocket, token: Optional[str]) -> bool:
        """
        接受新的 WebSocket 连接

        允许无token连接，连接后需调用 system.login 进行认证

        Args:
            websocket: WebSocket 连接对象
            token: 用户 token（可选）

        Returns:
            是否连接成功
        """
        await websocket.accept()

        user_id = None
        user = None
        session_token = None

        # 如果提供了 token，尝试验证
        if token:
            is_valid, user_dict = authenticate_websocket(websocket, token)
            if is_valid:
                user_id = user_dict['id']
                user = user_dict
                session_token = token
                logger.info(f"WebSocket 连接建立（已认证）: user={user['username']}")
            else:
                logger.warning(f"WebSocket 连接建立（token无效，需重新登录）")
        else:
            logger.info(f"WebSocket 连接建立（未认证）")

        # 创建连接（可能是未认证状态）
        connection = WebSocketConnection(websocket, user_id, user)
        connection.session_token = session_token

        # 如果是已认证用户，检查是否已有连接
        if user_id and user_id in self.active_connections:
            try:
                await self.active_connections[user_id].websocket.close()
            except:
                pass

        # 存储连接（未认证连接用临时ID存储，登录后会更新）
        if user_id:
            self.active_connections[user_id] = connection
        else:
            # 未认证连接使用临时ID（websocket对象的id）
            temp_id = f"unauth_{id(websocket)}"
            self.active_connections[temp_id] = connection

        # 启动心跳检测任务
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_check())

        return True

    def disconnect(self, websocket: WebSocket):
        """
        断开 WebSocket 连接

        Args:
            websocket: 要断开的 WebSocket 连接
        """
        user_id = None
        for uid, conn in list(self.active_connections.items()):
            if conn.websocket == websocket:
                user_id = uid
                del self.active_connections[uid]
                logger.info(f"WebSocket 连接断开: user_id={user_id}, 剩余连接数={len(self.active_connections)}")
                break

        # 如果没有活跃连接，停止心跳检测
        if not self.active_connections and self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """
        向指定用户发送消息

        Args:
            user_id: 用户ID
            message: 要发送的消息

        Returns:
            是否发送成功
        """
        connection = self.active_connections.get(user_id)
        if not connection:
            return False

        try:
            await connection.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: user_id={user_id}, error={str(e)}")
            # 移除无效连接
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            return False

    async def broadcast_to_project(self, project_id: str, message: dict, exclude_user: str = None):
        """
        向项目成员广播消息

        Args:
            project_id: 项目ID
            message: 要广播的消息
            exclude_user: 要排除的用户ID（发送者）
        """
        try:
            conn = sqlite3.connect("data/yourwork.db", timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.execute(
                "SELECT user_id FROM project_members WHERE project_id = ?",
                (project_id,)
            )
            members = cursor.fetchall()
            conn.close()

            for member in members:
                user_id = member['user_id']
                if exclude_user and user_id == exclude_user:
                    continue
                await self.send_to_user(user_id, message)

        except Exception as e:
            logger.error(f"广播消息失败: project_id={project_id}, error={str(e)}")

    async def handle_message(self, message_data: dict, connection: WebSocketConnection) -> dict:
        """
        处理接收到的消息

        Args:
            message_data: 消息数据
            connection: WebSocket 连接对象

        Returns:
            响应消息
        """
        # 更新活跃时间
        connection.update_active_time()

        # 解析消息
        try:
            message = WSMessage.from_dict(message_data)
        except Exception as e:
            logger.error(f"消息解析失败: {str(e)}")
            return {
                "action": message_data.get("action", ""),
                "request_id": message_data.get("request_id", ""),
                "code": 400,
                "message": "消息格式错误",
                "data": None
            }

        # 检查认证状态：未认证只能调用 system.login
        if connection.user is None:
            if message.action != "system.login":
                return WSResponse.error(
                    message.action,
                    message.request_id,
                    401,
                    "未登录：请先调用 system.login 进行认证"
                ).to_dict()

        # 检查会话是否超时（仅对已认证用户）
        if connection.user and connection.is_timeout():
            return WSResponse.error(
                message.action,
                message.request_id,
                401,
                "未登录：会话已过期，请重新登录"
            ).to_dict()

        # 获取处理器
        handler = ACTION_HANDLERS.get(message.action)
        if not handler:
            return WSResponse.error(
                message.action,
                message.request_id,
                404,
                f"未知的操作: {message.action}"
            ).to_dict()

        # 执行处理逻辑
        try:
            # 获取数据库连接
            conn = sqlite3.connect("data/yourwork.db", timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")

            # 获取客户端IP
            client_ip = None
            if hasattr(connection.websocket, 'client'):
                client_ip = connection.websocket.client.host if connection.websocket.client else None

            # 调用处理器
            response = await handler(
                data=message.data or {},
                user=connection.user,
                conn=conn,
                request_id=message.request_id,
                ip_address=client_ip,
                connection=connection  # 传入连接对象，用于登录后更新状态
            )

            conn.close()

            # 触发服务器主动推送（如需要）
            await self._trigger_notifications(message.action, response, connection)

            return response.to_dict()

        except Exception as e:
            logger.error(f"处理消息异常: action={message.action}, error={str(e)}")
            return WSResponse.error(
                message.action,
                message.request_id,
                500,
                "服务器内部错误"
            ).to_dict()

    async def authenticate_connection(self, connection: WebSocketConnection, user_id: str, user: dict, session_token: str):
        """
        将未认证连接升级为已认证状态

        Args:
            connection: WebSocket 连接对象
            user_id: 用户ID
            user: 用户信息
            session_token: 会话令牌
        """
        # 移除未认证连接的临时ID
        temp_id = f"unauth_{id(connection.websocket)}"
        if temp_id in self.active_connections:
            del self.active_connections[temp_id]

        # 如果该用户已有连接，先断开
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].websocket.close()
            except:
                pass

        # 更新连接状态
        connection.user_id = user_id
        connection.user = user
        connection.session_token = session_token

        # 用用户ID存储连接
        self.active_connections[user_id] = connection

        logger.info(f"WebSocket 连接认证成功: user={user['username']}, 当前连接数={len(self.active_connections)}")

    async def _trigger_notifications(self, action: str, response: WSResponse, connection: WebSocketConnection):
        """
        根据操作触发服务器主动推送

        Args:
            action: 操作名称
            response: 响应对象
            connection: WebSocket 连接对象
        """
        if response.code != 0:
            return

        notification = None

        # 里程碑更新通知
        if action.startswith("milestone.") and action in ["milestone.update", "milestone.create"]:
            if response.data and 'project_id' in response.data:
                notification = WSNotification.create(
                    "milestone.updated",
                    {
                        "project_id": response.data.get('project_id'),
                        "project_name": "",  # 可选：查询项目名称
                        "milestone_id": response.data.get('id'),
                        "milestone_name": response.data.get('name'),
                        "status": response.data.get('status'),
                        "operator": connection.user.get('username', '')
                    }
                )

        # 项目状态更新通知
        elif action == "project.update_status":
            if response.data and 'id' in response.data:
                notification = WSNotification.create(
                    "project.updated",
                    {
                        "project_id": response.data.get('id'),
                        "project_name": "",  # 可选：查询项目名称
                        "status": response.data.get('status'),
                        "operator": connection.user.get('username', '')
                    }
                )

        # 产出物上传通知
        elif action == "deliverable.upload":
            if response.data and 'project_id' in response.data:
                notification = WSNotification.create(
                    "deliverable.uploaded",
                    {
                        "project_id": response.data.get('project_id'),
                        "project_name": "",
                        "deliverable_id": response.data.get('id'),
                        "original_name": response.data.get('original_name'),
                        "uploaded_by": connection.user.get('username', '')
                    }
                )

        # 发送通知
        if notification:
            await self.broadcast_to_project(
                response.data.get('project_id') or response.data.get('id'),
                notification.to_dict(),
                exclude_user=connection.user_id
            )

    async def _heartbeat_check(self):
        """心跳检测任务"""
        while self.active_connections:
            try:
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

                current_time = time.time()
                timeout_users = []

                for user_id, connection in list(self.active_connections.items()):
                    # 检查是否超时
                    if (current_time - connection.last_active_time) > WS_SESSION_TIMEOUT:
                        timeout_users.append(user_id)
                    else:
                        # 发送心跳包
                        try:
                            await connection.websocket.send_json({
                                "type": "heartbeat",
                                "timestamp": current_time
                            })
                        except Exception as e:
                            logger.warning(f"发送心跳失败: user_id={user_id}, error={str(e)}")
                            timeout_users.append(user_id)

                # 移除超时连接
                for user_id in timeout_users:
                    connection = self.active_connections.get(user_id)
                    if connection:
                        try:
                            await connection.websocket.send_json({
                                "type": "error",
                                "code": 401,
                                "message": "会话已过期"
                            })
                            await connection.websocket.close()
                        except:
                            pass
                        del self.active_connections[user_id]
                        logger.info(f"会话超时断开: user_id={user_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测异常: {str(e)}")

    def get_connection_count(self) -> int:
        """获取当前活跃连接数"""
        return len(self.active_connections)

    def get_active_user_ids(self) -> list:
        """获取当前活跃的用户ID列表"""
        return list(self.active_connections.keys())
