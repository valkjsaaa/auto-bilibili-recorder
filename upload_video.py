import asyncio
import os
import sys
import time
import traceback
from queue import Queue
from threading import Lock
from typing import Optional

import bilibili_api
import dateutil.parser
import yaml
from bilibili_api import Verify
from bilibili_api.video import video_upload, video_submit, video_cover_upload, get_video_info, send_comment, video_update

with open('/storage/bilibili-config.yaml', 'r') as file:
    bilibili_config = yaml.load(file, Loader=yaml.FullLoader)


upload_task_yaml_path = '/storage/upload-task.yaml'
upload_task_dict: {str: str} = {}


def load_upload_task_dict(yaml_path=None):
    global upload_task_dict, upload_task_yaml_path
    if yaml_path is not None:
        upload_task_yaml_path = yaml_path
    if os.path.isfile(upload_task_yaml_path):
        try:
            with open(upload_task_yaml_path, 'r') as file:
                upload_task_dict = yaml.load(file, Loader=yaml.FullLoader)
        except:
            print("upload task list parse error", file=sys.stderr)
            return


def update_upload_task_dict():
    with open(upload_task_yaml_path, 'w') as file:
        yaml.dump(upload_task_dict, file, Dumper=yaml.Dumper)


def upload_video(image_path, video_path, date_string, uploader_name, title, config, update_mode, task_id):
    verify = Verify(sessdata=config["sessdata"], csrf=config["bili_jct"])
    video_date = dateutil.parser.isoparse(date_string)
    video_name = f"【{uploader_name}】{video_date.strftime('%Y年%m月%d日')} {title} 无弹幕先行版"
    cover_url = video_cover_upload(image_path, verify=verify)

    def on_progress(update):
        print(update, file=sys.stderr)

    filename = video_upload(video_path, verify=verify, on_progress=on_progress)

    if not update_mode:
        data = {
            "copyright": 2,
            "source": config["source"],
            "cover": cover_url,
            "desc": config["description"],
            "desc_format_id": 0,
            "dynamic": "",
            "interactive": 0,
            "no_reprint": 0,
            "subtitles": {
                "lan": "",
                "open": 0
            },
            "tag": config["tags"],
            "tid": config["channel_id"],
            "title": video_name,
            "videos": [
                {
                    "desc": "",
                    "filename": filename,
                    "title": video_name
                }
            ]
        }

        result = video_submit(data, verify)
        print(f"{video_name} uploaded: {result}", file=sys.stderr)
        upload_task_dict[task_id] = result['bvid']
        update_upload_task_dict()
        return result
    else:
        v = get_video_info(bvid=upload_task_dict[task_id], is_simple=False, is_member=True, verify=verify)
        print(f"updating... original_video: {v}", file=sys.stderr)
        data = {
            "copyright": v["archive"]['copyright'],
            "source": v["archive"]["source"],
            "cover": v["archive"]["cover"],
            "desc": v["archive"]["desc"],
            "desc_format_id": v["archive"]["desc_format_id"],
            "dynamic": v["archive"]["dynamic"],
            # "interactive": v["archive"]["interactive"],
            # "no_reprint": v["archive"]["no_reprint"],
            # "subtitle": v["subtitle"],
            "tag": v["archive"]["tag"],
            "tid": v["archive"]["tid"],
            "title": v["archive"]["title"].replace("无弹幕先行版", "弹幕高能版"),
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

        result = video_update(data, verify)
        print(f"{data['title']} updated: {result}", file=sys.stderr)
        return result



comment_task_yaml_path = '/storage/comment-task.yaml'
comment_task_list: [(str, [str], [str], {str: str})] = []
comment_task_list_lock = Lock()


def load_comment_task_list(yaml_path=None):
    global comment_task_list, comment_task_yaml_path
    if yaml_path is not None:
        comment_task_yaml_path = yaml_path
    if os.path.isfile(comment_task_yaml_path):
        try:
            with open(comment_task_yaml_path, 'r') as file:
                comment_task_list = yaml.load(file, Loader=yaml.FullLoader)
        except:
            print("comment task list parse error", file=sys.stderr)
            return


def update_comment_task_list():
    with open(comment_task_yaml_path, 'w') as file:
        yaml.dump(comment_task_list, file, Dumper=yaml.Dumper)


def post_comment_async(bv_number: str, sc_comments: [str], he_comments: [str], config: {str: str}):
    global comment_task_list
    comment_task_list_lock.acquire(blocking=True)
    comment_task_list += [(bv_number, sc_comments, he_comments, config)]
    comment_task_list_lock.release()
    update_comment_task_list()


def post_comments_on_vid(bv_number: str, comments: [str], verify: Verify):
    if len(comments) > 0:
        resp = send_comment(comments[0], bvid=bv_number, verify=verify)
        for i in range(1, len(comments)):
            send_comment(comments[i], bvid=bv_number, root=resp['rpid'], verify=verify)


def post_comment(bv_number: str, sc_comments: [str], he_comments: [str], config: {str: str}) -> bool:
    try:
        verify = Verify(sessdata=config["sessdata"], csrf=config["bili_jct"])
        _ = get_video_info(bvid=bv_number, verify=verify)
        try:
            post_comments_on_vid(bv_number, sc_comments, verify)
            post_comments_on_vid(bv_number, he_comments, verify)
        except bilibili_api.exceptions.BilibiliApiException:
            print("comment posting error", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
        finally:
            return True
    except bilibili_api.exceptions.BilibiliApiException:
        return False


video_posting_queue = Queue()


def find_config(room_id) -> Optional[dict]:
    for config in bilibili_config:
        if room_id in config['upload_room_list']:
            return config
    return None


SEG_CHAR = '\n\n\n\n'


def video_poster():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        request_json = video_posting_queue.get()
        if 'trial' not in request_json:
            request_json['trial'] = 0
        trial = request_json['trial']
        try:
            update_mode = request_json['is_update']
            room_id = request_json['RoomId']
            room_name = request_json['Name']
            room_title = request_json['Title']
            config = find_config(room_id)
            if config is None:
                print(f"{room_id} is not in the list of rooms that need to be uploaded, skip.", file=sys.stderr)
                continue
            flv_file_path = request_json['RelativePath']
            record_time = request_json['StartRecordTime']
            base_file_path = flv_file_path.rpartition('.')[0]
            video_file_path = base_file_path + ".flv"
            update_video_file_path = base_file_path + ".bar.mp4"
            png_file_path = base_file_path + ".png"
            resp = upload_video(
                image_path=png_file_path,
                video_path=update_video_file_path if update_mode else video_file_path,
                date_string=record_time,
                uploader_name=room_name,
                title=room_title,
                config=config,
                update_mode=update_mode,
                task_id=request_json['EventRandomId']
            )
            if not update_mode:
                bvid = resp['bvid']
                he_file_path = base_file_path + ".he.txt"
                sc_file_path = base_file_path + ".sc.txt"
                with open(he_file_path, 'r') as file:
                    he_str = file.read()
                with open(sc_file_path, 'r') as file:
                    sc_str = file.read()
                he_list = he_str.split(SEG_CHAR)
                sc_list = sc_str.split(SEG_CHAR)
                post_comment_async(bvid, sc_list, he_list, config)
        except Exception as err:
            try:
                request_json['trial'] = trial + 1
                if trial < 5:
                    video_posting_queue.put(request_json)
                else:
                    print(f"Too many trials for room {request_json['RoomId']} at {request_json['StartRecordTime']}")
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
            except Exception:
                print(f"Unknown video posting exception", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
        finally:
            print(f"Video posting queue length: {video_posting_queue.qsize()}", file=sys.stderr)
            sys.stderr.flush()


def comment_poster():
    global comment_task_list
    while True:
        try:
            items_to_remove = []
            if len(comment_task_list) != 0:
                print(f"checking {[task[0] for task in comment_task_list]}", file=sys.stderr)
                for idx, (bv_number, sc_comments, he_comments, config) in enumerate(comment_task_list):
                    if post_comment(bv_number, sc_comments, he_comments, config):
                        items_to_remove += [idx]
                if len(items_to_remove) != 0:
                    comment_task_list_lock.acquire(blocking=True)
                    comment_task_list = \
                        [comment_task for idx, comment_task in enumerate(comment_task_list) if idx not in
                         items_to_remove]
                    update_comment_task_list()
                    comment_task_list_lock.release()
        except Exception as err:
            print(f"Unknown video posting exception: {err}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
        finally:
            sys.stderr.flush()
            time.sleep(60)


# if __name__ == '__main__':
#     import threading
#     load_comment_task_list("./example_dir/comment-task.yaml")
#     with open('./example_dir/bilibili-config.yaml', 'r') as file:
#         bilibili_config = yaml.load(file, Loader=yaml.FullLoader)
#     # video_posting_queue.put({'EventRandomId': '34d3af43-02ab-468a-abbb-b7cd5d653f47', 'RoomId': 16405, 'Name': '★⑥檤轮囬★', 'Title': '回来了', 'RelativePath': '/Users/jackie/Downloads/bililive-docker/example_dir/16405-★⑥檤轮囬★/录制-16405-20210309-232932-回来了.flv', 'FileSize': 1590008206, 'StartRecordTime': '2021-03-09T23:29:32.2938893+08:00', 'EndRecordTime': '2021-03-10T02:44:40.889765+08:00'})
#     video_upload_thread = threading.Thread(target=video_poster)
#     comment_poster_thread = threading.Thread(target=comment_poster)
#
#     video_upload_thread.start()
#     comment_poster_thread.start()
