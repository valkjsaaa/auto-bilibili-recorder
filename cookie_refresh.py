"""
Bilibili web cookie refresh, following
https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html

The pinned bilibili_api's Credential.refresh() is broken (refresh_cookies() splats dict_items
into the Credential constructor), so the flow is implemented here with plain requests.
"""
import binascii
import re
import time
from typing import Optional
from urllib.parse import unquote

import requests
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA

PUBLIC_KEY = RSA.importKey(
    """\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----"""
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
TIMEOUT = 15


class CookieRefreshError(Exception):
    pass


def sessdata_expiry(sessdata: str) -> Optional[int]:
    """SESSDATA looks like "<hash>,<expiry unix time>,<...>" (URL-encoded)."""
    try:
        return int(unquote(sessdata).split(",")[1])
    except (IndexError, ValueError, AttributeError):
        return None


def cookie_info(cookies: dict) -> Optional[dict]:
    """
    Returns {"refresh": bool, "timestamp": ms} while logged in, None if the cookies are no longer logged in.
    """
    r = requests.get("https://passport.bilibili.com/x/passport-login/web/cookie/info",
                     cookies=cookies, headers=HEADERS, timeout=TIMEOUT).json()
    if r["code"] == -101:
        return None
    if r["code"] != 0:
        raise CookieRefreshError(f"cookie/info failed: {r['code']} {r.get('message')}")
    return r["data"]


def correspond_path(timestamp_ms: int) -> str:
    cipher = PKCS1_OAEP.new(PUBLIC_KEY, SHA256)
    return binascii.b2a_hex(cipher.encrypt(f"refresh_{timestamp_ms}".encode())).decode()


def refresh_cookies(cookies: dict, refresh_token: str, timestamp_ms: Optional[int] = None) -> (dict, str):
    """
    Exchanges cookies + refresh_token (localStorage "ac_time_value") for new cookies.
    Returns ({"SESSDATA", "bili_jct", "DedeUserID"}, new_refresh_token). The old refresh_token is spent.
    """
    if timestamp_ms is None:
        timestamp_ms = round(time.time() * 1000)
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)

    r = session.get(f"https://www.bilibili.com/correspond/1/{correspond_path(timestamp_ms)}", timeout=TIMEOUT)
    match = re.search(r'<div id="1-name">(.+?)</div>', r.text)
    if r.status_code != 200 or match is None:
        raise CookieRefreshError(f"getting refresh_csrf failed: HTTP {r.status_code}")

    r = session.post("https://passport.bilibili.com/x/passport-login/web/cookie/refresh", data={
        "csrf": cookies["bili_jct"],
        "refresh_csrf": match.group(1),
        "source": "main_web",
        "refresh_token": refresh_token,
    }, timeout=TIMEOUT)
    body = r.json()
    if body["code"] != 0:
        raise CookieRefreshError(f"cookie/refresh failed: {body['code']} {body.get('message')}")
    try:
        new_cookies = {key: r.cookies[key] for key in ("SESSDATA", "bili_jct", "DedeUserID")}
    except KeyError as err:
        raise CookieRefreshError(f"cookie/refresh response is missing cookie {err}")
    new_refresh_token = body["data"]["refresh_token"]

    # Invalidates the old session. The new cookies already work, so a failure here only leaves the old one alive.
    confirm = requests.post("https://passport.bilibili.com/x/passport-login/web/confirm/refresh", data={
        "csrf": new_cookies["bili_jct"],
        "refresh_token": refresh_token,
    }, cookies={**cookies, **new_cookies}, headers=HEADERS, timeout=TIMEOUT).json()
    if confirm["code"] != 0:
        print(f"confirm/refresh failed (harmless): {confirm['code']} {confirm.get('message')}")
    return new_cookies, new_refresh_token
