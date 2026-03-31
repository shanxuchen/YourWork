"""
WebSocket 消息模型定义
"""
from dataclasses import dataclass
from typing import Any, Optional, Dict
from datetime import datetime


@dataclass
class WSMessage:
    """WebSocket 请求消息"""
    action: str
    request_id: str
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "WSMessage":
        """从字典创建消息对象"""
        return cls(
            action=data.get("action", ""),
            request_id=data.get("request_id", ""),
            data=data.get("data")
        )


@dataclass
class WSResponse:
    """WebSocket 响应消息"""
    action: str
    request_id: str
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "action": self.action,
            "request_id": self.request_id,
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def success(cls, action: str, request_id: str, data: Any = None, message: str = "success") -> "WSResponse":
        """创建成功响应"""
        return cls(action=action, request_id=request_id, code=0, message=message, data=data)

    @classmethod
    def error(cls, action: str, request_id: str, code: int, message: str) -> "WSResponse":
        """创建错误响应"""
        return cls(action=action, request_id=request_id, code=code, message=message, data=None)


@dataclass
class WSNotification:
    """WebSocket 服务器主动推送消息"""
    type: str  # 固定值 "notification"
    event: str  # 事件类型
    data: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "type": self.type,
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp
        }

    @classmethod
    def create(cls, event: str, data: Dict[str, Any]) -> "WSNotification":
        """创建推送消息"""
        return cls(
            type="notification",
            event=event,
            data=data,
            timestamp=datetime.now().isoformat()
        )


# WebSocket 配置常量
WS_SESSION_TIMEOUT = 900  # 会话超时时间（秒），默认15分钟
WS_MAX_CONNECTIONS = 1000  # 最大连接数
WS_HEARTBEAT_INTERVAL = 30  # 心跳检测间隔（秒）
