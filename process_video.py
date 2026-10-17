from quart import Quart, request, Response

from record_upload_manager import RecordUploadManager

from bilibili_api import settings

settings.timeout = 60.0

app = Quart(__name__)

record_upload_manager = RecordUploadManager("./recorder_config.yaml", "recorder_save.yaml")


@app.route('/process_video', methods=['POST'])
async def respond_process():
    json_request = await request.json
    print(json_request)
    await record_upload_manager.handle_update(json_request)
    return Response(response="", status=200)


@app.route('/reprocess', methods=['POST'])
async def respond_reprocess():
    """{"flv_paths": ["128308/20261015/128308-20261015-115616-200.flv", ...]}, relative to /storage"""
    json_request = await request.json
    session_id = record_upload_manager.replay_session(json_request["flv_paths"])
    return Response(response=session_id, status=200)


if __name__ == "__main__":
    # no reloader: it re-execs on any /webhook file change and fails with "Exec format error"
    app.run(port=10261, use_reloader=False)
