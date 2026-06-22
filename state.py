import json
import os
import uuid
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_AXES_FILE = os.path.join(_DATA_DIR, "appeal_axes.json")
_BANNERS_FILE = os.path.join(_DATA_DIR, "banners.json")
_BANNERS_IMG_DIR = os.path.join(_DATA_DIR, "banners")


# ── Appeal axes ───────────────────────────────────────────────────────────────

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


# ── Saved banners ─────────────────────────────────────────────────────────────

def load_banners() -> list[dict]:
    if not os.path.exists(_BANNERS_FILE):
        return []
    with open(_BANNERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_banner_entry(
    product_name: str,
    axis_label: str,
    variation: dict,
    platform_images: list,
    tonmana: str,
    objective: str,
) -> dict:
    banner_id = str(uuid.uuid4())
    img_dir = os.path.join(_BANNERS_IMG_DIR, banner_id)
    os.makedirs(img_dir, exist_ok=True)

    saved_platforms = []
    for platform, img in platform_images:
        filename = f"{platform.filename}_{platform.width}x{platform.height}.png"
        fpath = os.path.join(img_dir, filename)
        img.save(fpath, "PNG", optimize=True)
        saved_platforms.append({
            "platform_name": platform.name,
            "filename": filename,
            "path": fpath,
            "width": platform.width,
            "height": platform.height,
        })

    entry = {
        "id": banner_id,
        "product_name": product_name,
        "axis": axis_label,
        "variation": variation.get("variation", ""),
        "label": variation.get("label", ""),
        "prompt": variation.get("prompt", ""),
        "rationale": variation.get("rationale", ""),
        "tonmana": tonmana,
        "objective": objective,
        "platforms": saved_platforms,
        "created_at": datetime.now().isoformat(),
    }

    banners = load_banners()
    banners.append(entry)
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_BANNERS_FILE, "w", encoding="utf-8") as f:
        json.dump(banners, f, ensure_ascii=False, indent=2)

    return entry


def delete_banner(banner_id: str) -> None:
    import shutil
    banners = [b for b in load_banners() if b["id"] != banner_id]
    img_dir = os.path.join(_BANNERS_IMG_DIR, banner_id)
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_BANNERS_FILE, "w", encoding="utf-8") as f:
        json.dump(banners, f, ensure_ascii=False, indent=2)
