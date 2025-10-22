from datetime import datetime


class ActionInfo:
    def __init__(self, action_text, start_frame, end_frame):
        self.action_text = action_text
        self.start_frame = start_frame
        self.end_frame = end_frame

    def to_dict(self):
        return {
            "action_text": self.action_text,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame
        }


class TakeItem:
    def __init__(self, task_id="", task_name="", episode_id="", take_desc="", take_note="", record_id=None, take_name_cn: str = ""):
        # 任务ID（业务任务ID）
        self._task_id = task_id
        # 任务名称（从数据库获取）
        self._task_name = task_name
        # Episode ID（从数据库获取）
        self._episode_id = episode_id
        # Take名称（组合格式：task_name_task_id_episode_id）
        self._take_name = ""
        # Take中文名称（源自 task_name_cn，仅用于显示/存档，不参与设备交互）
        self._take_name_cn = take_name_cn or ""
        # 录制描述
        self._take_desc = take_desc
        # 录制批注
        self._take_notes = take_note
        # 录制ID（仅用于设备交互，不用于显示/导出）
        self._record_id = record_id
        # 录制开始时间
        self._start_time = datetime.now()
        # 录制结束时间
        self._end_time = datetime.now()
        # 录制时长
        self._due = 0
        # 任务状态
        self._task_status = "pending"
        # 动作信息列表
        self._actions = []
        
        # 自动生成take_name
        self._generate_take_name()

    def _generate_take_name(self):
        """生成take_name：task_name_task_id_episode_id"""
        if self._task_name and self._task_id and self._episode_id:
            self._take_name = f"{self._task_name}_{self._task_id}_{self._episode_id}"
        elif self._task_name and self._task_id:
            self._take_name = f"{self._task_name}_{self._task_id}"
        else:
            self._take_name = ""

    def update_task_info(self, task_id=None, task_name=None, episode_id=None):
        """更新任务信息并重新生成take_name"""
        if task_id is not None:
            self._task_id = task_id
        if task_name is not None:
            self._task_name = task_name
        if episode_id is not None:
            self._episode_id = episode_id
        self._generate_take_name()

    def add_action(self, action_info):
        self._actions.append(action_info)

    def __json__(self):
        return {
            "task_id": self._task_id,
            "task_name": self._task_name,
            "episode_id": self._episode_id,
            "take_name": self._take_name,
            "take_name_cn": self._take_name_cn,
            "take_desc": self._take_desc,
            "take_notes": self._take_notes,
            "record_id": self._record_id,
            "start_time": self._start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "end_time": self._end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "due": str(self._due),
            "task_status": self._task_status,
            "actions": [a.to_dict() for a in self._actions]
        }
