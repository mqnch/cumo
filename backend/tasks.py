import logging
import threading
from pathlib import Path
from typing import Optional

from huey import SqliteHuey
from huey.consumer import Consumer
from huey.constants import WORKER_THREAD

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "cumo.db"
huey = SqliteHuey("cumo", filename=str(DB_PATH))


@huey.task()
def debug_task(payload: Optional[dict] = None):
    logger.info("Huey debug task executed with payload=%s", payload)
    return {"ok": True, "payload": payload}


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
