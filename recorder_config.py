import datetime
import threading
import time
import traceback
from collections import OrderedDict
from typing import Optional

from bilibili_api import Credential

from cookie_refresh import cookie_info, refresh_cookies, sessdata_expiry
from credential_store import CredentialStore

# Refresh early even if Bilibili doesn't ask yet: an expired SESSDATA can no longer be refreshed.
REFRESH_DAYS_BEFORE_EXPIRY = 30


class UploaderAccount:
    key: str
    name: str
    sessdata: str
    bili_jct: str
    buvid3: str
    buvid4: str
    dedeuserid: str
    ac_time_value: Optional[str]
    login_proxy: str
    access_token: str
    line: str
    verify: Credential
    valid: bool

    def __init__(self, config_dict, key=None, store: Optional[CredentialStore] = None):
        self.ac_time_value = None
        for key_, value in config_dict.items():
            self.__setattr__(key_, value)
        self.key = key if key is not None else getattr(self, "name", "")
        self.store = store
        self.lock = threading.Lock()
        self.config_sessdata = getattr(self, "sessdata", None)
        if store is not None:
            stored = store.get(self.key, self.config_sessdata)
            if stored is not None:
                print(f"using refreshed cookies for {self.key} from {stored.get('updated_at')}")
                self.sessdata = stored["sessdata"]
                self.bili_jct = stored["bili_jct"]
                self.ac_time_value = stored["ac_time_value"]
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
        assert (
                hasattr(self, "sessdata") and
                hasattr(self, "bili_jct") and
                hasattr(self, "buvid3") and
                hasattr(self, "buvid4") and
                hasattr(self, "dedeuserid")
        ), f"missing cookies! {self.name}, \"sessdata\", \"bili_jct\", \"buvid3\", \"buvid4\", \"dedeuserid\""
        self.verify = Credential.from_cookies(self.get_cookie_dict())
        self.verify.ac_time_value = self.ac_time_value
        self.valid = False
        if not hasattr(self, "line"):
            self.line = "auto"
        self.refresh_if_needed()
        if self.valid:
            print(f"login successfully! {self.key} ({self.name})")
        else:
            # Don't take the whole recorder down: other accounts and rooms keep working.
            print(f"!!! login failed for {self.key} ({self.name}): cookies are invalid or expired. "
                  f"Uploads and danmaku for this account will fail until recorder_config.yaml is updated.")

    def expiry_days_left(self) -> Optional[float]:
        expiry = sessdata_expiry(self.sessdata)
        return None if expiry is None else (expiry - time.time()) / 86400

    def refresh_if_needed(self, force=False) -> bool:
        """Checks the cookies and refreshes them when needed. Returns True if the cookies changed."""
        with self.lock:
            try:
                info = cookie_info(self.get_cookie_dict())
            except Exception as err:
                print(f"cookie check failed for {self.key}, will retry later: {err}")
                return False
            self.valid = info is not None
            days_left = self.expiry_days_left()
            expiring = days_left is not None and days_left < REFRESH_DAYS_BEFORE_EXPIRY
            if info is not None and not info["refresh"] and not expiring and not force:
                return False
            reason = "logged out" if info is None else \
                "requested by bilibili" if info["refresh"] else \
                f"expires in {days_left:.1f} days" if expiring else "forced"
            if not self.ac_time_value:
                print(f"!!! cookies for {self.key} need refreshing ({reason}) but no ac_time_value is configured. "
                      f"Add the account's localStorage ac_time_value to recorder_config.yaml.")
                return False
            print(f"refreshing cookies for {self.key} ({reason})")
            try:
                new_cookies, new_refresh_token = refresh_cookies(
                    self.get_cookie_dict(), self.ac_time_value, info["timestamp"] if info else None)
            except Exception as err:
                print(f"!!! cookie refresh failed for {self.key}: {err}")
                print(traceback.format_exc())
                return False
            self.sessdata = new_cookies["SESSDATA"]
            self.bili_jct = new_cookies["bili_jct"]
            self.ac_time_value = new_refresh_token
            # Tasks hold a reference to this Credential, so update it in place.
            self.verify.sessdata = self.sessdata
            self.verify.bili_jct = self.bili_jct
            self.verify.ac_time_value = self.ac_time_value
            self.valid = True
            if self.store is not None:
                self.store.put(self.key, {
                    "base_sessdata": self.config_sessdata,
                    "sessdata": self.sessdata,
                    "bili_jct": self.bili_jct,
                    "ac_time_value": self.ac_time_value,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                })
            print(f"cookies refreshed for {self.key}, new SESSDATA expires in {self.expiry_days_left():.0f} days")
            return True


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
    def __init__(self, config_dict, store: Optional[CredentialStore] = None):
        self.accounts = {
            name: UploaderAccount(account, key=name, store=store) for name, account in config_dict['accounts'].items()
        }
        self.rooms = [RecoderRoom(room) for room in config_dict['rooms']]
        for room in self.rooms:
            if room.uploader is not None:
                assert room.uploader in self.accounts, f"uploader {room.uploader} not found"
                room.uploader_obj = self.accounts[room.uploader]
            if room.recorder is not None:
                assert room.recorder in self.accounts, f"recorder {room.recorder} not found"
                room.recorder_obj = self.accounts[room.recorder]
