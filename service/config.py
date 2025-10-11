# service/config.py
import os
from typing import Optional


class APIConfig:
    """API配置管理"""
    
    def __init__(self):
        # API后端基础URL
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:8000/api')
        
        # API超时设置
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))
        
        # 重试设置
        self.max_retries = int(os.getenv('API_MAX_RETRIES', '3'))
        
        # 认证设置（如果需要）
        self.api_key = os.getenv('API_KEY', '')
        self.api_secret = os.getenv('API_SECRET', '')
    
    def get_api_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"
    
    def get_headers(self) -> dict:
        """获取请求头"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers


# 全局配置实例
api_config = APIConfig()
