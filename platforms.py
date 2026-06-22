from dataclasses import dataclass
from PIL import Image
import os


@dataclass
class Platform:
    name: str
    filename: str
    width: int
    height: int


PLATFORMS = [
    Platform("Instagram Square",  "instagram_square",  1080, 1080),
    Platform("Instagram Story",   "instagram_story",   1080, 1920),
    Platform("X (Twitter)",       "twitter",           1200,  675),
    Platform("Facebook",          "facebook",          1200,  628),
    Platform("Google 300x250",    "google_300x250",     300,  250),
    Platform("Google 728x90",     "google_728x90",      728,   90),
    Platform("Google 160x600",    "google_160x600",     160,  600),
]


def _smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def save_all_platforms(source: Image.Image, label: str, output_dir: str) -> list[tuple[str, str]]:
    var_dir = os.path.join(output_dir, label)
    os.makedirs(var_dir, exist_ok=True)
    saved = []
    for p in PLATFORMS:
        cropped = _smart_crop(source, p.width, p.height)
        fname = f"{p.filename}_{p.width}x{p.height}.png"
        fpath = os.path.join(var_dir, fname)
        cropped.save(fpath, "PNG", optimize=True)
        saved.append((p.name, fpath))
    return saved


def resize_for_all_platforms(source: Image.Image) -> list[tuple[Platform, Image.Image]]:
    """Return resized PIL images for all platforms (no disk I/O)."""
    return [(p, _smart_crop(source, p.width, p.height)) for p in PLATFORMS]
