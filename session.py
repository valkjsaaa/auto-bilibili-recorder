import asyncio
import datetime
import os
import sys
import time
import traceback
from asyncio import Task
from typing import Optional

import dateutil.parser
from gpuinfo import GPUInfo

from commons import BINARY_PATH


async def async_wait_output(command):
    print(f"running: {command}")
    sys.stdout.flush()
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return_value = await process.communicate()
    sys.stdout.flush()
    sys.stderr.flush()
    return return_value


class Video:
    base_path: str
    session_id: str
    video_length: float
    room_id: int
    video_resolution: str
    video_length_flv: float

    def __init__(self, file_closed_event_json):
        flv_name = file_closed_event_json['EventData']['RelativePath']
        self.base_path = flv_name.rpartition('.')[0]
        self.session_id = file_closed_event_json["EventData"]["SessionId"]
        self.room_id = file_closed_event_json["EventData"]["RoomId"]
        self.video_length = file_closed_event_json["EventData"]["Duration"]

    def flv_file_path(self):
        return self.base_path + ".flv"

    def xml_file_path(self):
        return self.base_path + ".xml"

    async def gen_thumbnail(self, he_time, png_file_path, video_log_path):
        ffmpeg_command_img = f"ffmpeg -y -ss {he_time} -i \"{self.flv_file_path()}\" -vframes 1 \"{png_file_path}\"" \
                             f" >> \"{video_log_path}\" 2>&1"
        await async_wait_output(ffmpeg_command_img)

    async def query_meta(self):
        video_length_str = await async_wait_output(
            f'ffprobe -v error -show_entries format=duration '
            f'-of default=noprint_wrappers=1:nokey=1 "{self.flv_file_path()}"'
        )
        video_resolution_str = await async_wait_output(
            f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height '
            f'-of csv=s=x:p=0 "{self.flv_file_path()}"'
        )
        self.video_length_flv = float(video_length_str[0].decode('utf-8').strip())
        self.video_resolution = str(video_resolution_str[0].decode('utf-8').strip())


