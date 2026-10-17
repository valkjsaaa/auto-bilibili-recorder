import subprocess

from commons import BINARY_PATH
from recorder_config import RecoderRoom


def spawn_recorder(room: RecoderRoom):
    cookie_command = ""
    if room.recorder_obj is not None:
        recorder_obj = room.recorder_obj
        cookie_dict = recorder_obj.get_cookie_dict()
        # if any cookie value is None, we can't use it for recording
        if None in cookie_dict.values():
            print(f"invalid cookie for {room.id}, connect to websocket without cookie.")
        else:
            cookie_command = "--cookie \"" + "; ".join([f"{k}={v}" for k, v in cookie_dict.items()]) + "\" "
            print(f"recorder for {room.id} with cookie of {recorder_obj.key}")
    else:
        print(f"no recorder for {room.id}, connect to websocket without cookie.")
    # exec so that terminate() reaches the recorder instead of only the wrapping shell
    spawn_command = \
        f"exec {BINARY_PATH}BililiveRecorder/BililiveRecorder.Cli " \
        f"portable " \
        f"-d 63 " \
        f"--webhook-url " \
        f'"http://127.0.0.1:10261/process_video" ' \
        f'--filename ' \
        '"{{ roomId }}/{{ \\"now\\" | time_zone: \\"Asia/Shanghai\\" | format_date: \\"yyyyMMdd\\" }}/'\
        '{{ roomId }}-{{ \\"now\\" | time_zone: \\"Asia/Shanghai\\" | format_date: \\"yyyyMMdd-HHmmss-fff\\" }}.flv" ' \
        f'{cookie_command}' \
        f'/storage/ ' \
        f'{room.id} '
    print(f"spawn recorder for {room.id}")
    return subprocess.Popen(spawn_command, shell=True)


def stop_recorder(process: subprocess.Popen):
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


class RecorderManager:

    def __init__(self, rooms: [RecoderRoom]):
        self.recorder_dict: {int: subprocess.Popen} = {room: spawn_recorder(room) for room in rooms}

    def update_rooms(self, new_rooms, dry_run=False):
        current_rooms = set(self.recorder_dict.keys())
        new_rooms_set = set(new_rooms)
        to_del_rooms = current_rooms.difference(new_rooms_set)
        to_new_rooms = new_rooms_set.difference(current_rooms)
        if not dry_run:
            for room in to_new_rooms:
                self.recorder_dict[room] = spawn_recorder(room)
            for room in to_del_rooms:
                stop_recorder(self.recorder_dict[room])
                del self.recorder_dict[room]
        return to_new_rooms, to_del_rooms

    def restart_room(self, room):
        """Respawns a recorder, e.g. to pick up refreshed cookies."""
        print(f"restarting recorder for {room.id}")
        stop_recorder(self.recorder_dict[room])
        self.recorder_dict[room] = spawn_recorder(room)


if __name__ == '__main__':
    import time
    BINARY_PATH = "../exes/"
    manager = RecorderManager([RecoderRoom({"id": 3})])

    time.sleep(10)

    manager.update_rooms([3])
    time.sleep(10)
