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
    def __init__(self, shot_name="", take_no=0, take_name="", take_desc="", take_note=""):
        # Shot名称
        self._shot_name = shot_name
        # Take No.
        self._take_no = take_no
        # Take名
        self._take_name = take_name
        # 录制描述
        self._take_desc = take_desc
        # 录制批注
        self._take_notes = take_note
        # 录制开始时间
        self._start_time = datetime.now()
        # 录制结束时间
        self._end_time = datetime.now()
        # 录制时长
        self._due = 0
        # 评分
        self._eval= "--"
        self._actions = []

    def add_action(self, action_info):
        self._actions.append(action_info)

    def __json__(self):
        return {
            "shot_name": self._shot_name,
            "take_no": self._take_no,
            "take_name": self._take_name,
            "take_desc": self._take_desc,
            "take_notes": self._take_notes,
            "start_time": self._start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "end_time": self._end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "due": str(self._due),
            "eval": self._eval,
            "actions":[a.to_dict() for a in self._actions]
        }
