from bilibili_api.video_uploader import (
    VideoUploader, VideoUploaderPage, VideoEditor, VideoMeta, Lines, _choose_line)
from recorder_config import UploaderAccount

SPECIAL_SPACE = "\u2007"


class UploadTask:

    def __init__(self, session_id, video_path, thumbnail_path, sc_path, he_path, subtitle_path,
                 title, source, description, tag, channel_id, danmaku, account: UploaderAccount):
        self.session_id = session_id
        self.video_path = video_path
        self.sc_path = sc_path
        self.he_path = he_path
        self.subtitle_path = subtitle_path
        self.thumbnail_path = thumbnail_path
        self.title = title
        self.source = source
        self.description = description
        self.tag = tag
        self.channel_id = channel_id
        self.danmaku = danmaku
        self.account = account
        self.verify = self.account.verify
        self.trial = 0

    async def upload(self, session_dict: {str: str}):

        if self.danmaku:
            suffix = "弹幕高能版"
        else:
            suffix = "无弹幕版"
        if self.account.line == "auto":
            line = None
        elif self.account.line == "bda2":
            line = Lines.BDA2
        elif self.account.line == "qn":
            line = Lines.QN
        elif self.account.line == "ws":
            line = Lines.WS
        elif self.account.line == "bldsa":
            line = Lines.BLDSA
        else:
            print(f"Unknown line: {self.account.line}, use auto instead.")
            line = None
        meta = VideoMeta(
            tid=self.channel_id,
            title=self.title + SPECIAL_SPACE + suffix,
            desc=self.description,
            tags=self.tag,
            original=False,
            source=self.source,
            cover=self.thumbnail_path,
            no_reprint=False,
            subtitle={
                "lan": "",
                "open": 0
            }
        )

        async def on_progress(data):
            print(data)

        uploader = VideoUploader(
            pages=[
                VideoUploaderPage(
                    path=self.video_path,
                    title=suffix
                )
            ],
            meta=meta,
            credential=self.verify,
            line=line
        )
        uploader.add_event_listener("__ALL__", on_progress)
        if self.session_id not in session_dict:

            result = await uploader.start()
            print(f"{meta.title} uploaded: {result}")
            return result['bvid']
        else:
            videos = []
            uploader.line = await _choose_line(uploader.line)
            for page in uploader.pages:
                data = await uploader._upload_page(page)
                videos.append(
                    {
                        "title": page.title,
                        "filename": data['filename'],
                        "desc": "",
                        "cid": data['cid']
                    }
                )
                print(f"{page.title} uploaded: {data['filename']}")
            meta_dict = {
                "copyright": 2,
                "desc_format_id": 0,
                "dynamic": "",
                "interactive": 0,
                "new_web_edit": 1, "act_reserve_create": 0,
                         "handle_staff": False, "topic_grey": 1, "no_reprint": 0, "subtitles": {
                            "lan": "",
                            "open": 0
                         }, "web_os": 2, 'videos': videos}
            updater = VideoEditor(
                bvid=session_dict[self.session_id],
                meta=meta_dict,
                credential=self.verify
            )
            updater.add_event_listener("__ALL__", on_progress)
            await updater._fetch_configs()
            updater.meta["desc"] = updater._VideoEditor__old_configs["archive"]["desc"]
            updater.meta["tag"] = updater._VideoEditor__old_configs["archive"]["tag"]
            updater.meta["copyright"] = updater._VideoEditor__old_configs["archive"]["copyright"]
            updater.meta["source"] = updater._VideoEditor__old_configs["archive"]["source"]
            updater.meta["cover"] = updater._VideoEditor__old_configs["archive"]["cover"]
            updater.meta["tid"] = updater._VideoEditor__old_configs["archive"]["tid"]
            old_title = updater._VideoEditor__old_configs["archive"]["title"]
            if SPECIAL_SPACE in old_title:
                stripped_title = old_title.rpartition(SPECIAL_SPACE)[0]
            else:
                stripped_title = old_title
            new_title = stripped_title + SPECIAL_SPACE + suffix
            updater.meta["title"] = new_title
            result = await updater._submit()
            print(f"{new_title} updated: {result}")
            return updater.bvid
