
class DictShotName:

    def __init__(self) -> None:
        self._dict_shotname = {}

    # 按shotname进行分组，得到最大Take#与Shot总数
    def add_shot_with_take(self, shot_name, take_no):
        shot_count = 1
        if shot_name in self._dict_shotname:
            (max_take_no, shot_cnt) = self._dict_shotname[shot_name]
            shot_count = shot_cnt + 1
            if take_no > max_take_no:
                self._dict_shotname[shot_name] = (take_no, shot_count)
        else:
            self._dict_shotname[shot_name] = (take_no, shot_count)


    def shot_list_group_by(self, take_list):
        self._dict_shotname.clear()
        max_take_no = 0
        for take_item in take_list:
            # 按shotname进行分组，得到最大Take#与Shot总数
            if take_item._shot_name in self._dict_shotname:
                (max_take_no, shot_count) = self._dict_shotname[take_item._shot_name]
                shot_count = shot_count + 1
                
                if take_item._take_no > max_take_no:
                    self._dict_shotname[take_item._shot_name] = (take_item._take_no, shot_count)
            else:
                self._dict_shotname[take_item._shot_name] = (take_item._take_no, 1)

    def take_info(self, shot_name):
        if shot_name in self._dict_shotname:
            return self._dict_shotname[shot_name]
        else:
            return None

    def clear(self):
        self._dict_shotname.clear()

