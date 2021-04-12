import os.path
import sys

from bilibili_api.video import video_upload, video_cover_upload, video_submit, get_video_info, video_update


class UploadTask:

    def __init__(self, session_id, video_path, thumbnail_path, sc_path, he_path,
                 title, source, description, tag, channel_id, danmaku, verify):
        self.session_id = session_id
        self.video_path = video_path
        self.sc_path = sc_path
        self.he_path = he_path
        self.thumbnail_path = thumbnail_path
        self.title = title
        self.source = source
        self.description = description
        self.tag = tag
        self.channel_id = channel_id
        self.danmaku = danmaku
        self.verify = verify
        self.trial = 0

    def upload(self, session_dict: {str: str}):
        def on_progress(update):
            print(update)
        filename = video_upload(self.video_path, verify=self.verify, on_progress=on_progress)
        if self.session_id not in session_dict:
            if self.danmaku:
                suffix = "弹幕高能版"
            else:
                suffix = "无弹幕版"
            cover_url = video_cover_upload(self.thumbnail_path, verify=self.verify)
            data = {
                "copyright": 2,
                "source": self.source,
                "cover": cover_url,
                "desc": self.description,
                "desc_format_id": 0,
                "dynamic": "",
                "interactive": 0,
                "no_reprint": 0,
                "subtitles": {
                    "lan": "",
                    "open": 0
                },
                "tag": self.tag,
                "tid": self.channel_id,
                "title": self.title + " " + suffix,
                "videos": [
                    {
                        "desc": "",
                        "filename": filename,
                        "title": os.path.basename(filename)
                    }
                ]
            }

            result = video_submit(data, self.verify)
            print(f"{self.title} uploaded: {result}", file=sys.stderr)
            return result['bvid']
        else:
            old_bv = session_dict[self.session_id]
            v = get_video_info(bvid=old_bv, is_simple=False, is_member=True, verify=self.verify)
            old_title = v["archive"]["title"]
            if self.danmaku and "无弹幕版" in old_title:
                new_title = old_title.replace("无弹幕版", "弹幕高能版")
            else:
                new_title = old_title
            data = {
                "copyright": v["archive"]['copyright'],
                "source": v["archive"]["source"],
                "cover": v["archive"]["cover"],
                "desc": v["archive"]["desc"],
                "desc_format_id": v["archive"]["desc_format_id"],
                "dynamic": v["archive"]["dynamic"],
                "tag": v["archive"]["tag"],
                "tid": v["archive"]["tid"],
                "title": new_title,
                "videos":
                    [{
                        "desc": video['desc'],
                        "filename": filename if idx == 0 else video['filename'],
                        "title": video['title']
                    } for idx, video in enumerate(v["videos"])]
                ,
                "handle_staff": False,
                'bvid': v["archive"]["bvid"]
            }
            result = video_update(data, self.verify)
            print(f"{data['title']} updated: {result}")
            return result['bvid']

