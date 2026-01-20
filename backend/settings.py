import json
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "settings.json"


def _load_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _save_settings(data: Dict[str, Any]) -> None:
    SETTINGS_PATH.write_text(json.dumps(data, indent=2, sort_keys=True))


def get_settings() -> Dict[str, Any]:
    return _load_settings()


def set_setting(key: str, value: Any) -> Dict[str, Any]:
    data = _load_settings()
    data[key] = value
    _save_settings(data)
    return data


def get_selected_calendar_id() -> Optional[str]:
    data = _load_settings()
    value = data.get("selectedCalendarId")
    if isinstance(value, str) and value:
        return value
    return None

