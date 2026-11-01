from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import threading

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EYEVOX_SCRIPT = os.path.join(BASE_DIR, "eyevox.py")

eyevox_process = None
process_lock = threading.Lock()


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "app": "EYEVOX",
        "status": "connected"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "app": "EYEVOX",
        "health": "ok",
        "message": "Python server is running"
    })


@app.route("/eyevox/status", methods=["GET"])
def eyevox_status():
    global eyevox_process

    with process_lock:
        running = (
            eyevox_process is not None
            and eyevox_process.poll() is None
        )

    return jsonify({
        "running": running
    })


@app.route("/eyevox/start", methods=["POST"])
def start_eyevox():
    global eyevox_process

    with process_lock:
        if eyevox_process is not None and eyevox_process.poll() is None:
            return jsonify({
                "success": True,
                "message": "EYEVOX is already running"
            }), 200

        if not os.path.isfile(EYEVOX_SCRIPT):
            return jsonify({
                "success": False,
                "message": "eyevox.py file not found"
            }), 404

        try:
            eyevox_process = subprocess.Popen(
                [sys.executable, EYEVOX_SCRIPT],
                cwd=BASE_DIR
            )

            return jsonify({
                "success": True,
                "message": "EYEVOX started"
            }), 200

        except Exception as exc:
            eyevox_process = None
            return jsonify({
                "success": False,
                "message": str(exc)
            }), 500


@app.route("/eyevox/stop", methods=["POST"])
def stop_eyevox():
    global eyevox_process

    with process_lock:
        if eyevox_process is None or eyevox_process.poll() is not None:
            eyevox_process = None
            return jsonify({
                "success": True,
                "message": "EYEVOX is already stopped"
            }), 200

        try:
            eyevox_process.terminate()
            eyevox_process.wait(timeout=5)
            eyevox_process = None

            return jsonify({
                "success": True,
                "message": "EYEVOX stopped"
            }), 200

        except subprocess.TimeoutExpired:
            eyevox_process.kill()
            eyevox_process.wait()
            eyevox_process = None

            return jsonify({
                "success": True,
                "message": "EYEVOX stopped"
            }), 200

        except Exception as exc:
            return jsonify({
                "success": False,
                "message": str(exc)
            }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )