"""
WebSocket 单元测试 - 测试 schemas 模块
测试 WSMessage、WSResponse、WSNotification 消息模型
"""

import os
import sys
import json
import unittest
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from websocket.schemas import (
    WSMessage, WSResponse, WSNotification,
    WS_SESSION_TIMEOUT, WS_MAX_CONNECTIONS, WS_HEARTBEAT_INTERVAL
)


class TestWSMessage(unittest.TestCase):
    """测试 WSMessage 消息模型"""

    def test_create_message(self):
        """测试创建消息"""
        message = WSMessage(
            action="test.action",
            request_id="req_001",
            data={"key": "value"}
        )

        self.assertEqual(message.action, "test.action")
        self.assertEqual(message.request_id, "req_001")
        self.assertEqual(message.data, {"key": "value"})

    def test_create_message_without_data(self):
        """测试创建无数据的消息"""
        message = WSMessage(
            action="test.action",
            request_id="req_001"
        )

        self.assertEqual(message.action, "test.action")
        self.assertEqual(message.request_id, "req_001")
        self.assertIsNone(message.data)

    def test_from_dict(self):
        """测试从字典创建消息"""
        data = {
            "action": "project.create",
            "request_id": "req_002",
            "data": {"name": "Test Project"}
        }

        message = WSMessage.from_dict(data)

        self.assertEqual(message.action, "project.create")
        self.assertEqual(message.request_id, "req_002")
        self.assertEqual(message.data, {"name": "Test Project"})

    def test_from_dict_without_data(self):
        """测试从字典创建消息（无 data 字段）"""
        data = {
            "action": "system.ping",
            "request_id": "req_003"
        }

        message = WSMessage.from_dict(data)

        self.assertEqual(message.action, "system.ping")
        self.assertEqual(message.request_id, "req_003")
        self.assertIsNone(message.data)


class TestWSResponse(unittest.TestCase):
    """测试 WSResponse 响应模型"""

    def test_create_response(self):
        """测试创建响应"""
        response = WSResponse(
            action="test.action",
            request_id="req_001",
            code=0,
            message="success",
            data={"result": "ok"}
        )

        self.assertEqual(response.action, "test.action")
        self.assertEqual(response.request_id, "req_001")
        self.assertEqual(response.code, 0)
        self.assertEqual(response.message, "success")
        self.assertEqual(response.data, {"result": "ok"})

    def test_to_dict(self):
        """测试转换为字典"""
        response = WSResponse(
            action="test.action",
            request_id="req_001",
            code=0,
            message="success",
            data={"result": "ok"}
        )

        result = response.to_dict()

        expected = {
            "action": "test.action",
            "request_id": "req_001",
            "code": 0,
            "message": "success",
            "data": {"result": "ok"}
        }
        self.assertEqual(result, expected)

    def test_to_dict_without_data(self):
        """测试转换为字典（无 data）"""
        response = WSResponse(
            action="test.action",
            request_id="req_001",
            code=404,
            message="not found"
        )

        result = response.to_dict()

        expected = {
            "action": "test.action",
            "request_id": "req_001",
            "code": 404,
            "message": "not found"
        }
        self.assertEqual(result, expected)

    def test_success_method(self):
        """测试成功响应工厂方法"""
        response = WSResponse.success(
            action="project.create",
            request_id="req_001",
            data={"project_id": "xxx"},
            message="创建成功"
        )

        self.assertEqual(response.code, 0)
        self.assertEqual(response.message, "创建成功")
        self.assertEqual(response.data, {"project_id": "xxx"})

    def test_error_method(self):
        """测试错误响应工厂方法"""
        response = WSResponse.error(
            action="project.create",
            request_id="req_001",
            code=403,
            message="无权限"
        )

        self.assertEqual(response.code, 403)
        self.assertEqual(response.message, "无权限")
        self.assertIsNone(response.data)


class TestWSNotification(unittest.TestCase):
    """测试 WSNotification 推送消息模型"""

    def test_create_notification(self):
        """测试创建推送消息"""
        notification = WSNotification(
            type="notification",
            event="test.event",
            data={"message": "test"},
            timestamp="2024-01-01T00:00:00"
        )

        self.assertEqual(notification.type, "notification")
        self.assertEqual(notification.event, "test.event")
        self.assertEqual(notification.data, {"message": "test"})
        self.assertEqual(notification.timestamp, "2024-01-01T00:00:00")

    def test_to_dict(self):
        """测试转换为字典"""
        notification = WSNotification(
            type="notification",
            event="milestone.updated",
            data={"project_id": "xxx"},
            timestamp="2024-01-01T00:00:00"
        )

        result = notification.to_dict()

        expected = {
            "type": "notification",
            "event": "milestone.updated",
            "data": {"project_id": "xxx"},
            "timestamp": "2024-01-01T00:00:00"
        }
        self.assertEqual(result, expected)

    def test_create_factory_method(self):
        """测试创建推送消息工厂方法"""
        notification = WSNotification.create(
            event="message.new",
            data={"title": "新消息"}
        )

        self.assertEqual(notification.type, "notification")
        self.assertEqual(notification.event, "message.new")
        self.assertEqual(notification.data, {"title": "新消息"})
        # 验证时间戳格式
        datetime.fromisoformat(notification.timestamp)


class TestWSConstants(unittest.TestCase):
    """测试 WebSocket 配置常量"""

    def test_session_timeout(self):
        """测试会话超时配置"""
        self.assertEqual(WS_SESSION_TIMEOUT, 900)  # 15分钟
        self.assertEqual(WS_SESSION_TIMEOUT, 15 * 60)

    def test_max_connections(self):
        """测试最大连接数配置"""
        self.assertEqual(WS_MAX_CONNECTIONS, 1000)

    def test_heartbeat_interval(self):
        """测试心跳间隔配置"""
        self.assertEqual(WS_HEARTBEAT_INTERVAL, 30)  # 30秒


class TestMessageSerialization(unittest.TestCase):
    """测试消息序列化和反序列化"""

    def test_message_json_roundtrip(self):
        """测试消息 JSON 序列化/反序列化"""
        original_data = {
            "action": "project.create",
            "request_id": "req_001",
            "data": {
                "name": "Test Project",
                "description": "Test Description"
            }
        }

        # 序列化
        json_str = json.dumps(original_data)

        # 反序列化
        parsed_data = json.loads(json_str)
        message = WSMessage.from_dict(parsed_data)

        self.assertEqual(message.action, original_data["action"])
        self.assertEqual(message.request_id, original_data["request_id"])
        self.assertEqual(message.data, original_data["data"])

    def test_response_json_serialization(self):
        """测试响应 JSON 序列化"""
        response = WSResponse.success(
            action="test.action",
            request_id="req_001",
            data={"items": [1, 2, 3]}
        )

        response_dict = response.to_dict()
        json_str = json.dumps(response_dict)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["code"], 0)
        self.assertEqual(parsed["data"]["items"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
