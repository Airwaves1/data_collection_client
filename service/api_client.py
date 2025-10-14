# service/api_client.py
import requests
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime


class DataCollectionAPIClient:
    """数据采集API客户端 - 封装HTTP请求"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api", timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """发送HTTP请求，包含重试机制"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, timeout=self.timeout)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, timeout=self.timeout)
                elif method.upper() == 'PATCH':
                    response = self.session.patch(url, json=data, timeout=self.timeout)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, timeout=self.timeout)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                response.raise_for_status()
                
                if response.content:
                    return response.json()
                return None
                
            except requests.exceptions.RequestException as e:
                print(f"API请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"API请求最终失败: {url}")
                    return None
        
        return None
    
    def _handle_response(self, result: Optional[Dict], operation: str) -> Optional[Any]:
        """处理API响应"""
        if result is None:
            print(f"{operation} 失败: API请求无响应")
            return None
        return result
    
    # -------- collector API --------
    def upsert_collector(self, collector: Dict[str, Any]) -> Optional[int]:
        """创建或更新采集者"""
        if collector.get("id"):
            endpoint = f"collectors/{collector['id']}/"
            result = self._make_request('PUT', endpoint, collector)
        else:
            endpoint = "collectors/"
            result = self._make_request('POST', endpoint, collector)
        
        return result.get('id') if result else None
    
    def get_collector(self, collector_id: int) -> Optional[Dict[str, Any]]:
        """获取采集者信息"""
        endpoint = f"collectors/{collector_id}/"
        return self._make_request('GET', endpoint)
    
    def list_collectors(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """获取采集者列表"""
        endpoint = "collectors/list_collectors/"
        params = {'limit': limit, 'offset': offset}
        result = self._make_request('GET', endpoint, params=params)
        return result if result else []
    
    def register_collector(self, collector_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """用户注册"""
        endpoint = "collectors/register/"
        return self._make_request('POST', endpoint, collector_data)
    
    def login_collector(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录"""
        endpoint = "collectors/login/"
        data = {'username': username, 'password': password}
        return self._make_request('POST', endpoint, data)
    
    # -------- task_info API --------
    def create_task_info(self, task: Dict[str, Any]) -> Optional[int]:
        """创建任务信息"""
        endpoint = "tasks/"
        result = self._make_request('POST', endpoint, task)
        return result.get('id') if result else None
    
    def update_task_info_links(self, task_info_id: int, links: Dict[str, Optional[int]]) -> bool:
        """更新任务信息的外键链接"""
        endpoint = f"tasks/{task_info_id}/update_links/"
        result = self._make_request('PATCH', endpoint, links)
        return result is not None
    
    def get_task_info_by_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """根据episode_id获取任务信息"""
        endpoint = "tasks/by_episode/"
        params = {'episode_id': episode_id}
        return self._make_request('GET', endpoint, params=params)
    
    def get_task_info_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据业务task_id获取任务信息"""
        endpoint = "tasks/by_task_id/"
        params = {'task_id': task_id}
        return self._make_request('GET', endpoint, params=params)
    
    def list_tasks_by_collector(self, collector_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """根据采集者ID获取任务列表"""
        endpoint = "tasks/by_collector/"
        params = {'collector_id': collector_id, 'limit': limit, 'offset': offset}
        result = self._make_request('GET', endpoint, params=params)
        return result if result else []
    
    # -------- observations API --------
    def create_observations(self, obs: Dict[str, Any]) -> Optional[int]:
        """创建观察数据"""
        endpoint = "observations/"
        result = self._make_request('POST', endpoint, obs)
        return result.get('id') if result else None
    
    def list_observations(self, limit: int = 2000, offset: int = 0) -> List[Dict[str, Any]]:
        """获取观察数据列表"""
        endpoint = "observations/"
        params = {'limit': limit, 'offset': offset}
        result = self._make_request('GET', endpoint, params=params)
        return result if result else []
    
    def get_observations_by_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """根据episode_id获取观察数据"""
        endpoint = "observations/"
        params = {'episode_id': episode_id}
        result = self._make_request('GET', endpoint, params=params)
        return result[0] if result and len(result) > 0 else None
    
    # -------- parameters API --------
    def create_parameters(self, params: Dict[str, Any]) -> Optional[int]:
        """创建参数数据"""
        endpoint = "parameters/"
        result = self._make_request('POST', endpoint, params)
        return result.get('id') if result else None
    
    # -------- skeletonData API --------
    def create_skeleton_data(self, data: Dict[str, Any]) -> Optional[int]:
        """创建骨骼数据"""
        endpoint = "skeleton-data/"
        result = self._make_request('POST', endpoint, data)
        return result.get('id') if result else None
    
    # -------- kinematicData API --------
    def create_kinematic_data(self, data: Dict[str, Any]) -> Optional[int]:
        """创建运动学数据"""
        endpoint = "kinematic-data/"
        result = self._make_request('POST', endpoint, data)
        return result.get('id') if result else None
    
    # -------- imu API --------
    def create_imu(self, imu: Dict[str, Any]) -> Optional[int]:
        """创建IMU数据"""
        endpoint = "imu-data/"
        result = self._make_request('POST', endpoint, imu)
        return result.get('id') if result else None
    
    # -------- tactile_feedback API --------
    def create_tactile_feedback(self, tf: Dict[str, Any]) -> Optional[int]:
        """创建触觉反馈数据"""
        endpoint = "tactile-feedback/"
        result = self._make_request('POST', endpoint, tf)
        return result.get('id') if result else None
    
    # -------- 便捷组合 API --------
    def save_full_episode(self, collector_id: int, episode_id: str, task_id: str, task_name: str,
                          init_scene_text: str, action_config: List[dict], task_status: str = 'pending') -> Optional[int]:
        """一次性写入 task_info（不含子表），返回 task_info.id"""
        endpoint = "tasks/save_full_episode/"
        data = {
            'collector_id': collector_id,
            'task_id': task_id,
            'task_name': task_name,
            'init_scene_text': init_scene_text,
            'action_config': action_config,
            'task_status': task_status,
        }
        result = self._make_request('POST', endpoint, data)
        return result.get('task_id') if result else None
    
    def update_task_status(self, task_id: int, task_status: str) -> bool:
        """更新任务状态"""
        endpoint = f"tasks/{task_id}/update_status/"
        data = {'task_status': task_status}
        result = self._make_request('PATCH', endpoint, data)
        return result is not None
    
    def update_task_by_task_id(self, task_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据业务task_id更新任务信息"""
        endpoint = "tasks/update_by_task_id/"
        data = {'task_id': task_id, **task_data}
        return self._make_request('PATCH', endpoint, data)

    # -------- 读取 API --------
    def list_task_infos(self, limit: int = 500, offset: int = 0):
        """获取任务信息列表"""
        endpoint = "tasks/"
        params = {"limit": limit, "offset": offset}
        return self._make_request('GET', endpoint, params=params)

    def get_task_info(self, task_id: int):
        """获取单个任务信息"""
        endpoint = f"tasks/{task_id}/"
        return self._make_request('GET', endpoint)

    def get_collector(self, collector_id: int):
        """获取采集者信息"""
        endpoint = f"collectors/{collector_id}/"
        return self._make_request('GET', endpoint)