class Session:
    session_id: str
    start_time: time.time
    end_time: Optional[datetime.datetime]
    room_id: int
    videos: [Video]
    total_length: float
    notify_length: int
    length_alert: bool
    he_time: Optional[float]
    early_video_path: Optional[str]
    room_name: str
    room_title: str

    def __init__(self, session_start_event_json, notify_length=60):
        self.start_time = dateutil.parser.isoparse(session_start_event_json["EventTimestamp"])
        self.session_id = session_start_event_json["EventData"]["SessionId"]
        self.room_id = session_start_event_json["EventData"]["RoomId"]
        self.end_time = None
        self.notify_length = notify_length
        self.length_alert = False
        self.total_length = 0
        self.videos = []
        self.he_time = None
        self.early_video_path = None
        self.process_update(session_start_event_json)
        self.upload_task: Optional[Task] = None

    def process_update(self, update_json):
        self.room_name = update_json["EventData"]["Name"]
        self.room_title = update_json["EventData"]["Title"]
        if update_json["EventType"] == "SessionEnded":
            self.end_time = dateutil.parser.isoparse(update_json["EventTimestamp"])

    async def add_video(self, video):
        try:
            await video.query_meta()
        except ValueError:
            print(traceback.format_exc())
            print(f"video corrupted, skipping: {video.flv_file_path()}")
            return
        self.videos += [video]
        new_length = self.total_length + video.video_length
        if (new_length // self.notify_length) != (self.total_length // self.notify_length):
            self.length_alert = True
        self.total_length += new_length

    def output_base_path(self):
        return self.videos[0].base_path + ".all"

    def output_path(self):
        return {
            "xml": self.output_base_path() + ".xml",
            "ass": self.output_base_path() + ".ass",
            "early_video": self.output_base_path() + ".flv",
            "danmaku_video": self.output_base_path() + ".bar.mp4",
            "concat_file": self.output_base_path() + ".concat.txt",
            "thumbnail": self.output_base_path() + ".thumb.png",
            "he_graph": self.output_base_path() + ".he.png",
            "he_file": self.output_base_path() + ".he.txt",
            "sc_file": self.output_base_path() + ".sc.txt",
            "sc_srt": self.output_base_path() + ".sc.srt",
            "he_pos": self.output_base_path() + ".he_pos.txt",
            "extras_log": self.output_base_path() + ".extras.log",
            "video_log": self.output_base_path() + ".video.log",
        }

    async def merge_xml(self):
        xmls = ' '.join(['"' + video.xml_file_path() + '"' for video in self.videos])
        danmaku_merge_command = \
            f"python3 {BINARY_PATH}DanmakuProcess/danmaku_energy_map/merge_danmaku.py " \
            f"{xmls} " \
            f"--video_time \".flv\" " \
            f"--output \"{self.output_path()['xml']}\" " \
            f">> \"{self.output_path()['extras_log']}\" 2>&1"
        await async_wait_output(danmaku_merge_command)

    async def process_xml(self):
        danmaku_extras_command = \
            f"python3 {BINARY_PATH}DanmakuProcess/danmaku_energy_map/danmaku_energy_map.py " \
            f"--graph \"{self.output_path()['he_graph']}\" " \
            f"--he_map \"{self.output_path()['he_file']}\" " \
            f"--sc_list \"{self.output_path()['sc_file']}\" " \
            f"--he_time \"{self.output_path()['he_pos']}\" " \
            f"--sc_srt \"{self.output_path()['sc_srt']}\" " \
            f"\"{self.output_path()['xml']}\" " \
            f">> \"{self.output_path()['extras_log']}\" 2>&1"
        await async_wait_output(danmaku_extras_command)
        with open(self.output_path()['he_pos'], 'r') as file:
            he_time_str = file.readline()
            self.he_time = float(he_time_str)

    def generate_concat(self):
        concat_text = "\n".join([f"file '{os.path.basename(video.flv_file_path())}'" for video in self.videos])
        with open(self.output_path()['concat_file'], 'w') as concat_file:
            concat_file.write(concat_text)

    async def process_thumbnail(self):
        local_he_time = self.he_time
        thumbnail_generated = False
        for video in self.videos:
            if local_he_time < video.video_length_flv:
                await video.gen_thumbnail(local_he_time, self.output_path()['thumbnail'],
                                          self.output_path()['video_log'])
                thumbnail_generated = True
                break
            local_he_time -= video.video_length_flv
        if not thumbnail_generated:  # Rare case where he_pos is after the last video
            print(f"{self.output_path()['video']}: thumbnail at {local_he_time} cannot be found")
            await self.videos[-1].gen_thumbnail(
                self.videos[-1].video_length_flv / 2,
                self.output_path()['thumbnail'],
                self.output_path()['video_log']
            )

    async def process_danmaku(self):
        danmaku_conversion_command = \
            f"{BINARY_PATH}DanmakuFactory/DanmakuFactory " \
            f"--ignore-warnings " \
            f"-o \"{self.output_path()['ass']}\" " \
            f"-i \"{self.output_path()['xml']}\" " \
            f"--fontname \"Noto Sans CJK SC\" -S 50 " \
            f">> \"{self.output_path()['extras_log']}\" 2>&1"
        await async_wait_output(danmaku_conversion_command)

    async def process_early_video(self):
        if len(self.videos) == 1:
            self.early_video_path = self.videos[0].flv_file_path
        format_check = True
        ref_video_res = self.videos[0].video_resolution
        for video in self.videos:
            if video.video_resolution != ref_video_res:
                format_check = False
                break
        if not format_check:
            return
        ffmpeg_command = f'''ffmpeg \
        -f concat \
        -safe 0 \
        -i "{self.output_path()['concat_file']}" \
        -c copy "{self.output_path()['early_video']}" >> "{self.output_path()["video_log"]}" 2>&1'''
        await async_wait_output(ffmpeg_command)
        self.early_video_path = self.output_path()['early_video']

    async def process_video(self):
        total_time = sum([video.video_length_flv for video in self.videos])
        max_size = 8000_000 * 8  # Kb
        audio_bitrate = 320
        video_bitrate = (max_size / total_time - audio_bitrate) - 500  # just to be safe
        max_video_bitrate = float(8000)  # BiliBili now re-encode every video anyways
        video_bitrate = int(min(max_video_bitrate, video_bitrate))
        ffmpeg_command = f'''ffmpeg -y -loop 1 -t {total_time} \
        -i "{self.output_path()['he_graph']}" \
        -f concat \
        -safe 0 \
        -i "{self.output_path()['concat_file']}" \
        -t {total_time} \
        -filter_complex "
        [0:v][1:v]scale2ref=iw:iw*(main_h/main_w)[color][ref];
        [color]split[color1][color2];
        [color1]hue=s=0[gray];
        [color2]negate=negate_alpha=1[color_neg];
        [gray]negate=negate_alpha=1[gray_neg];
        color=black:d={total_time}[black];
        [black][ref]scale2ref[blackref][ref2];
        [blackref]split[blackref1][blackref2];
        [color_neg][blackref1]overlay=x=t/{total_time}*W-W[color_crop_neg];
        [gray_neg][blackref2]overlay=x=t/{total_time}*W[gray_crop_neg];
        [color_crop_neg]negate=negate_alpha=1[color_crop];
        [gray_crop_neg]negate=negate_alpha=1[gray_crop];
        [ref2][color_crop]overlay=y=main_h-overlay_h[out_color];
        [out_color][gray_crop]overlay=y=main_h-overlay_h[out];
        [out]ass='{self.output_path()['ass']}'[out_sub]" \
        -map "[out_sub]" -map 1:a ''' + \
                         (" -c:v h264_nvenc -preset slow "
                          if GPUInfo.check_empty() is not None else " -c:v libx264 -preset medium ") + \
                         f'-b:v {video_bitrate}K' + f''' -b:a 320K -ar 44100  "{self.output_path()['danmaku_video']}" \
                    ''' + f'>> "{self.output_path()["video_log"]}" 2>&1'
        await async_wait_output(ffmpeg_command)

    async def gen_early_video(self):
        if len(self.videos) == 0:
            print(f"No video in session for {self.room_id}@{self.start_time}, skip!")
            return
        await self.merge_xml()
        await self.process_xml()
        await self.process_danmaku()
        await self.process_thumbnail()
        self.generate_concat()
        await self.process_early_video()

    async def gen_danmaku_video(self):
        if len(self.videos) == 0:
            print(f"No video in session for {self.room_id}@{self.start_time}, skip!")
            return
        await self.process_video()

#
# if __name__ == '__main__':
#     BINARY_PATH = "../exes/"
#     session_json = {'EventType': 'SessionStarted', 'EventTimestamp': '2021-04-09T22:50:15.301987-07:00',
#                     'EventId': '6379acb5-0dfd-465e-bb03-58d9867e7591',
#                     'EventData': {'SessionId': 'e3807981-3104-402a-ad71-8d42023c787d', 'RoomId': 1016219, 'ShortId': 0,
#                                   'Name': '隐染啊', 'Title': '不要自闭挑战', 'AreaNameParent': '娱乐', 'AreaNameChild': '户外'}}
#     video_json_list = [
#         {'EventType': 'FileClosed', 'EventTimestamp': '2021-04-09T23:44:37.128312-07:00',
#          'EventId': '114c0b8d-80a3-4d2e-81f5-9d1ba17f4acd',
#          'EventData': {'RelativePath': '1016219-隐染啊/录制-1016219-20210409-234332-不要自闭挑战.flv', 'FileSize': 8488458,
#                        'Duration': 63.646, 'FileOpenTime': '2021-04-09T23:43:32.456413-07:00',
#                        'FileCloseTime': '2021-04-09T23:44:37.128288-07:00',
#                        'SessionId': '22fa4a41-6e75-4ed6-8352-2a2449eeb252', 'RoomId': 1016219, 'ShortId': 0,
#                        'Name': '隐染啊', 'Title': '不要自闭挑战', 'AreaNameParent': '娱乐', 'AreaNameChild': '户外'}},
#         {'EventType': 'FileClosed', 'EventTimestamp': '2021-04-09T23:45:43.996789-07:00',
#          'EventId': 'ff29a876-06c6-4007-8f4a-25da210ab043',
#          'EventData': {'RelativePath': '1016219-隐染啊/录制-1016219-20210409-234437-不要自闭挑战.flv', 'FileSize': 8528472,
#                        'Duration': 66.796, 'FileOpenTime': '2021-04-09T23:44:37.128482-07:00',
#                        'FileCloseTime': '2021-04-09T23:45:43.996718-07:00',
#                        'SessionId': '22fa4a41-6e75-4ed6-8352-2a2449eeb252', 'RoomId': 1016219, 'ShortId': 0,
#                        'Name': '隐染啊', 'Title': '不要自闭挑战', 'AreaNameParent': '娱乐', 'AreaNameChild': '户外'}},
#         {'EventType': 'FileClosed', 'EventTimestamp': '2021-04-09T23:46:50.169678-07:00',
#          'EventId': '89d52da7-4cf4-46eb-84e3-be050c21f5f8',
#          'EventData': {'RelativePath': '1016219-隐染啊/录制-1016219-20210409-234543-不要自闭挑战.flv', 'FileSize': 8665668,
#                        'Duration': 66.923, 'FileOpenTime': '2021-04-09T23:45:43.997006-07:00',
#                        'FileCloseTime': '2021-04-09T23:46:50.16964-07:00',
#                        'SessionId': '22fa4a41-6e75-4ed6-8352-2a2449eeb252', 'RoomId': 1016219, 'ShortId': 0,
#                        'Name': '隐染啊', 'Title': '不要自闭挑战', 'AreaNameParent': '娱乐', 'AreaNameChild': '户外'}},
#         {'EventType': 'FileClosed', 'EventTimestamp': '2021-04-09T23:46:55.203116-07:00',
#          'EventId': '39e1aff4-7d3d-45ec-a228-492244677353',
#          'EventData': {'RelativePath': '1016219-隐染啊/录制-1016219-20210409-234650-不要自闭挑战.flv', 'FileSize': 993789,
#                        'Duration': 7.463, 'FileOpenTime': '2021-04-09T23:46:50.16998-07:00',
#                        'FileCloseTime': '2021-04-09T23:46:55.2031-07:00',
#                        'SessionId': '22fa4a41-6e75-4ed6-8352-2a2449eeb252', 'RoomId': 1016219, 'ShortId': 0,
#                        'Name': '隐染啊', 'Title': '不要自闭挑战', 'AreaNameParent': '娱乐', 'AreaNameChild': '户外'}}
#     ]
#     session = Session(session_json)
#     video_tasks = []
#     for video_json in video_json_list:
#         video = Video(video_json)
#         asyncio.run(session.add_video(video))
#
#     asyncio.run(session.gen_early_video())
#     asyncio.run(session.gen_danmaku_video())
