"""
动捕任务数据模型
"""
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd


@dataclass
class TaskData:
    """单个任务数据模型"""
    task_id: str = ""
    task_name_en: str = ""
    task_name_cn: str = ""
    file_size_mb: str = ""
    total_action_slices: str = ""
    duration_s: str = ""
    scenarios: str = ""
    action_text_en: str = ""
    action_text_cn: str = ""
    object_en: str = ""
    object_cn: str = ""
    data_frame_fps: str = ""
    hand_usage: str = ""
    rgb_cams: str = ""
    depth_cams: str = ""
    wrist_cams: str = ""
    data_collect_method: str = ""
    camera_calibration: str = ""
    pose_joint_angles: str = ""
    kinematic_params: str = ""
    tactile_feedback: str = ""

    @classmethod
    def from_excel_row(cls, row_data: dict) -> 'TaskData':
        """从Excel行数据创建TaskData实例"""
        return cls(
            task_id=str(row_data.get('task_id', '')),
            task_name_en=str(row_data.get('task_name_EN', '')),
            task_name_cn=str(row_data.get('task_name_CN', '')),
            file_size_mb=str(row_data.get('file size(MB)', '')),
            total_action_slices=str(row_data.get('total_action-slices', '')),
            duration_s=str(row_data.get('duration(s)', '')),
            scenarios=str(row_data.get('scenarios', '')),
            action_text_en=str(row_data.get('example of action_text', '')),
            action_text_cn=str(row_data.get('example of action_text_CN', '')),
            object_en=str(row_data.get('object', '')),
            object_cn=str(row_data.get('object_CN', '')),
            data_frame_fps=str(row_data.get('data frame(fps)', '')),
            hand_usage=str(row_data.get('hand usage', '')),
            rgb_cams=str(row_data.get('# RGB Cams', '')),
            depth_cams=str(row_data.get('# Depth Cams', '')),
            wrist_cams=str(row_data.get('# Wrist Cams', '')),
            data_collect_method=str(row_data.get('Data Collect Method', '')),
            camera_calibration=str(row_data.get('Has Camera Calibration?', '')),
            pose_joint_angles=str(row_data.get('pose and joint angles', '')),
            kinematic_params=str(row_data.get('Kinematic Parameters', '')),
            tactile_feedback=str(row_data.get('Tactile Feedback(触觉反馈)', ''))
        )

    def get_display_name(self) -> str:
        """获取显示名称"""
        if self.task_name_en:
            return f"[{self.task_id}] {self.task_name_en}"
        return f"Task {self.task_id}"

    def get_all_properties(self) -> List[tuple]:
        """获取所有属性的键值对列表"""
        return [
            ("任务ID", self.task_id),
            ("任务名称(英文)", self.task_name_en),
            ("任务名称(中文)", self.task_name_cn),
            ("文件大小(MB)", self.file_size_mb),
            ("动作片段总数", self.total_action_slices),
            ("持续时间(秒)", self.duration_s),
            ("场景", self.scenarios),
            ("动作文本(英文)", self.action_text_en),
            ("动作文本(中文)", self.action_text_cn),
            ("对象(英文)", self.object_en),
            ("对象(中文)", self.object_cn),
            ("数据帧率(FPS)", self.data_frame_fps),
            ("手部使用", self.hand_usage),
            ("RGB相机", self.rgb_cams),
            ("深度相机", self.depth_cams),
            ("手腕相机", self.wrist_cams),
            ("数据收集方法", self.data_collect_method),
            ("摄像头校准", self.camera_calibration),
            ("姿态关节角度", self.pose_joint_angles),
            ("运动学参数", self.kinematic_params),
            ("触觉反馈", self.tactile_feedback)
        ]


class TaskDataManager:
    """任务数据管理器"""
    
    def __init__(self):
        self.tasks: List[TaskData] = []
        self.current_task: Optional[TaskData] = None

    def load_from_excel(self, file_path: str) -> bool:
        """从Excel文件加载数据"""
        try:
            print(f"[DEBUG] 开始加载Excel文件: {file_path}")
            
            # 读取Excel文件，不跳过任何行，让pandas自动识别列名
            df = pd.read_excel(file_path)
            print(f"[DEBUG] Excel文件读取成功，数据形状: {df.shape}")
            print(f"[DEBUG] 原始列名: {list(df.columns)}")
            
            # 检查是否有正确的列名
            if 'task_id' not in df.columns:
                print(f"[DEBUG] 未找到task_id列，尝试查找包含task_id的行作为列名")
                # 查找包含task_id的行
                for i, row in df.iterrows():
                    if 'task_id' in str(row.values):
                        print(f"[DEBUG] 在第{i}行找到task_id，使用该行作为列名")
                        # 使用该行作为列名
                        df.columns = df.iloc[i]
                        # 删除该行数据
                        df = df.drop(i)
                        # 重置索引
                        df = df.reset_index(drop=True)
                        break
                else:
                    print(f"[ERROR] 未找到包含task_id的行")
                    return False
            
            print(f"[DEBUG] 修正后的列名: {list(df.columns)}")
            
            # 打印前几行数据用于调试
            print(f"[DEBUG] 前5行数据:")
            print(df.head())
            
            self.tasks.clear()
            
            valid_tasks = 0
            invalid_tasks = 0
            
            for index, row in df.iterrows():
                print(f"[DEBUG] 处理第{index}行数据...")
                row_dict = row.to_dict()
                print(f"[DEBUG] 行数据: {row_dict}")
                
                task = TaskData.from_excel_row(row_dict)
                print(f"[DEBUG] 创建的任务对象 - task_id: '{task.task_id}', task_name_en: '{task.task_name_en}'")
                
                if task.task_id and str(task.task_id).strip():  # 只添加有ID的任务
                    self.tasks.append(task)
                    valid_tasks += 1
                    print(f"[DEBUG] 有效任务 #{valid_tasks}: {task.get_display_name()}")
                else:
                    invalid_tasks += 1
                    print(f"[DEBUG] 无效任务 #{invalid_tasks}: task_id为空或无效")
            
            print(f"[DEBUG] 导入完成 - 有效任务: {valid_tasks}, 无效任务: {invalid_tasks}, 总任务数: {len(self.tasks)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Load excel error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_scenarios(self) -> List[str]:
        """获取所有场景类型"""
        scenarios = set()
        for task in self.tasks:
            if task.scenarios:
                scenarios.add(task.scenarios)
        return sorted(list(scenarios))

    def get_tasks_by_scenario(self, scenario: str) -> List[TaskData]:
        """根据场景获取任务列表"""
        if scenario == "All":
            return self.tasks
        return [task for task in self.tasks if task.scenarios == scenario]

    def get_task_by_id(self, task_id: str) -> Optional[TaskData]:
        """根据ID获取任务"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def set_current_task(self, task: TaskData):
        """设置当前任务"""
        self.current_task = task