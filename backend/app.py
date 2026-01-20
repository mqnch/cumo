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
from tasks import debug_task, push_to_calendar, start_consumer, stop_consumer
from auth import get_calendar_service
from settings import get_selected_calendar_id, get_settings, set_setting

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
    raw = os.environ.get("CUMO_BACKEND_PORT") or os.environ.get("PORT") or "5001"
    try:
        return int(raw)
    except ValueError:
        return 5001


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


@app.route('/calendars', methods=['GET'])
def calendars():
    try:
        service = get_calendar_service()
        items = service.calendarList().list().execute().get("items", [])
        calendars = [
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "primary": item.get("primary", False),
                "accessRole": item.get("accessRole"),
            }
            for item in items
        ]
        return jsonify({"calendars": calendars}), 200
    except Exception as exc:
        return jsonify({"error": f"Failed to load calendars: {str(exc)}"}), 500


@app.route('/settings', methods=['GET'])
def settings():
    return jsonify(get_settings()), 200


@app.route('/settings/calendar', methods=['POST'])
def set_calendar():
    data = request.get_json(silent=True) or {}
    calendar_id = data.get("calendarId")
    if not calendar_id or not isinstance(calendar_id, str):
        return jsonify({"error": "Missing calendarId"}), 400
    updated = set_setting("selectedCalendarId", calendar_id)
    return jsonify(updated), 200


@app.route('/debug/enqueue', methods=['POST'])
def debug_enqueue():
    payload = request.get_json(silent=True) or {}
    result = debug_task(payload)
    task_id = getattr(result, 'id', None)
    return jsonify({"enqueued": True, "task_id": task_id}), 200


@app.route('/schedule', methods=['POST'])
def schedule():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    calendar_id = get_selected_calendar_id()
    if not calendar_id:
        return jsonify({"error": "No calendar selected"}), 400

    event_payload = None
    if isinstance(data, dict):
        if isinstance(data.get("event"), dict):
            event_payload = data["event"]
        elif "text" in data:
            text = data.get("text")
            if not isinstance(text, str):
                return jsonify({"error": "'text' must be a string"}), 400
            event_payload = parse_nlp_text(text)
        else:
            event_payload = data

    if not isinstance(event_payload, dict):
        return jsonify({"error": "Invalid event payload"}), 400

    result = push_to_calendar(event_payload, calendar_id)
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
