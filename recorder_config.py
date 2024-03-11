from collections import OrderedDict
from typing import Optional

from bilibili_api import Credential, sync


class UploaderAccount:
    name: str
    sessdata: str
    bili_jct: str
    buvid3: str
    buvid4: str
    dedeuserid: str
    login_proxy: str
    access_token: str
    line: str
    verify: Credential

    def __init__(self, config_dict):
        for key, value in config_dict.items():
            self.__setattr__(key, value)
        self.login()

    def get_cookie_dict(self):
        return OrderedDict({
            "buvid3": self.buvid3,
            "buvid4": self.buvid4,
            "DedeUserID": self.dedeuserid,
            "SESSDATA": self.sessdata,
            "bili_jct": self.bili_jct,
        })

    def login(self):
        print(self.__dict__)
        assert (
                hasattr(self, "sessdata") and
                hasattr(self, "bili_jct") and
                hasattr(self, "buvid3") and
                hasattr(self, "buvid4") and
                hasattr(self, "dedeuserid")
        ), f"missing cookies! {self.name}, \"sessdata\", \"bili_jct\", \"buvid3\", \"buvid4\", \"dedeuserid\""
        self.verify = Credential.from_cookies(self.get_cookie_dict())
        assert sync(self.verify.check_valid()), f"login failed! {self.name}"
        print(f"login successfully! {self.name} {self.sessdata} {self.bili_jct}")
        if not hasattr(self, "line"):
            self.line = "auto"


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
