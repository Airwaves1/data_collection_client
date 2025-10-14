# service/db_controller.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from .api_client import DataCollectionAPIClient


class DBController:
    """
    数据采集业务控制器 - 基于Django REST API
    所有操作都通过HTTP API与后端通信
    """
    
    def __init__(self, api_client: Optional[DataCollectionAPIClient] = None):
        self.api_client = api_client or DataCollectionAPIClient()

    # -------- collector --------
    def upsert_collector(self, collector: Dict[str, Any]) -> int:
        """
        collector: {
            'id': Optional[int],  # 可选，如果存在则更新
            'collector_organization': str,
            'collector_id': str,
            'collector_name': str,
            'target_customer': Optional[str],
        }
        返回: collector.id
        """
        result = self.api_client.upsert_collector(collector)
        return result if result else 0

    def get_collector(self, collector_id: int) -> Optional[Dict[str, Any]]:
        """获取采集者信息"""
        return self.api_client.get_collector(collector_id)

    def list_collectors(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """获取采集者列表"""
        return self.api_client.list_collectors(limit, offset)
    
    def register_collector(self, collector_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """用户注册"""
        return self.api_client.register_collector(collector_data)
    
    def login_collector(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户登录"""
        return self.api_client.login_collector(username, password)

    # -------- task_info (核心元数据) --------
    def create_task_info(self, task: Dict[str, Any]) -> int:
        """
        task: {
          'collector_id': int,
          'episode_id': str,
          'task_name': str,
          'init_scene_text': Optional[str],
          'action_config': list|dict,   # 会以JSON写入
          # 以下外键字段可为空，后续由各子模块写入后 "回填更新"
          'observations_id': Optional[int],
          'parameters_id': Optional[int],
          'skeletonData_id': Optional[int],
          'kinematicData_id': Optional[int],
          'imu_id': Optional[int],
          'tactile_feedback_id': Optional[int],
          'created_at': Optional[datetime],   # 可不传
          'completed_at': Optional[datetime], # 可不传
        }
        返回: task_info.id
        """
        result = self.api_client.create_task_info(task)
        return result if result else 0

    def update_task_info_links(self, task_info_id: int, links: Dict[str, Optional[int]]) -> None:
        """
        回填外键：observations_id / parameters_id / skeletonData_id / kinematicData_id / imu_id / tactile_feedback_id
        links 形如: {'observations_id': 1, 'parameters_id': None, ...}
        """
        self.api_client.update_task_info_links(task_info_id, links)

    def get_task_info_by_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """根据episode_id获取任务信息"""
        return self.api_client.get_task_info_by_episode(episode_id)
    
    def get_task_info_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据业务task_id获取任务信息"""
        return self.api_client.get_task_info_by_task_id(task_id)

    def list_tasks_by_collector(self, collector_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """根据采集者ID获取任务列表"""
        return self.api_client.list_tasks_by_collector(collector_id, limit, offset)

    # -------- observations --------
    def create_observations(self, obs: Dict[str, Any]) -> int:
        """
        obs: { 'task_id': int, 'episode_id': str, 'video_path': str, 'depth_path': Optional[str] }
        """
        result = self.api_client.create_observations(obs)
        return result if result else 0
    
    def list_observations(self, limit: int = 2000, offset: int = 0) -> List[Dict[str, Any]]:
        """获取观察数据列表"""
        return self.api_client.list_observations(limit, offset)
    
    def get_observations_by_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """根据episode_id获取观察数据"""
        return self.api_client.get_observations_by_episode(episode_id)

    # -------- parameters --------
    def create_parameters(self, params: Dict[str, Any]) -> int:
        """
        params: { 'task_id': int, 'episode_id': str, 'parameters_path': str }
        """
        result = self.api_client.create_parameters(params)
        return result if result else 0

    # -------- skeletonData --------
    def create_skeleton_data(self, data: Dict[str, Any]) -> int:
        """
        data: { 'task_id': int, 'episode_id': str, 'fbx_path': str, 'bvh_path': str, 'csv_path': str, 'npy_path': str }
        """
        result = self.api_client.create_skeleton_data(data)
        return result if result else 0

    # -------- kinematicData --------
    def create_kinematic_data(self, data: Dict[str, Any]) -> int:
        """
        data: { 'task_id': int, 'episode_id': str, 'path': str }
        """
        result = self.api_client.create_kinematic_data(data)
        return result if result else 0

    # -------- imu --------
    def create_imu(self, imu: Dict[str, Any]) -> int:
        """
        imu: { 'task_id': int, 'episode_id': str, 'leftHandIMU_path': str, 'rightHandIMU_path': str }
        """
        result = self.api_client.create_imu(imu)
        return result if result else 0

    # -------- tactile_feedback --------
    def create_tactile_feedback(self, tf: Dict[str, Any]) -> int:
        """
        tf: { 'task_id': int, 'episode_id': str, 'leftHandTac_path': str, 'rightHandTac_path': str }
        """
        result = self.api_client.create_tactile_feedback(tf)
        return result if result else 0

    # -------- 便捷组合 API --------
    def save_full_episode(self, collector_id: int, episode_id: str, task_id: str, task_name: str,
                          init_scene_text: str, action_config: List[dict], task_status: str = 'pending') -> int:
        """
        一次性写入 task_info（不含子表），返回 task_info.id
        episode_id参数保留用于兼容性，但实际由后端自动生成
        """
        result = self.api_client.save_full_episode(collector_id, "", task_id, task_name, init_scene_text, action_config, task_status)
        return result if result else 0
    
    def update_task_status(self, task_id: int, task_status: str) -> bool:
        """更新任务状态"""
        return self.api_client.update_task_status(task_id, task_status)
    
    def update_task_by_task_id(self, task_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据业务task_id更新任务信息"""
        return self.api_client.update_task_by_task_id(task_id, task_data)

    # -------- 读取 API --------
    def get_task_info(self, task_id: int):
        return self.api_client.get_task_info(task_id)

    def list_task_infos(self, limit: int = 500, offset: int = 0):
        return self.api_client.list_task_infos(limit, offset)

    def get_collector(self, collector_id: int):
        return self.api_client.get_collector(collector_id)