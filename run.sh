FLASK_APP=/webhook/process_video.py MODE=PRODUCTION python3 -m flask run --port 10621 >> /storage/flask.log 2>&1 &

BililiveRecorder/BililiveRecorder.Cli/bin/Release/netcoreapp3.1/BililiveRecorder.Cli run /storage/