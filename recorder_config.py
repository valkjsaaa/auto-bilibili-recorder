from typing import Optional


class UploaderAccount:
    name: str
    sessdata: str
    bili_jct: str

    def __init__(self, config_dict):
        for key, value in config_dict.items():
            self.__setattr__(key, value)


class RecoderRoom:
    id: int
    uploader: Optional[str]
    tags: Optional[str]
    channel_id: Optional[int]
    title: Optional[str]
    description: Optional[str]
    source: Optional[str]

    def __init__(self, config_dict):
        self.uploader = None
        for key, value in config_dict.items():
            self.__setattr__(key, value)


class RecorderConfig:
    def __init__(self, config_dict):
        self.accounts = {name: UploaderAccount(account) for name, account in config_dict['accounts'].items()}
        self.rooms = [RecoderRoom(room) for room in config_dict['rooms']]
        for room in self.rooms:
            if room.uploader is not None:
                assert room.uploader in self.accounts
