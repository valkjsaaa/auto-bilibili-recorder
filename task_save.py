from comment_task import CommentTask


class TaskSave:

    def __init__(self):
        self.session_id_map: {str: str} = {}
        self.active_comment_tasks: [CommentTask] = []
        self.video_name_history = []

    def to_dict(self):
        return {
            "session_id_map": self.session_id_map,
            "active_comment_tasks": [task.to_dict() for task in self.active_comment_tasks],
            "video_name_history": self.video_name_history
        }

    @staticmethod
    def from_dict(save_dict) -> 'TaskSave':
        task_save = TaskSave()
        task_save.session_id_map = save_dict["session_id_map"]
        assert type(task_save.session_id_map) is dict
        task_save.active_comment_tasks = [CommentTask.from_dict(task) for task in save_dict["active_comment_tasks"]]
        task_save.video_name_history = save_dict["video_name_history"]
        assert type(task_save.video_name_history) is list
        return task_save


if __name__ == '__main__':
    import yaml
    from bilibili_api import Verify
    ts = TaskSave()
    ct = CommentTask("sc_path", "he_path", "session_id", Verify("sessdata", "csrf"))
    ts.active_comment_tasks += [ct]
    ts.session_id_map["session_id"] = "bvid"
    ts_yaml = yaml.dump(ts.to_dict())
    ts_1 = TaskSave.from_dict(yaml.load(ts_yaml))
    print(ts)
    print(ts_1)
