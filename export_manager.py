"""
数据导出管理器
负责从数据库导出TaskInfo和视频文件到指定目录
"""

import os
import json
import shutil
import glob
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtCore import QCoreApplication


class ExportManager:
    """数据导出管理器"""
    
    def __init__(self, db_controller, parent_widget=None):
        """
        初始化导出管理器
        
        Args:
            db_controller: 数据库控制器实例
            parent_widget: 父窗口组件，用于显示对话框
        """
        self.db_controller = db_controller
        self.parent_widget = parent_widget
    
    def export_data(self, takelist=None, open_folder=None):
        """
        导出数据到选定文件夹
        
        Args:
            takelist: 录制列表，用于获取业务任务ID
            open_folder: 默认打开文件夹路径
        """
        # 选择导出根目录
        export_dir = QFileDialog.getExistingDirectory(
            self.parent_widget, 
            "选择导出文件夹", 
            open_folder or os.getcwd()
        )
        if not export_dir:
            return
        
        root_dir = os.path.join(export_dir, 'task_info')
        os.makedirs(root_dir, exist_ok=True)
        
        try:
            # 获取业务任务ID列表
            business_task_ids = self._get_business_task_ids(takelist)
            
            if not business_task_ids:
                QMessageBox.information(
                    self.parent_widget, 
                    "导出", 
                    "没有可导出的任务"
                )
                return
            
            # 导出task_info数据
            exported_count = self._export_task_info_data(root_dir, business_task_ids)
            
            # 导出视频文件
            self._export_video_files(export_dir, business_task_ids, exported_count)
            
        except Exception as e:
            QMessageBox.warning(
                self.parent_widget, 
                "导出失败", 
                f"导出发生异常: {e}"
            )
    
    def _get_business_task_ids(self, takelist):
        """
        获取业务任务ID列表
        
        Args:
            takelist: 录制列表
            
        Returns:
            list: 业务任务ID列表
        """
        business_task_ids = []
        
        # 优先从当前会话的录制条目收集业务task_id
        if takelist:
            for take in takelist:
                if getattr(take, '_task_id', None):
                    business_task_ids.append(str(take._task_id))
            # 去重
            business_task_ids = list(dict.fromkeys(business_task_ids))
        
        # 如果当前会话没有可用业务ID，则从后端读取所有TaskInfo
        if not business_task_ids:
            resp = self.db_controller.list_task_infos(limit=1000, offset=0) or []
            if isinstance(resp, dict):
                items = resp.get('results', []) or []
            elif isinstance(resp, list):
                items = resp
            else:
                items = []
            
            biz_set = []
            for it in items:
                try:
                    if isinstance(it, dict) and it.get('task_id'):
                        biz_set.append(str(it.get('task_id')))
                except Exception:
                    continue
            business_task_ids = list(dict.fromkeys(biz_set))
        
        return business_task_ids
    
    def _export_task_info_data(self, root_dir, business_task_ids):
        """
        导出task_info数据
        
        Args:
            root_dir: 导出根目录
            business_task_ids: 业务任务ID列表
            
        Returns:
            int: 导出的任务数量
        """
        exported = 0
        total_tasks = len(business_task_ids)
        
        # 创建进度条
        progress = QProgressDialog("正在导出 task_info...", None, 0, total_tasks, self.parent_widget)
        progress.setWindowTitle("导出")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        for idx, biz_id in enumerate(business_task_ids, start=1):
            progress.setLabelText(f"正在导出 task_info: {biz_id} ({idx}/{total_tasks})")
            progress.setValue(idx - 1)
            QCoreApplication.processEvents()
            
            # 从后端拉取全部TaskInfo并过滤出该业务ID的所有episode
            resp = self.db_controller.list_task_infos(limit=2000, offset=0) or []
            if isinstance(resp, dict):
                items = resp.get('results', []) or []
            elif isinstance(resp, list):
                items = resp
            else:
                items = []
            
            matched = [it for it in items if isinstance(it, dict) and str(it.get('task_id')) == str(biz_id)]
            if not matched:
                continue
            
            # 构建导出数据
            export_array = []
            for data in matched:
                export_array.append({
                    "episode_id": int(data.get('episode_id') or data.get('id')),
                    "label_info": {"action_config": data.get('action_config', [])},
                    "task_name": data.get('task_name', ''),
                    "init_scene_text": data.get('init_scene_text', '')
                })
            
            # 写入文件
            output_file = os.path.join(root_dir, f"{biz_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_array, f, ensure_ascii=False, indent=2)
            exported += 1
        
        progress.setValue(total_tasks)
        return exported
    
    def _export_video_files(self, export_dir, business_task_ids, task_info_count):
        """
        导出视频文件到指定目录结构
        
        Args:
            export_dir: 导出根目录
            business_task_ids: 业务任务ID列表
            task_info_count: 已导出的任务信息数量
        """
        try:
            # 获取所有observations数据
            observations_data = self.db_controller.list_observations(limit=2000, offset=0) or []
            if not observations_data:
                print("没有找到observations数据，跳过视频文件导出")
                QMessageBox.information(
                    self.parent_widget, 
                    "导出完成", 
                    f"已导出 {task_info_count} 个任务信息到: {export_dir}"
                )
                return
            
            # 检查observations数据格式
            if not isinstance(observations_data, list):
                print(f"observations数据格式错误: {type(observations_data)}")
                QMessageBox.information(
                    self.parent_widget, 
                    "导出完成", 
                    f"已导出 {task_info_count} 个任务信息到: {export_dir}"
                )
                return
            
            # 按task_id分组observations
            observations_by_task = self._group_observations_by_task(observations_data, business_task_ids)
            
            if not observations_by_task:
                print("没有找到匹配的observations数据，跳过视频文件导出")
                QMessageBox.information(
                    self.parent_widget, 
                    "导出完成", 
                    f"已导出 {task_info_count} 个任务信息到: {export_dir}"
                )
                return
            
            # 创建observations目录并导出视频文件
            observations_dir = os.path.join(export_dir, 'observations')
            os.makedirs(observations_dir, exist_ok=True)
            
            exported_episodes = self._copy_video_files(observations_dir, observations_by_task)
            
            QMessageBox.information(
                self.parent_widget, 
                "导出完成", 
                f"已导出 {task_info_count} 个任务信息和 {exported_episodes} 个episode的视频文件到: {export_dir}"
            )
            
        except Exception as e:
            print(f"导出视频文件失败: {e}")
            QMessageBox.warning(
                self.parent_widget, 
                "导出失败", 
                f"导出视频文件失败: {e}"
            )
    
    def _group_observations_by_task(self, observations_data, business_task_ids):
        """
        按task_id分组observations数据
        
        Args:
            observations_data: observations数据列表
            business_task_ids: 业务任务ID列表
            
        Returns:
            dict: 按task_id分组的observations数据
        """
        observations_by_task = {}
        
        for obs in observations_data:
            # 检查obs是否为字典类型
            if not isinstance(obs, dict):
                print(f"跳过非字典类型的observation数据: {type(obs)}")
                continue
            
            # 通过task_info获取task_id
            task_info_id = obs.get('task_info')
            if task_info_id:
                # 获取对应的task_info
                task_info = self.db_controller.get_task(task_info_id)
                if task_info and isinstance(task_info, dict):
                    biz_task_id = str(task_info.get('task_id', ''))
                    if biz_task_id in business_task_ids:
                        if biz_task_id not in observations_by_task:
                            observations_by_task[biz_task_id] = []
                        observations_by_task[biz_task_id].append(obs)
        
        return observations_by_task
    
    def _copy_video_files(self, observations_dir, observations_by_task):
        """
        复制视频文件到目标目录
        
        Args:
            observations_dir: observations目录路径
            observations_by_task: 按task_id分组的observations数据
            
        Returns:
            int: 导出的episode数量
        """
        # 计算总进度
        total_episodes = sum(len(episodes) for episodes in observations_by_task.values())
        progress = QProgressDialog("正在导出视频文件...", None, 0, total_episodes, self.parent_widget)
        progress.setWindowTitle("导出视频")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        exported_episodes = 0
        
        for biz_task_id, episodes in observations_by_task.items():
            # 创建task_id目录
            task_dir = os.path.join(observations_dir, biz_task_id)
            os.makedirs(task_dir, exist_ok=True)
            
            for episode in episodes:
                # 检查episode是否为字典类型
                if not isinstance(episode, dict):
                    print(f"跳过非字典类型的episode数据: {type(episode)}")
                    continue
                
                episode_id = str(episode.get('episode_id', ''))
                video_path = episode.get('video_path', '')
                depth_path = episode.get('depth_path', '')
                
                # 检查是否有有效的视频或深度路径
                has_video_files = video_path and os.path.exists(video_path)
                has_depth_files = depth_path and os.path.exists(depth_path)
                
                if not has_video_files and not has_depth_files:
                    print(f"Episode {episode_id} 没有有效的视频或深度文件路径，跳过")
                    continue
                
                # 创建episode_id目录
                episode_dir = os.path.join(task_dir, episode_id)
                videos_dir = os.path.join(episode_dir, 'videos')
                depth_dir = os.path.join(episode_dir, 'depth')
                os.makedirs(videos_dir, exist_ok=True)
                os.makedirs(depth_dir, exist_ok=True)
                
                # 更新进度
                exported_episodes += 1
                progress.setLabelText(f"正在导出视频: {biz_task_id}/{episode_id} ({exported_episodes}/{total_episodes})")
                progress.setValue(exported_episodes - 1)
                QCoreApplication.processEvents()
                
                # 复制视频文件
                if has_video_files:
                    self._copy_files_from_directory(video_path, videos_dir, "视频")
                
                # 复制深度文件
                if has_depth_files:
                    self._copy_files_from_directory(depth_path, depth_dir, "深度")
        
        progress.setValue(total_episodes)
        return exported_episodes
    
    def _copy_files_from_directory(self, file_path, dest_dir, file_type):
        """
        从指定目录复制所有文件到目标目录
        
        Args:
            file_path: 源文件路径
            dest_dir: 目标目录
            file_type: 文件类型（用于日志）
        """
        try:
            # 获取目录下所有文件
            source_dir = os.path.dirname(file_path)
            if os.path.exists(source_dir):
                files = glob.glob(os.path.join(source_dir, '*'))
                for file_path in files:
                    if os.path.isfile(file_path):
                        filename = os.path.basename(file_path)
                        dest_path = os.path.join(dest_dir, filename)
                        shutil.copy2(file_path, dest_path)
                        print(f"复制{file_type}文件: {file_path} -> {dest_path}")
            else:
                print(f"{file_type}目录不存在: {source_dir}")
        except Exception as e:
            print(f"复制{file_type}文件失败: {e}")
