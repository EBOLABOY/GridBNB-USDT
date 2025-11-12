"""
简化的API测试脚本 - 快速验证核心功能
"""

import os
import sys
import asyncio

# 设置测试环境变量（在导入其他模块之前）
os.environ['PYTEST_CURRENT_TEST'] = 'test_api_simple.py'
os.environ['BINANCE_API_KEY'] = 'a' * 64
os.environ['BINANCE_API_SECRET'] = 'b' * 64

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from aiohttp import web, ClientSession
from src.services.web_server_v2 import create_web_app


async def test_api():
    """快速测试API"""
    print("\n=== Starting API Test ===\n")

    # 启动测试服务器
    print("1. Starting test server...")
    app = await create_web_app(traders={})
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 58182)
    await site.start()
    print("   Server started on http://127.0.0.1:58182")

    # 等待服务器启动
    await asyncio.sleep(0.5)

    results = []

    async with ClientSession() as session:
        # 测试1: 登录
        print("\n2. Testing login...")
        try:
            async with session.post(
                'http://127.0.0.1:58182/api/auth/login',
                json={'username': 'admin', 'password': 'admin123'}
            ) as resp:
                data = await resp.json()
                if resp.status == 200 and 'access_token' in data:
                    token = data['access_token']
                    print(f"   [OK] Login successful")
                    print(f"   Token: {token[:20]}...")
                    results.append(('Login', True))
                else:
                    print(f"   [FAIL] Login failed: {resp.status}")
                    print(f"   Response: {data}")
                    results.append(('Login', False))
                    await runner.cleanup()
                    return results
        except Exception as e:
            print(f"   [ERROR] {e}")
            results.append(('Login', False))
            await runner.cleanup()
            return results

        # 测试2: 获取当前用户
        print("\n3. Testing get current user...")
        try:
            headers = {'Authorization': f'Bearer {token}'}
            async with session.get(
                'http://127.0.0.1:58182/api/auth/me',
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   [OK] User: {data.get('username')}")
                    results.append(('Get User', True))
                else:
                    print(f"   [FAIL] Status: {resp.status}")
                    results.append(('Get User', False))
        except Exception as e:
            print(f"   [ERROR] {e}")
            results.append(('Get User', False))

        # 测试3: 获取配置列表
        print("\n4. Testing get configs...")
        try:
            async with session.get(
                'http://127.0.0.1:58182/api/configs',
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   [OK] Configs: {data.get('total', 0)} items")
                    results.append(('Get Configs', True))
                else:
                    print(f"   [FAIL] Status: {resp.status}")
                    results.append(('Get Configs', False))
        except Exception as e:
            print(f"   [ERROR] {e}")
            results.append(('Get Configs', False))

        # 测试4: 未授权访问
        print("\n5. Testing unauthorized access...")
        try:
            async with session.get(
                'http://127.0.0.1:58182/api/configs'
            ) as resp:
                if resp.status == 401:
                    print(f"   [OK] Correctly rejected (401)")
                    results.append(('Unauthorized', True))
                else:
                    print(f"   [FAIL] Expected 401, got {resp.status}")
                    results.append(('Unauthorized', False))
        except Exception as e:
            print(f"   [ERROR] {e}")
            results.append(('Unauthorized', False))

    # 关闭服务器
    await runner.cleanup()
    print("\n6. Server stopped")

    # 输出结果
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print("=" * 50)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 50)

    return passed == total


if __name__ == '__main__':
    try:
        success = asyncio.run(test_api())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
