"""
Web认证功能测试
"""
import pytest
import base64
from unittest.mock import MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from src.services.web_server import auth_required


class TestWebAuthentication(AioHTTPTestCase):
    """测试Web认证功能"""
    
    async def get_application(self):
        """创建测试应用"""
        app = web.Application()
        
        @auth_required
        async def protected_handler(request):
            return web.Response(text="Protected content")
        
        app.router.add_get('/protected', protected_handler)
        return app
    
    async def test_no_auth_configured(self):
        """测试未配置认证时的行为"""
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = None
            mock_settings.WEB_PASSWORD = None
            
            resp = await self.client.request("GET", "/protected")
            assert resp.status == 200
            text = await resp.text()
            assert text == "Protected content"
    
    async def test_missing_auth_header(self):
        """测试缺少认证头的情况"""
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = "admin"
            mock_settings.WEB_PASSWORD = "password"
            
            resp = await self.client.request("GET", "/protected")
            assert resp.status == 401
            assert 'WWW-Authenticate' in resp.headers
    
    async def test_valid_authentication(self):
        """测试有效认证"""
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = "admin"
            mock_settings.WEB_PASSWORD = "password"
            
            # 创建有效的Basic认证头
            credentials = base64.b64encode(b"admin:password").decode('utf-8')
            headers = {'Authorization': f'Basic {credentials}'}
            
            resp = await self.client.request("GET", "/protected", headers=headers)
            assert resp.status == 200
            text = await resp.text()
            assert text == "Protected content"
    
    async def test_invalid_credentials(self):
        """测试无效凭据"""
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = "admin"
            mock_settings.WEB_PASSWORD = "password"
            
            # 创建无效的Basic认证头
            credentials = base64.b64encode(b"admin:wrongpassword").decode('utf-8')
            headers = {'Authorization': f'Basic {credentials}'}
            
            resp = await self.client.request("GET", "/protected", headers=headers)
            assert resp.status == 401
    
    async def test_malformed_auth_header(self):
        """测试格式错误的认证头"""
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = "admin"
            mock_settings.WEB_PASSWORD = "password"
            
            # 测试不同的错误格式
            test_cases = [
                "Bearer token",  # 错误的认证类型
                "Basic",         # 缺少凭据
                "Basic invalid_base64",  # 无效的base64
                "Basic " + base64.b64encode(b"no_colon").decode('utf-8'),  # 缺少冒号
            ]
            
            for auth_header in test_cases:
                headers = {'Authorization': auth_header}
                resp = await self.client.request("GET", "/protected", headers=headers)
                assert resp.status == 401


class TestAuthDecorator:
    """测试认证装饰器的单元测试"""
    
    @pytest.mark.asyncio
    async def test_auth_decorator_no_config(self):
        """测试装饰器在无配置时的行为"""
        @auth_required
        async def test_handler(request):
            return web.Response(text="success")
        
        # 模拟请求
        request = MagicMock()
        request.headers = {}
        
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = None
            mock_settings.WEB_PASSWORD = None
            
            response = await test_handler(request)
            assert response.text == "success"
    
    @pytest.mark.asyncio
    async def test_auth_decorator_with_valid_auth(self):
        """测试装饰器在有效认证时的行为"""
        @auth_required
        async def test_handler(request):
            return web.Response(text="success")
        
        # 创建有效的认证头
        credentials = base64.b64encode(b"admin:password").decode('utf-8')
        request = MagicMock()
        request.headers = {'Authorization': f'Basic {credentials}'}
        
        with patch('src.services.web_server.settings') as mock_settings:
            mock_settings.WEB_USER = "admin"
            mock_settings.WEB_PASSWORD = "password"
            
            response = await test_handler(request)
            assert response.text == "success"


if __name__ == '__main__':
    pytest.main([__file__])
