#!/usr/bin/python3
import os
import sys

from flask import Flask, request, Response
import threading

import socket

from queue import Queue

os.chdir("/storage")


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


print(get_ip_address())

app = Flask(__name__)

danmaku_request_queue = Queue()
video_request_queue = Queue()


def danmaku_processor():
    while True:
        request_json = danmaku_request_queue.get()
        try:
            flv_file_path = request_json['RelativePath']
            base_file_path = flv_file_path.rpartition('.')[0]
            xml_file_path = base_file_path + ".xml"
            ass_file_path = base_file_path + ".ass"
            danmaku_log_path = base_file_path + ".danmaku.log"

            danmaku_conversion_command = \
                f"/DanmakuFactory/DanmakuFactory -o \"{ass_file_path}\" -i \"{xml_file_path}\" " \
                f"--fontname \"Noto Sans CJK\" " \
                f">> \"{danmaku_log_path}\" 2>&1"
            if os.system(danmaku_conversion_command) == 0:
                video_request_queue.put(request_json)
                print(f"Video queue length: {video_request_queue.qsize()}")
            else:
                raise Exception("Danmaku process error")
            if not os.path.isfile(ass_file_path):
                raise Exception("Danmaku file cannot be found")
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown danmaku exception")
        finally:
            print(f"Danmaku queue length: {danmaku_request_queue.qsize()}")


def video_processor():
    while True:
        request_json = video_request_queue.get()
        try:
            flv_file_path = request_json['RelativePath']
            base_file_path = flv_file_path.rpartition('.')[0]
            ass_file_path = base_file_path + ".ass"
            m4v_file_path = base_file_path + ".m4v"
            video_log_path = base_file_path + ".video.log"

            ffmpeg_command = f"ffmpeg -i \"{flv_file_path}\" -vf \"ass={ass_file_path}\" \"{m4v_file_path}\"" \
                             f" >> \"{video_log_path}\" 2>&1"
            if os.system(ffmpeg_command) == 0:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: Processing completed")
            else:
                raise Exception("Video process error")
            if not os.path.isfile(ass_file_path):
                raise Exception("Video file cannot be found")
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown video exception")
        finally:
            print(f"Video queue length: {danmaku_request_queue.qsize()}")


danmaku_thread = threading.Thread(target=danmaku_processor)
video_thread = threading.Thread(target=video_processor)

danmaku_thread.start()
video_thread.start()


@app.route('/process_video', methods=['POST'])
def respond():
    print(request.json)
    danmaku_request_queue.put(request.json)
    print(f"Danmaku queue length: {danmaku_request_queue.qsize()}")
    if danmaku_thread.is_alive() and video_thread.is_alive():
        return Response(status=200)
    else:
        return Response(status=500)
