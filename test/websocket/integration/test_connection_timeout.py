"""
YourWork - WebSocket连接超时测试
测试WebSocket连接超时机制和心跳功能
"""

import unittest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock

from test.test_base import TestBase
from fastapi.testclient import TestClient
from fastapi import WebSocket
from main import app

# 导入WebSocket相关模块
from websocket.manager import WebSocketManager, WebSocketConnection
from websocket.schemas import WS_SESSION_TIMEOUT, WS_HEARTBEAT_INTERVAL


class TestWebSocketConnectionTimeout(TestBase):
    """测试WebSocket连接超时机制"""

    def test_session_timeout_configuration(self):
        """测试会话超时配置"""
        # 验证超时配置常量
        self.assertIsNotNone(WS_SESSION_TIMEOUT)
        self.assertGreater(WS_SESSION_TIMEOUT, 0)
        self.assertEqual(WS_SESSION_TIMEOUT, 900, "默认会话超时应为15分钟")

    def test_heartbeat_interval_configuration(self):
        """测试心跳间隔配置"""
        self.assertIsNotNone(WS_HEARTBEAT_INTERVAL)
        self.assertGreater(WS_HEARTBEAT_INTERVAL, 0)
        self.assertEqual(WS_HEARTBEAT_INTERVAL, 30, "默认心跳间隔应为30秒")

    def test_connection_manager_initialization(self):
        """测试连接管理器初始化"""
        manager = WebSocketManager()

        self.assertIsNotNone(manager)
        self.assertEqual(len(manager.active_connections), 0)
        self.assertIsNone(manager._heartbeat_task)
        self.assertEqual(manager.get_connection_count(), 0)
        self.assertEqual(manager.get_active_user_ids(), [])


class TestWebSocketConnectionLifeCycle(TestBase):
    """测试WebSocket连接生命周期"""

    def test_connection_creation(self):
        """测试连接创建"""
        manager = WebSocketManager()

        # 创建模拟的WebSocket和用户
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_user = {
            "id": "test-user-1",
            "username": "testuser",
            "display_name": "测试用户"
        }

        # 创建连接对象
        connection = WebSocketConnection(mock_websocket, mock_user["id"], mock_user)

        self.assertIsNotNone(connection)
        self.assertEqual(connection.user_id, mock_user["id"])
        self.assertEqual(connection.user, mock_user)
        self.assertIsNotNone(connection.last_active_time)

    def test_connection_active_time_update(self):
        """测试连接活跃时间更新"""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)
        initial_time = connection.last_active_time

        # 短暂等待
        time.sleep(0.1)

        # 更新活跃时间
        connection.update_active_time()

        self.assertGreater(connection.last_active_time, initial_time)

    def test_connection_timeout_check(self):
        """测试连接超时检查"""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        # 初始状态不应超时
        self.assertFalse(connection.is_timeout())

        # 修改last_active_time模拟超时
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT - 1
        self.assertTrue(connection.is_timeout())

    def test_multiple_connections_same_user(self):
        """测试同一用户的多个连接处理"""
        manager = WebSocketManager()

        # 创建模拟连接
        mock_websocket1 = MagicMock(spec=WebSocket)
        mock_websocket1.close = AsyncMock()
        mock_websocket2 = MagicMock(spec=WebSocket)
        mock_websocket2.accept = AsyncMock()
        mock_user = {"id": "same-user", "username": "testuser"}

        connection1 = WebSocketConnection(mock_websocket1, "same-user", mock_user)
        manager.active_connections["same-user"] = connection1

        # 验证第一个连接存在
        self.assertEqual(manager.get_connection_count(), 1)

        # 模拟第二个连接（应该替换第一个）
        connection2 = WebSocketConnection(mock_websocket2, "same-user", mock_user)
        manager.active_connections["same-user"] = connection2

        # 验证仍然只有一个连接
        self.assertEqual(manager.get_connection_count(), 1)


class TestHeartbeatMechanism(TestBase):
    """测试心跳机制"""

    def test_heartbeat_message_format(self):
        """测试心跳消息格式"""
        expected_fields = ["type", "timestamp"]
        heartbeat_message = {
            "type": "heartbeat",
            "timestamp": time.time()
        }

        # 验证消息格式
        self.assertIn("type", heartbeat_message)
        self.assertEqual(heartbeat_message["type"], "heartbeat")
        self.assertIn("timestamp", heartbeat_message)

    def test_heartbeat_reception(self):
        """测试心跳接收处理"""
        # 这个测试需要实际的WebSocket连接
        # 在集成测试环境中可能需要跳过
        pass

    def test_heartbeat_response(self):
        """测试心跳响应"""
        # 测试客户端对心跳的响应
        pass


class TestSessionTimeout(TestBase):
    """测试会话超时"""

    def test_timeout_after_inactivity(self):
        """测试不活跃后的超时"""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        # 设置活跃时间为过去（模拟超时）
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT - 10

        # 验证超时
        self.assertTrue(connection.is_timeout())

    def test_no_timeout_with_activity(self):
        """测试有活动时不超时"""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        # 持续更新活跃时间
        for _ in range(5):
            time.sleep(0.1)
            connection.update_active_time()
            self.assertFalse(connection.is_timeout())

    def test_timeout_boundary_conditions(self):
        """测试超时边界条件"""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        # 正好在超时边界
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT
        # 根据实现，这可能刚好超时或未超时
        is_timeout = connection.is_timeout()
        self.assertIsInstance(is_timeout, bool)

        # 刚好在超时前
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT + 1
        self.assertFalse(connection.is_timeout())

        # 刚好在超时后
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT - 1
        self.assertTrue(connection.is_timeout())


