import json
import os
import uuid
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_AXES_FILE = os.path.join(_DATA_DIR, "appeal_axes.json")


def load_axes() -> list[dict]:
    if not os.path.exists(_AXES_FILE):
        return []
    with open(_AXES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def add_axis(
    product_name: str,
    product_url: str,
    axis: dict,
    product_context: dict | None = None,
) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "product_name": product_name,
        "product_url": product_url,
        **axis,
        "product_context": product_context or {},
        "created_at": datetime.now().isoformat(),
    }
    axes = load_axes()
    axes.append(entry)
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_AXES_FILE, "w", encoding="utf-8") as f:
        json.dump(axes, f, ensure_ascii=False, indent=2)
    return entry


def delete_axis(axis_id: str) -> None:
    axes = [a for a in load_axes() if a["id"] != axis_id]
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_AXES_FILE, "w", encoding="utf-8") as f:
        json.dump(axes, f, ensure_ascii=False, indent=2)
