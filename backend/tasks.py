import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dateutil import parser as date_parser
from huey import SqliteHuey
from huey.consumer import Consumer
from huey.constants import WORKER_THREAD

from auth import get_calendar_service

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "cumo.db"
huey = SqliteHuey("cumo", filename=str(DB_PATH))


@huey.task()
def debug_task(payload: Optional[dict] = None):
    logger.info("Huey debug task executed with payload=%s", payload)
    return {"ok": True, "payload": payload}


def _coerce_datetime(value: str) -> datetime:
    parsed = date_parser.parse(value)
    if parsed.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed


def _build_event(payload: dict) -> dict:
    title = payload.get("title") or payload.get("summary") or "Untitled event"
    start_raw = payload.get("datetime") or payload.get("start")
    end_raw = payload.get("end_time") or payload.get("end")

    if not start_raw:
        raise ValueError("Missing start datetime in payload")

    start_dt = _coerce_datetime(str(start_raw))
    
    # Check if this should be an all-day event (time is midnight and no explicit end_time)
    is_all_day = (
        start_dt.hour == 0 and 
        start_dt.minute == 0 and 
        start_dt.second == 0 and 
        start_dt.microsecond == 0 and
        not end_raw
    )
    
    if is_all_day:
        # All-day event: use date format and set end to next day
        end_dt = start_dt + timedelta(days=1)
        return {
            "summary": title,
            "start": {"date": start_dt.strftime("%Y-%m-%d")},
            "end": {"date": end_dt.strftime("%Y-%m-%d")},
        }
    else:
        # Timed event: use dateTime format
        if end_raw:
            end_dt = _coerce_datetime(str(end_raw))
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        return {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        }


@huey.task()
def push_to_calendar(event_payload: dict, calendar_id: str):
    if not calendar_id:
        raise RuntimeError("No calendar selected")

    service = get_calendar_service()
    body = _build_event(event_payload)
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return {
        "id": created.get("id"),
        "htmlLink": created.get("htmlLink"),
    }


class ThreadedConsumer(Consumer):
    def _set_signal_handlers(self):
        if threading.current_thread() is threading.main_thread():
            super()._set_signal_handlers()


_consumer: Optional[Consumer] = None
_consumer_thread: Optional[threading.Thread] = None
_consumer_lock = threading.Lock()


def start_consumer() -> Optional[threading.Thread]:
    global _consumer, _consumer_thread
    with _consumer_lock:
        if _consumer_thread and _consumer_thread.is_alive():
            return _consumer_thread

        _consumer = ThreadedConsumer(huey, worker_type=WORKER_THREAD)

        def _run():
            try:
                _consumer.run()
            except Exception:
                logger.exception("Huey consumer crashed")

        _consumer_thread = threading.Thread(
            target=_run,
            name="HueyConsumer",
            daemon=True,
        )
        _consumer_thread.start()
        return _consumer_thread


def stop_consumer(graceful: bool = True, timeout: float = 5.0) -> None:
    global _consumer, _consumer_thread
    with _consumer_lock:
        consumer = _consumer
        thread = _consumer_thread

    if consumer:
        consumer.stop(graceful=graceful)
    if thread and thread.is_alive():
        thread.join(timeout=timeout)
