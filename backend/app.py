import atexit
import logging
import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from nlp import parse_text as parse_nlp_text, get_nlp_status
from tasks import debug_task, start_consumer, stop_consumer

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logger = logging.getLogger(__name__)

_consumer_started = False


def _ensure_consumer_started() -> None:
    global _consumer_started
    if _consumer_started:
        return
    start_consumer()
    _consumer_started = True


atexit.register(lambda: stop_consumer(graceful=True))


def _resolve_port() -> int:
    raw = os.environ.get("CUMO_BACKEND_PORT") or os.environ.get("PORT") or "5000"
    try:
        return int(raw)
    except ValueError:
        return 5000


def _resolve_host() -> str:
    return os.environ.get("CUMO_BACKEND_HOST", "127.0.0.1")


@app.route('/parse', methods=['POST'])
def parse_text():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' field in request body"}), 400

    text = data.get('text', '')

    if not isinstance(text, str):
        return jsonify({"error": "'text' must be a string"}), 400
    try:
        result = parse_nlp_text(text)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": f"Parsing failed: {str(exc)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "nlp": get_nlp_status()}), 200


@app.route('/debug/enqueue', methods=['POST'])
def debug_enqueue():
    payload = request.get_json(silent=True) or {}
    result = debug_task(payload)
    task_id = getattr(result, 'id', None)
    return jsonify({"enqueued": True, "task_id": task_id}), 200


if __name__ == '__main__':
    _ensure_consumer_started()
    app.run(
        debug=os.environ.get("CUMO_BACKEND_DEBUG", "0") == "1",
        host=_resolve_host(),
        port=_resolve_port(),
        use_reloader=False,
    )
