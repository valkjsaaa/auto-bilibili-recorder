import datetime
import traceback
import re
from typing import Any

import bilibili_api
from bilibili_api import Credential, video, comment
from bilibili_api.comment import send_comment

from upload_task import UploadTask

SEG_CHAR = '\n\n\n\n'
ERROR_THRESHOLD = 10
HOURS_THRESHOLD = 12

TEXT_LIMIT = 900


def segment_text(text):
    lines = text.split('\n')
    new_text = ""
    new_segment = ""

    for line in lines:
        if len(new_segment) + len(line) < TEXT_LIMIT:
            new_segment += line + "\n"
        else:
            if len(line) > TEXT_LIMIT:
                print(f"line\"{line}\" too long, omit.")
            else:
                new_text += new_segment + SEG_CHAR
                new_segment = line + "\n"
    new_text += new_segment
    return new_text


def process_text(text, bvid):
    text.replace(SEG_CHAR, "\n")
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        matches = re.findall("^\\s+([0-9]+):([0-9]+)", line)
        if len(matches) > 0:
            mins = matches[0][0]
            secs = matches[0][1]
            link = f"https://www.bilibili.com/video/{bvid}?t={mins}m{secs}s"
            line += "\t" + link
        new_lines += [line]
    new_str = "\n".join(new_lines)
    return segment_text(new_str)


class CommentTask:
    def __init__(self, sc_path, he_path, session_id, verify: Credential):
        self.sc_path = sc_path
        self.he_path = he_path
        self.sc_root_id = ""
        self.he_root_id = ""
        self.sc_progress = 0
        self.he_progress = 0
        self.session_id = session_id
        self.start_date = datetime.datetime.now(datetime.timezone.utc)
        self.verify = verify
        self.error_count = 0

    def to_dict(self):
        return {
            "sc_path": self.sc_path,
            "he_path": self.he_path,
            "sc_root_id": self.sc_root_id,
            "he_root_id": self.he_root_id,
            "sc_progress": self.sc_progress,
            "he_progress": self.he_progress,
            "session_id": self.session_id,
            "start_date": self.start_date,
            "credentials_dict": self.verify.get_cookies(),
            "error_count": self.error_count
        }

    @staticmethod
    def from_dict(save_dict: {str: Any}) -> 'CommentTask':
        comment_task = CommentTask(
            save_dict['sc_path'],
            save_dict['he_path'],
            save_dict['session_id'],
            Credential.from_cookies(save_dict['credentials_dict'])
        )
        for key, value in save_dict.items():
            comment_task.__setattr__(key, value)
        return comment_task

    @staticmethod
    def from_upload_task(upload_task: UploadTask) -> 'CommentTask':
        comment_task = CommentTask(upload_task.sc_path, upload_task.he_path, upload_task.session_id, upload_task.verify)
        return comment_task

    async def post_comment(self, session_dict: {str: str}) -> bool:
        if (datetime.datetime.now(datetime.timezone.utc) - self.start_date).total_seconds() / 60 / 60 > HOURS_THRESHOLD:
            print(f"Comment task {self.session_id} expired")
            return True
        if self.session_id not in session_dict:
            print(f"session {self.session_id} not found")
            return False
        if self.error_count > ERROR_THRESHOLD:
            print(f"Comment task {self.session_id} failed too many times")
            return True
        bvid = session_dict[self.session_id]
        target_video = video.Video(bvid=bvid, credential=self.verify)
        try:
            await target_video.get_info()
        except (bilibili_api.ApiException, bilibili_api.ResponseCodeException):  # The video is not published yet
            return False
        print(f"posting comments on {bvid}")
        self.error_count += 1
        # load sc and se text
        with open(self.sc_path, 'r') as file:
            # sc_str = process_text(file.read(), bvid)
            sc_str = file.read()
        with open(self.he_path, 'r') as file:
            # he_str = process_text(file.read(), bvid)
            he_str = file.read()
        sc_list = sc_str.split(SEG_CHAR)
        he_list = he_str.split(SEG_CHAR)
        try:
            if self.he_root_id == "":
                resp = await send_comment(
                    he_list[0],
                    oid=target_video.get_aid(),
                    type_=comment.CommentResourceType.VIDEO,
                    credential=self.verify
                )
                self.he_root_id = resp['rpid']
                self.he_progress = 1
            for i, content in enumerate(he_list):
                if i >= self.he_progress:
                    await send_comment(
                        content,
                        oid=target_video.get_aid(),
                        type_=comment.CommentResourceType.VIDEO,
                        root=self.he_root_id,
                        credential=self.verify
                    )
                    self.he_progress = i + 1
            if self.sc_root_id == "":
                resp = await send_comment(
                    sc_list[0],
                    oid=target_video.get_aid(),
                    type_=comment.CommentResourceType.VIDEO,
                    credential=self.verify
                )
                self.sc_root_id = resp['rpid']
                self.sc_progress = 1
            for i, content in enumerate(sc_list):
                if i >= self.sc_progress:
                    await send_comment(
                        content,
                        oid=target_video.get_aid(),
                        type_=comment.CommentResourceType.VIDEO,
                        root=self.sc_root_id,
                        credential=self.verify
                    )
                    self.sc_progress = i + 1
        except (bilibili_api.ApiException, bilibili_api.ResponseCodeException):
            print("Comment posting failed")
            print(print(traceback.format_exc()))
            return False
        return True


if __name__ == '__main__':
    import yaml

    ct_1 = CommentTask("sc_path", "he_path", "session_id", Credential.from_cookies({
            "buvid3": "buvid3",
            "buvid4": "buvid4",
            "DedeUserID": "DedeUserID",
            "SESSDATA": "SESSDATA",
            "bili_jct": "bili_jct"
    }))
    ct_yaml = yaml.dump(ct_1.to_dict())
    ct_2 = CommentTask.from_dict(yaml.load(ct_yaml, Loader=yaml.FullLoader))
    print(ct_1)
    print(ct_2)
