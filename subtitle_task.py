import datetime
import traceback
from typing import Any

import bilibili_api
import srt
from bilibili_api import Credential, video

from upload_task import UploadTask

ERROR_THRESHOLD = 10
HOURS_THRESHOLD = 12


class SubtitleTask:
    def __init__(self, subtitle_path: str, bvid: str, verify: Credential):
        self.subtitle_path = subtitle_path
        self.bvid = bvid
        self.start_date = datetime.datetime.now(datetime.timezone.utc)
        self.verify = verify
        self.error_count = 0

    def to_dict(self):
        return {
            "subtitle_path": self.subtitle_path,
            "bvid": self.bvid,
            "credential_dict": self.verify.get_cookies(),
            "start_date": self.start_date,
            "error_count": self.error_count
        }

    @staticmethod
    def from_dict(save_dict: {str: Any}) -> 'SubtitleTask':
        comment_task = SubtitleTask(
            save_dict['subtitle_path'],
            save_dict['bvid'],
            Credential.from_cookies(save_dict['credential_dict'])
        )
        for key, value in save_dict.items():
            if key != "credential_dict":
                comment_task.__setattr__(key, value)
        return comment_task

    @staticmethod
    def from_upload_task(upload_task: UploadTask, bvid: str) -> 'SubtitleTask':
        comment_task = SubtitleTask(upload_task.subtitle_path, bvid, upload_task.verify)
        return comment_task

    def is_earlier_task_of(self, new_task: 'SubtitleTask'):
        return new_task.bvid == self.bvid and new_task.start_date > self.start_date

    async def post_subtitle(self) -> bool:
        if (datetime.datetime.now(datetime.timezone.utc) - self.start_date).total_seconds() / 60 / 60 > HOURS_THRESHOLD:
            return True
        target_video = video.Video(bvid=self.bvid, credential=self.verify)
        if self.error_count > ERROR_THRESHOLD:
            return True
        try:
            await target_video.get_info()
        except (bilibili_api.ApiException, bilibili_api.ResponseCodeException):  # Video not published yet
            return False
        self.error_count += 1
        with open(self.subtitle_path) as srt_file:
            srt_obj = srt.parse(srt_file.read())
        srt_json = {
            "font_size": 0.4,
            "font_color": "#FFFFFF",
            "background_alpha": 0.5,
            "background_color": "#9C27B0",
            "Stroke": "none",
            "body": []
        }

        for srt_single_obj in srt_obj:
            srt_single_obj: srt.Subtitle
            srt_single_obj_body = {
                "from": srt_single_obj.start.total_seconds(),
                "to": srt_single_obj.end.total_seconds(),
                "location": 2,
                "content": srt_single_obj.content
            }
            srt_json["body"] += [srt_single_obj_body]
        print(f"posting subtitles on {self.bvid}")
        try:
            await target_video.submit_subtitle(
                lan="zh-CN",
                data=srt_json,
                submit=True,
                sign=True,
                page_index=0
            )
        except bilibili_api.ResponseCodeException as e:
            # noinspection PyUnresolvedReferences
            if hasattr(e, 'code') and (e.code == 79022 or e.code == -404 or e.code == 502):  # video not approved yet
                self.error_count -= 1
                return False
            else:
                print(traceback.format_exc())
                return False
        except Exception as e:
            self.error_count -= 1
            print(traceback.format_exc())
            return False
        return True


if __name__ == '__main__':
    import yaml

    ct_1 = SubtitleTask("subtitle_path", "BV", Credential.from_cookies({
            "buvid3": "buvid3",
            "buvid4": "buvid4",
            "DedeUserID": "DedeUserID",
            "SESSDATA": "SESSDATA",
            "bili_jct": "bili_jct"
    }))
    ct_yaml = yaml.dump(ct_1.to_dict())
    ct_2 = SubtitleTask.from_dict(yaml.load(ct_yaml, Loader=yaml.FullLoader))
    print(ct_1)
    print(ct_2)
