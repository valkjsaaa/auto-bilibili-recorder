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
extras_request_queue = Queue()


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
            print(danmaku_conversion_command)
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
            png_file_path = base_file_path + ".png"
            video_log_path = base_file_path + ".video.log"

            ffmpeg_command = f"ffmpeg -i \"{flv_file_path}\" -vf \"ass={ass_file_path}\" -c:v h264_nvenc" \
                             f" \"{m4v_file_path}\" >> \"{video_log_path}\" 2>&1"
            ffmpeg_command_img = f"ffmpeg -i \"{flv_file_path}\" -ss 00:10:00 -vframes 1 \"{png_file_path}\"" \
                                 f" >> \"{video_log_path}\" 2>&1"
            print(ffmpeg_command)
            print(ffmpeg_command_img)
            if os.system(ffmpeg_command) == 0 and os.system(ffmpeg_command_img) == 0:
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


def extras_processor():
    while True:
        request_json = danmaku_request_queue.get()
        try:
            flv_file_path = request_json['RelativePath']
            base_file_path = flv_file_path.rpartition('.')[0]
            xml_file_path = base_file_path + ".xml"
            graph_file_path = base_file_path + ".he.pdf"
            he_file_path = base_file_path + ".he.txt"
            sc_file_path = base_file_path + ".sc.txt"
            extras_log_path = base_file_path + ".extras.log"

            danmaku_extras_command = \
                f"python3 /DanmakuProcess/danmaku-energy-map.py " \
                f"--graph \"{graph_file_path}\" " \
                f"--he_map \"{he_file_path}\" " \
                f"--sc_list \"{sc_file_path}\" " \
                f"\"{xml_file_path}\" " \
                f">> \"{extras_log_path}\" 2>&1"
            print(danmaku_extras_command)

            if os.system(danmaku_extras_command) == 0:
                pass
            else:
                raise Exception("Danmaku process error")
            if (not os.path.isfile(graph_file_path)) \
                    or (not os.path.isfile(he_file_path)) \
                    or (not os.path.isfile(sc_file_path)):
                raise Exception("Danmaku extras cannot be found")
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown danmaku extras exception")
        finally:
            print(f"Danmaku extras queue length: {danmaku_request_queue.qsize()}")


danmaku_thread = threading.Thread(target=danmaku_processor)
video_thread = threading.Thread(target=video_processor)
extras_thread = threading.Thread(target=extras_processor)

danmaku_thread.start()
video_thread.start()
extras_thread.start()


@app.route('/process_video', methods=['POST'])
def respond():
    print(request.json)
    danmaku_request_queue.put(request.json)
    extras_request_queue.put(request.json)
    print(f"Danmaku queue length: {danmaku_request_queue.qsize()}")
    if danmaku_thread.is_alive() and video_thread.is_alive():
        return Response(status=200)
    else:
        return Response(status=500)