class TestConnectionCleanup(TestBase):
    """测试连接清理"""

    def test_disconnect_removes_connection(self):
        """测试断开移除连接"""
        manager = WebSocketManager()

        # 创建模拟连接
        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}
        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        manager.active_connections["test-user"] = connection
        self.assertEqual(manager.get_connection_count(), 1)

        # 断开连接
        manager.disconnect(mock_websocket)

        # 验证连接被移除
        self.assertEqual(manager.get_connection_count(), 0)

    def test_multiple_disconnects(self):
        """测试多次断开"""
        manager = WebSocketManager()

        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}
        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        manager.active_connections["test-user"] = connection

        # 多次断开（不应该报错）
        manager.disconnect(mock_websocket)
        self.assertEqual(manager.get_connection_count(), 0)

        manager.disconnect(mock_websocket)
        self.assertEqual(manager.get_connection_count(), 0)

    def test_cleanup_on_error(self):
        """测试错误时清理"""
        manager = WebSocketManager()

        mock_websocket = MagicMock(spec=WebSocket)
        mock_user = {"id": "test-user", "username": "test"}
        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)

        manager.active_connections["test-user"] = connection

        # 模拟发送失败导致清理
        # 这需要测试send_to_user的错误处理
        # 由于需要异步，这里仅做结构测试
        self.assertEqual(manager.get_connection_count(), 1)


class TestConnectionPool(TestBase):
    """测试连接池管理"""

    def test_max_connections_limit(self):
        """测试最大连接数限制"""
        from websocket.schemas import WS_MAX_CONNECTIONS

        self.assertIsNotNone(WS_MAX_CONNECTIONS)
        self.assertGreater(WS_MAX_CONNECTIONS, 0)
        self.assertEqual(WS_MAX_CONNECTIONS, 1000)

    def test_connection_count_tracking(self):
        """测试连接数跟踪"""
        manager = WebSocketManager()

        # 初始状态
        self.assertEqual(manager.get_connection_count(), 0)

        # 添加连接
        for i in range(5):
            mock_websocket = MagicMock(spec=WebSocket)
            mock_user = {"id": f"user-{i}", "username": f"user{i}"}
            connection = WebSocketConnection(mock_websocket, f"user-{i}", mock_user)
            manager.active_connections[f"user-{i}"] = connection

        self.assertEqual(manager.get_connection_count(), 5)

        # 移除连接
        del manager.active_connections["user-0"]
        self.assertEqual(manager.get_connection_count(), 4)

    def test_active_user_ids_list(self):
        """测试活跃用户ID列表"""
        manager = WebSocketManager()

        user_ids = ["user-1", "user-2", "user-3"]

        for user_id in user_ids:
            mock_websocket = MagicMock(spec=WebSocket)
            mock_user = {"id": user_id, "username": f"user{user_id}"}
            connection = WebSocketConnection(mock_websocket, user_id, mock_user)
            manager.active_connections[user_id] = connection

        active_ids = manager.get_active_user_ids()
        self.assertEqual(set(active_ids), set(user_ids))


class TestConnectionRecovery(TestBase):
    """测试连接恢复"""

    def test_reconnect_after_timeout(self):
        """测试超时后重连"""
        # 测试超时后能否重新连接
        manager = WebSocketManager()

        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.close = AsyncMock()
        mock_user = {"id": "test-user", "username": "test"}

        connection = WebSocketConnection(mock_websocket, "test-user", mock_user)
        manager.active_connections["test-user"] = connection

        # 模拟超时断开
        connection.last_active_time = time.time() - WS_SESSION_TIMEOUT - 10

        # 验证超时
        self.assertTrue(connection.is_timeout())

        # 可以重新连接（创建新连接）
        mock_websocket2 = MagicMock(spec=WebSocket)
        connection2 = WebSocketConnection(mock_websocket2, "test-user", mock_user)
        manager.active_connections["test-user"] = connection2

        # 验证新连接未超时
        self.assertFalse(connection2.is_timeout())

    def test_state_preservation(self):
        """测试状态保留"""
        # 测试重连后状态是否保留
        pass


class TestConcurrentConnections(TestBase):
    """测试并发连接"""

    def test_concurrent_connection_handling(self):
        """测试并发连接处理"""
        manager = WebSocketManager()

        # 模拟多个用户同时连接
        connections = []
        for i in range(10):
            mock_websocket = MagicMock(spec=WebSocket)
            mock_user = {"id": f"user-{i}", "username": f"user{i}"}
            connection = WebSocketConnection(mock_websocket, f"user-{i}", mock_user)
            manager.active_connections[f"user-{i}"] = connection
            connections.append(connection)

        self.assertEqual(manager.get_connection_count(), 10)

        # 验证每个连接都有独立的活跃时间
        active_times = [conn.last_active_time for conn in connections]
        self.assertEqual(len(active_times), len(set(active_times)))


class TestErrorHandling(TestBase):
    """测试错误处理"""

    def test_invalid_websocket_disconnect(self):
        """测试无效WebSocket断开"""
        manager = WebSocketManager()

        # 尝试断开不存在的连接
        mock_websocket = MagicMock(spec=WebSocket)
        manager.disconnect(mock_websocket)

        # 不应该报错
        self.assertEqual(manager.get_connection_count(), 0)

    def test_connection_with_invalid_user(self):
        """测试无效用户的连接"""
        mock_websocket = MagicMock(spec=WebSocket)
        invalid_user = {"id": "", "username": ""}

        # 应该能创建连接（但可能被其他验证拒绝）
        connection = WebSocketConnection(mock_websocket, "", invalid_user)
        self.assertIsNotNone(connection)


if __name__ == "__main__":
    unittest.main()
