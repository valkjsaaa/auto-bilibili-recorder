#!/usr/bin/python3
import os
import sys

from flask import Flask, request, Response
import threading

import socket

from queue import Queue
from gpuinfo import GPUInfo

os.chdir("/storage")


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


print(get_ip_address(), file=sys.stderr)

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
                f"--fontname \"Noto Sans CJK\" -S 50 " \
                f">> \"{danmaku_log_path}\" 2>&1"
            print(danmaku_conversion_command, file=sys.stderr)
            if os.system(danmaku_conversion_command) != 0:
                print("Danmaku process error", file=sys.stderr)
            if not os.path.isfile(ass_file_path):
                raise Exception("Danmaku file cannot be found")
            else:
                extras_request_queue.put(request_json)
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown danmaku exception", file=sys.stderr)
        finally:
            print(f"Danmaku queue length: {danmaku_request_queue.qsize()}", file=sys.stderr)
            sys.stderr.flush()


def video_processor():
    while True:
        request_json = video_request_queue.get()
        try:
            flv_file_path = request_json['RelativePath']
            he_time = request_json['he_time']
            base_file_path = flv_file_path.rpartition('.')[0]
            video_file_path = base_file_path + ".bar.mp4"
            png_file_path = base_file_path + ".png"
            video_log_path = base_file_path + ".video.log"

            ffmpeg_command_img = f"ffmpeg -ss {he_time} -i \"{flv_file_path}\" -vframes 1 \"{png_file_path}\"" \
                                 f" >> \"{video_log_path}\" 2>&1"
            print(ffmpeg_command_img, file=sys.stderr)
            return_value = os.system(ffmpeg_command_img)
            return_text = "Processing completed" if return_value == 0 else "Processing error"
            print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: image {return_text}",
                  file=sys.stderr)
            if not os.path.isfile(png_file_path):
                raise Exception("Video preview file cannot be found")
            ffmpeg_command = f'FILE=\"{base_file_path}\" ' + ''' \
&& TIME=`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${FILE}.flv"`\
&& ffmpeg -loop 1 -t ${TIME} \
-i "${FILE}.he.png" \
-i "${FILE}.flv" \
-filter_complex "
[0:v][1:v]scale2ref=iw:iw*(main_h/main_w)[color][ref];
[color]split[color1][color2];
[color1]hue=s=0[gray];
[color2]negate=negate_alpha=1[color_neg];
[gray]negate=negate_alpha=1[gray_neg];
color=black:d=${TIME}[black];
[black][ref]scale2ref[blackref][ref2];
[blackref]split[blackref1][blackref2];
[color_neg][blackref1]overlay=x=t/${TIME}*W-W[color_crop_neg];
[gray_neg][blackref2]overlay=x=t/${TIME}*W[gray_crop_neg];
[color_crop_neg]negate=negate_alpha=1[color_crop];
[gray_crop_neg]negate=negate_alpha=1[gray_crop];
[ref2][color_crop]overlay=y=main_h-overlay_h[out_color];
[out_color][gray_crop]overlay=y=main_h-overlay_h[out];
[out]ass='${FILE}.ass'[out_sub]" \
-map "[out_sub]" -map 1:a ''' + \
                             (" -c:v h264_nvenc -preset slow "
                              if GPUInfo.check_empty() is not None else " -c:v libx264 -preset medium ") + \
                             '''-b:v 4500K -b:a 320K -ar 44100  "${FILE}.bar.mp4" \
            ''' + f'>> "{video_log_path}" 2>&1'
            print(ffmpeg_command, file=sys.stderr)
            return_value = os.system(ffmpeg_command)
            return_text = "Processing completed" if return_value == 0 else "Processing error"
            print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: video {return_text}",
                  file=sys.stderr)
            if not os.path.isfile(video_file_path):
                raise Exception("Video file cannot be found")
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown video exception", file=sys.stderr)
        finally:
            print(f"Video queue length: {danmaku_request_queue.qsize()}", file=sys.stderr)
            sys.stderr.flush()


def extras_processor():
    while True:
        request_json = extras_request_queue.get()
        try:
            flv_file_path = request_json['RelativePath']
            base_file_path = flv_file_path.rpartition('.')[0]
            xml_file_path = base_file_path + ".xml"
            graph_file_path = base_file_path + ".he.png"
            he_file_path = base_file_path + ".he.txt"
            sc_file_path = base_file_path + ".sc.txt"
            he_pos_file_path = base_file_path + ".he_pos.txt"
            extras_log_path = base_file_path + ".extras.log"

            danmaku_extras_command = \
                f"python3 /DanmakuProcess/danmaku_energy_map/danmaku_energy_map.py " \
                f"--graph \"{graph_file_path}\" " \
                f"--he_map \"{he_file_path}\" " \
                f"--sc_list \"{sc_file_path}\" " \
                f"--he_time \"{he_pos_file_path}\" " \
                f"\"{xml_file_path}\" " \
                f">> \"{extras_log_path}\" 2>&1"
            print(danmaku_extras_command, file=sys.stderr)

            if os.system(danmaku_extras_command) == 0:
                pass
            else:
                raise Exception("Danmaku process error")
            if (not os.path.isfile(graph_file_path)) \
                    or (not os.path.isfile(he_file_path)) \
                    or (not os.path.isfile(sc_file_path)) \
                    or (not os.path.isfile(he_pos_file_path)):
                raise Exception("Danmaku extras cannot be found")
            else:
                with open(he_pos_file_path, 'r') as file:
                    he_time = file.readline()
                request_json['he_time'] = he_time
                video_request_queue.put(request_json)
        except Exception as err:
            # noinspection PyBroadException
            try:
                print(f"Room {request_json['RoomId']} at {request_json['StartRecordTime']}: {err}", file=sys.stderr)
            except Exception:
                print(f"Unknown danmaku extras exception", file=sys.stderr)
        finally:
            print(f"Danmaku extras queue length: {danmaku_request_queue.qsize()}", file=sys.stderr)
            sys.stderr.flush()


danmaku_thread = threading.Thread(target=danmaku_processor)
video_thread = threading.Thread(target=video_processor)
extras_thread = threading.Thread(target=extras_processor)

danmaku_thread.start()
video_thread.start()
extras_thread.start()


@app.route('/process_video', methods=['POST'])
def respond():
    print(request.json, file=sys.stderr)
    danmaku_request_queue.put(request.json)
    print(f"Danmaku queue length: {danmaku_request_queue.qsize()}", file=sys.stderr)
    if danmaku_thread.is_alive() and video_thread.is_alive():
        return Response(status=200)
    else:
        return Response(status=500)
