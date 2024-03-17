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


if __name__ == "__main__":
    app.run(port=10261)
