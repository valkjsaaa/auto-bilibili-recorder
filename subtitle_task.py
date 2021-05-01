import datetime
import json
import traceback
from typing import Any

import bilibili_api
import srt
from bilibili_api import Verify, video

from upload_task import UploadTask

ERROR_THRESHOLD = 10
HOURS_THRESHOLD = 12


class SubtitleTask:
    def __init__(self, subtitle_path: str, bvid: str, cid: int, verify: Verify):
        self.subtitle_path = subtitle_path
        self.cid = cid
        self.bvid = bvid
        self.start_date = datetime.datetime.now(datetime.timezone.utc)
        self.sessdata = verify.sessdata
        self.csrf = verify.csrf
        self.error_count = 0

    def to_dict(self):
        return vars(self)

    @staticmethod
    def from_dict(save_dict: {str: Any}) -> 'SubtitleTask':
        comment_task = SubtitleTask(
            save_dict['subtitle_path'],
            save_dict['bvid'],
            save_dict['cid'],
            Verify(save_dict['sessdata'], save_dict['csrf'])
        )
        for key, value in save_dict.items():
            comment_task.__setattr__(key, value)
        return comment_task

    @staticmethod
    def from_upload_task(upload_task: UploadTask, bvid: str, cid: int) -> 'SubtitleTask':
        comment_task = SubtitleTask(upload_task.subtitle_path, bvid, cid, upload_task.verify)
        return comment_task

    def is_earlier_task_of(self, new_task: 'SubtitleTask'):
        return new_task.bvid == self.bvid and new_task.start_date > self.start_date

    def post_subtitle(self) -> bool:
        if (datetime.datetime.now(datetime.timezone.utc) - self.start_date).total_seconds() / 60 / 60 > HOURS_THRESHOLD:
            return True
        if self.error_count > ERROR_THRESHOLD:
            return True
        try:
            video.get_video_info(self.bvid)
        except bilibili_api.exceptions.BilibiliApiException:  # Video not published yet
            return False
        self.error_count += 1
        verify = Verify(self.sessdata, self.csrf)
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
        srt_json_str = json.dumps(srt_json)
        print(f"posting subtitles on {self.cid} of {self.bvid}")
        try:
            video.save_subtitle(srt_json_str, bvid=self.bvid, cid=self.cid, verify=verify)
        except bilibili_api.exceptions.BilibiliApiException as e:
            # noinspection PyUnresolvedReferences
            if hasattr(e, 'code') and (e.code == 79022 or e.code == -404 or e.code == 502):  # video not approved yet
                self.error_count -= 1
                return False
            else:
                print(traceback.format_exc())
                return False
        return True


if __name__ == '__main__':
    import yaml

    ct_1 = SubtitleTask("subtitle_path", "BV", 12345678, Verify("sessdata", "csrf"))
    ct_yaml = yaml.dump(ct_1.to_dict())
    ct_2 = SubtitleTask.from_dict(yaml.load(ct_yaml))
    print(ct_1)
    print(ct_2)
