"""Persistence layer — Supabase backend."""

import io
import os
import uuid
from datetime import datetime

from supabase import create_client, Client

_BUCKET = "banner-images"


def _client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL と SUPABASE_KEY が設定されていません。"
            ".env ファイルまたは Streamlit Cloud の Secrets を確認してください。"
        )
    return create_client(url, key)


# ── Appeal axes ───────────────────────────────────────────────────────────────

def load_axes() -> list[dict]:
    res = _client().table("appeal_axes").select("*").order("created_at").execute()
    return res.data or []


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
        "axis": axis.get("axis", ""),
        "description": axis.get("description", ""),
        "target_segment": axis.get("target_segment", ""),
        "rationale": axis.get("rationale", ""),
        "copy_suggestions": axis.get("copy_suggestions", {}),
        "product_context": product_context or {},
        "created_at": datetime.now().isoformat(),
    }
    _client().table("appeal_axes").insert(entry).execute()
    return entry


def delete_axis(axis_id: str) -> None:
    _client().table("appeal_axes").delete().eq("id", axis_id).execute()


# ── Saved banners ─────────────────────────────────────────────────────────────

def load_banners() -> list[dict]:
    res = _client().table("banners").select("*").order("created_at").execute()
    return res.data or []


def save_banner_entry(
    product_name: str,
    axis_label: str,
    variation: dict,
    platform_images: list,
    tonmana: str,
    objective: str,
) -> dict:
    banner_id = str(uuid.uuid4())
    client = _client()

    saved_platforms = []
    for platform, img in platform_images:
        filename = f"{platform.filename}_{platform.width}x{platform.height}.png"
        storage_path = f"{banner_id}/{filename}"

        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        buf.seek(0)

        client.storage.from_(_BUCKET).upload(
            storage_path,
            buf.getvalue(),
            {"content-type": "image/png", "upsert": "true"},
        )
        public_url = client.storage.from_(_BUCKET).get_public_url(storage_path)

        saved_platforms.append({
            "platform_name": platform.name,
            "filename": filename,
            "storage_path": storage_path,
            "public_url": public_url,
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
    client.table("banners").insert(entry).execute()
    return entry


def delete_banner(banner_id: str) -> None:
    client = _client()
    banners = load_banners()
    target = next((b for b in banners if b["id"] == banner_id), None)
    if target:
        paths = [
            p["storage_path"]
            for p in target.get("platforms", [])
            if "storage_path" in p
        ]
        if paths:
            client.storage.from_(_BUCKET).remove(paths)
    client.table("banners").delete().eq("id", banner_id).execute()
