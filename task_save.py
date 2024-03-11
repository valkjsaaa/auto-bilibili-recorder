from comment_task import CommentTask
from subtitle_task import SubtitleTask


class TaskSave:

    def __init__(self):
        self.session_id_map: {str: str} = {}
        self.active_comment_tasks: [CommentTask] = []
        self.active_subtitle_tasks: [SubtitleTask] = []
        self.video_name_history = {}

    def to_dict(self):
        return {
            "session_id_map": self.session_id_map,
            "active_comment_tasks": [task.to_dict() for task in self.active_comment_tasks],
            "active_subtitle_tasks": [task.to_dict() for task in self.active_subtitle_tasks],
            "video_name_history": self.video_name_history
        }

    @staticmethod
    def from_dict(save_dict) -> 'TaskSave':
        task_save = TaskSave()
        task_save.session_id_map = save_dict["session_id_map"]
        assert type(task_save.session_id_map) is dict
        task_save.active_comment_tasks = [CommentTask.from_dict(task) for task in save_dict["active_comment_tasks"]]
        if "active_subtitle_tasks" not in save_dict:
            task_save.active_subtitle_tasks = []
        else:
            task_save.active_subtitle_tasks = \
                [SubtitleTask.from_dict(task) for task in save_dict["active_subtitle_tasks"]]
        task_save.video_name_history = save_dict["video_name_history"]
        assert type(task_save.video_name_history) is dict
        return task_save


if __name__ == '__main__':
    import yaml
    from bilibili_api import Credential
    ts = TaskSave()
    ct = CommentTask("sc_path", "he_path", "session_id", Credential.from_cookies({
        "buvid3": "buvid3",
        "buvid4": "buvid4",
        "DedeUserID": "dedeuserid",
        "SESSDATA": "sessdata",
        "bili_jct": "bili_jct"
    }))
    ts.active_comment_tasks += [ct]
    ts.session_id_map["session_id"] = "bvid"
    ts_yaml = yaml.dump(ts.to_dict())
    ts_1 = TaskSave.from_dict(yaml.load(ts_yaml, Loader=yaml.FullLoader))
    print(ts)
    print(ts_1)
