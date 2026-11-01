from flask import Flask, jsonify, request
from flask_cors import CORS
import eyevox

app = Flask(__name__)

# Explicitly allow Vite development ports
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5179",
                "http://127.0.0.1:5179",
            ]
        }
    }
)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "app": "EYEVOX",
        "status": "connected"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/eyevox/status", methods=["GET"])
def eyevox_status():
    try:
        return jsonify(eyevox.get_preview_status())
    except Exception as error:
        app.logger.exception("Status error")
        return jsonify({
            "running": False,
            "message": str(error)
        }), 500


@app.route("/eyevox/start", methods=["POST"])
def start_eyevox():
    try:
        result = eyevox.start_engine()

        return jsonify({
            "success": True,
            "message": str(result or "EYEVOX started")
        })

    except Exception as error:
        app.logger.exception("Start error")
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route("/eyevox/stop", methods=["POST"])
def stop_eyevox():
    try:
        result = eyevox.stop_engine()

        return jsonify({
            "success": True,
            "message": str(result or "EYEVOX stopped")
        })

    except Exception as error:
        app.logger.exception("Stop error")
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route("/eyevox/frame", methods=["POST"])
def process_eyevox_frame():
    try:
        frame_bytes = request.get_data(cache=False)

        if not frame_bytes:
            return jsonify({
                "success": False,
                "message": "Empty camera frame"
            }), 400

        result = eyevox.process_frame(frame_bytes)

        return jsonify(result)

    except Exception as error:
        app.logger.exception("Frame processing error")

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )