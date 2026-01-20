import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from nlp import parse_text as parse_nlp_text, get_nlp_status

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


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


if __name__ == '__main__':
    app.run(
        debug=os.environ.get("CUMO_BACKEND_DEBUG", "0") == "1",
        host=_resolve_host(),
        port=_resolve_port(),
        use_reloader=False,
    )
