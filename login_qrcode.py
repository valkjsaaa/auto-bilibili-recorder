"""
Logs an uploader account in by QR code and prints (or writes) the cookies for recorder_config.yaml,
including ac_time_value, which the recorder needs to keep the cookies refreshed by itself.

    docker exec -it <container> /webhook/venv/bin/python /webhook/login_qrcode.py --write xk_bot

Scan the QR code with the Bilibili app logged in as that account, then restart the container.
"""
import argparse
import re
import sys
import time

import qrcode
import requests

from cookie_refresh import HEADERS, TIMEOUT

CONFIG_KEYS = ["sessdata", "bili_jct", "buvid3", "buvid4", "dedeuserid", "ac_time_value"]


def login() -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    data = session.get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
                       timeout=TIMEOUT).json()["data"]
    qr = qrcode.QRCode(border=1)
    qr.add_data(data["url"])
    qr.print_ascii(invert=True)
    qr.make_image().save("qrcode.png")
    print(f"Scan with the Bilibili app (also saved to qrcode.png): {data['url']}")
    while True:
        time.sleep(2)
        r = session.get("https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
                        params={"qrcode_key": data["qrcode_key"]}, timeout=TIMEOUT)
        poll = r.json()["data"]
        if poll["code"] == 0:
            break
        if poll["code"] == 86038:
            sys.exit("QR code expired, run again.")
        if poll["code"] not in (86101, 86090):  # not scanned / scanned but not confirmed
            sys.exit(f"Login failed: {poll}")
    spi = session.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=TIMEOUT).json()["data"]
    return {
        "sessdata": r.cookies["SESSDATA"],
        "bili_jct": r.cookies["bili_jct"],
        "dedeuserid": r.cookies["DedeUserID"],
        "buvid3": spi["b_3"],
        "buvid4": spi["b_4"],
        "ac_time_value": poll["refresh_token"],
    }


def write_account(config_path, account_key, values: dict):
    """Line-based so that the comments in recorder_config.yaml survive."""
    with open(config_path, 'r') as file:
        lines = file.read().split("\n")
    start = next((i for i, line in enumerate(lines) if line.rstrip() == f"  {account_key}:"), None)
    if start is None:
        sys.exit(f"account {account_key} not found in {config_path}")
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith("    ")), len(lines))
    missing = dict(values)
    for i in range(start + 1, end):
        match = re.match(r"^    (\w+):", lines[i])
        if match and match.group(1) in missing:
            lines[i] = f'    {match.group(1)}: "{missing.pop(match.group(1))}"'
    lines[end:end] = [f'    {key}: "{value}"' for key, value in missing.items()]
    with open(config_path, 'w') as file:
        file.write("\n".join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", metavar="ACCOUNT", help="update this account in the config instead of printing")
    parser.add_argument("--config", default="recorder_config.yaml")
    args = parser.parse_args()
    cookies = login()
    print(f"logged in as uid {cookies['dedeuserid']}")
    if args.write:
        write_account(args.config, args.write, cookies)
        print(f"updated {args.write} in {args.config}, restart the container to use it")
    else:
        for key in CONFIG_KEYS:
            print(f'    {key}: "{cookies[key]}"')
