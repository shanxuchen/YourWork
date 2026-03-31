"""
WebSocket 测试客户端
用于测试 YourWork 的 WebSocket API
"""
import asyncio
import websockets
import json
from datetime import datetime

# WebSocket 服务器地址
WS_URL = "ws://localhost:8001/ws"

# 默认管理员用户（从数据库获取）
DEFAULT_TOKEN = "058e679e-8f11-4fc5-a1a6-c89dc8b35e70"  # admin 的 user_id


async def test_websocket():
    """测试 WebSocket 连接和通信"""

    print("=" * 80)
    print("WebSocket 测试客户端")
    print("=" * 80)

    # 使用默认 token 或从命令行获取
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOKEN
    url = f"{WS_URL}?token={token}"

    print(f"\n1. 连接到: {url}")
    print(f"   Token: {token}\n")

    try:
        async with websockets.connect(url) as websocket:
            print("   [OK] 连接成功!\n")

            # 测试 1: 心跳检测
            print("2. 测试心跳检测 (system.ping)...")
            ping_msg = {
                "action": "system.ping",
                "request_id": f"test_ping_{int(datetime.now().timestamp())}",
                "data": {}
            }
            await websocket.send(json.dumps(ping_msg))
            print(f"   发送: {json.dumps(ping_msg)}")

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"   接收: {response}\n")

            # 测试 2: 获取项目列表
            print("3. 测试获取项目列表 (project.list)...")
            project_msg = {
                "action": "project.list",
                "request_id": f"test_project_{int(datetime.now().timestamp())}",
                "data": {
                    "page": 1,
                    "page_size": 5
                }
            }
            await websocket.send(json.dumps(project_msg))
            print(f"   发送: {json.dumps(project_msg)}")

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            print(f"   接收: {json.dumps(response_data, indent=2, ensure_ascii=False)}\n")

            # 测试 3: 获取可用接口
            print("4. 测试获取可用接口 (system.capabilities)...")
            cap_msg = {
                "action": "system.capabilities",
                "request_id": f"test_cap_{int(datetime.now().timestamp())}",
                "data": {}
            }
            await websocket.send(json.dumps(cap_msg))
            print(f"   发送: {json.dumps(cap_msg)}")

            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"   接收: {response}\n")

            print("=" * 80)
            print("所有测试完成!")
            print("=" * 80)

    except websockets.exceptions.WebSocketException as e:
        print(f"   [ERROR] WebSocket 错误: {e}")
    except asyncio.TimeoutError:
        print(f"   [ERROR] 响应超时")
    except Exception as e:
        print(f"   [ERROR] {type(e).__name__}: {e}")


if __name__ == "__main__":
    # 检查是否安装了 websockets 库
    try:
        import websockets
    except ImportError:
        print("错误: 需要安装 websockets 库")
        print("请运行: pip install websockets")
        exit(1)

    # 运行测试
    asyncio.run(test_websocket())
