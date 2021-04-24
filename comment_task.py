import datetime
import traceback
from typing import Any

import bilibili_api
from bilibili_api import Verify, video
from bilibili_api.video import send_comment

from upload_task import UploadTask

SEG_CHAR = '\n\n\n\n'
ERROR_THRESHOLD = 10
HOURS_THRESHOLD = 12


class CommentTask:
    def __init__(self, sc_path, he_path, session_id, verify: Verify):
        self.sc_path = sc_path
        self.he_path = he_path
        self.sc_root_id = ""
        self.he_root_id = ""
        self.sc_progress = 0
        self.he_progress = 0
        self.session_id = session_id
        self.start_date = datetime.datetime.now(datetime.timezone.utc)
        self.sessdata = verify.sessdata
        self.csrf = verify.csrf
        self.error_count = 0

    def to_dict(self):
        return vars(self)

    @staticmethod
    def from_dict(save_dict: {str: Any}) -> 'CommentTask':
        comment_task = CommentTask(
            save_dict['sc_path'],
            save_dict['he_path'],
            save_dict['session_id'],
            Verify(save_dict['sessdata'], save_dict['csrf'])
        )
        for key, value in save_dict.items():
            comment_task.__setattr__(key, value)
        return comment_task

    @staticmethod
    def from_upload_task(upload_task: UploadTask) -> 'CommentTask':
        comment_task = CommentTask(upload_task.sc_path, upload_task.he_path, upload_task.session_id, upload_task.verify)
        return comment_task

    def post_comment(self, session_dict: {str: str}) -> bool:
        if (datetime.datetime.now(datetime.timezone.utc) - self.start_date).total_seconds() / 60 / 60 > HOURS_THRESHOLD:
            return True
        if self.session_id not in session_dict:
            return False
        if self.error_count > ERROR_THRESHOLD:
            return True
        bvid = session_dict[self.session_id]
        try:
            video.get_video_info(bvid)
        except bilibili_api.exceptions.BilibiliApiException:  # Video not published yet
            return False
        print(f"posting comments on {bvid}")
        self.error_count += 1
        verify = Verify(self.sessdata, self.csrf)
        # load sc and se text
        with open(self.sc_path, 'r') as file:
            sc_str = file.read()
        with open(self.he_path, 'r') as file:
            he_str = file.read()
        sc_list = sc_str.split(SEG_CHAR)
        he_list = he_str.split(SEG_CHAR)
        try:
            if self.he_root_id == "":
                resp = send_comment(he_list[0], bvid=bvid, verify=verify)
                self.he_root_id = resp['rpid']
                self.he_progress = 1
            for i, content in enumerate(he_list):
                if i >= self.he_progress:
                    send_comment(content, bvid=bvid, root=self.he_root_id, verify=verify)
                    self.he_progress = i + 1
            if self.sc_root_id == "":
                resp = send_comment(sc_list[0], bvid=bvid, verify=verify)
                self.sc_root_id = resp['rpid']
                self.sc_progress = 1
            for i, content in enumerate(sc_list):
                if i >= self.sc_progress:
                    send_comment(content, bvid=bvid, root=self.sc_root_id, verify=verify)
                    self.sc_progress = i + 1
        except bilibili_api.exceptions.BilibiliApiException:
            print("Comment posting failed")
            print(print(traceback.format_exc()))
            return False
        return True


if __name__ == '__main__':
    import yaml
    ct_1 = CommentTask("sc_path", "he_path", "session_id", Verify("sessdata", "csrf"))
    ct_yaml = yaml.dump(ct_1.to_dict())
    ct_2 = CommentTask.from_dict(yaml.load(ct_yaml))
    print(ct_1)
    print(ct_2)
