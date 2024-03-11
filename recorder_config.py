from typing import Optional

from bilibili_api import Verify

from bili_web_api import BiliBili
from bilibili import Bilibili


class UploaderAccount:
    name: str
    username: str
    password: str
    sessdata: str
    bili_jct: str
    buvid3: str
    buvid4: str
    dedeuserid: str
    login_proxy: str
    access_token: str
    line: str
    verify: Verify

    def __init__(self, config_dict):
        for key, value in config_dict.items():
            self.__setattr__(key, value)
        self.login()

    def login(self):
        b = Bilibili()
        if hasattr(self, "login_proxy"):
            b.set_proxy(add=self.login_proxy)
        self.access_token = b.access_token
        print(self.__dict__)
        if hasattr(self, "sessdata") and hasattr(self, "bili_jct"):
            biliup_uploader = BiliBili(None)
            # we have self.account.sessdata, self.account.bili_jct
            cookie_jar = {
                "SESSDATA": self.sessdata,
                "bili_jct": self.bili_jct
            }
            try:
                biliup_uploader.login_by_cookies(cookie_jar)
                print(f"验证 cookie 成功: {self.name}")
            except Exception as e:
                print(f"验证 cookie 失败: {self.name}")
                print(e)
            pass
        else:
            b.login(username=self.username, password=self.password)
            self.sessdata = b._session.cookies['SESSDATA']
            self.bili_jct = b._session.cookies['bili_jct']
        if not hasattr(self, "line"):
            self.line = "auto"
        print(f"login successfully! {self.name} {self.access_token} {self.sessdata} {self.bili_jct}")
        self.verify = Verify(sessdata=self.sessdata, csrf=self.bili_jct)


class RecoderRoom:
    id: int
    uploader: Optional[str]
    uploader_obj: Optional[UploaderAccount]
    recorder: Optional[str]
    recorder_obj: Optional[UploaderAccount]
    tags: Optional[str]
    channel_id: Optional[int]
    title: Optional[str]
    description: Optional[str]
    source: Optional[str]
    he_user_dict: Optional[str]
    he_regex_rules: Optional[str]

    def __init__(self, config_dict):
        self.uploader = None
        self.recorder = None
        self.recorder_obj = None
        self.uploader_obj = None
        self.he_user_dict = None
        self.he_regex_rules = None
        for key, value in config_dict.items():
            self.__setattr__(key, value)
        if self.recorder is None and self.uploader is not None:
            self.recorder = self.uploader
        assert self.recorder_obj is None, "recorder_obj should not be set manually"
        assert self.uploader_obj is None, "uploader_obj should not be set manually"


class RecorderConfig:
    def __init__(self, config_dict):
        self.accounts = {name: UploaderAccount(account) for name, account in config_dict['accounts'].items()}
        self.rooms = [RecoderRoom(room) for room in config_dict['rooms']]
        for room in self.rooms:
            if room.uploader is not None:
                assert room.uploader in self.accounts, f"uploader {room.uploader} not found"
                room.uploader_obj = self.accounts[room.uploader]
            if room.recorder is not None:
                assert room.recorder in self.accounts, f"recorder {room.recorder} not found"
                room.recorder_obj = self.accounts[room.recorder]
