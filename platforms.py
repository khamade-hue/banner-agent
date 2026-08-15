from dataclasses import dataclass, field
from PIL import Image
import os


@dataclass
class Platform:
    name: str
    filename: str
    width: int
    height: int
    gen_size: str = "1024x1024"  # gpt-image-2 generation size
    canvas_label: str = ""  # empty = use GEN_SIZE_CANVAS[gen_size]

    @property
    def display_name(self) -> str:
        return f"{self.name}  {self.width}×{self.height}"

    def get_canvas_label(self) -> str:
        return self.canvas_label or GEN_SIZE_CANVAS.get(self.gen_size, self.gen_size)


PLATFORMS = [
    # SNS 縦型
    Platform("Instagram/TikTok ストーリー・リール", "instagram_story",     1080, 1920, "1024x1536"),
    Platform("Instagram フィード（縦型 4:5）",      "instagram_feed_45",   1080, 1350, "1024x1536",
             canvas_label="1080×1350px（縦型フィード・4:5）"),
    # SNS 正方形・横型
    Platform("Instagram フィード（正方形）",         "instagram_square",    1080, 1080, "1024x1024"),
    Platform("X（Twitter）",                        "twitter",             1200,  675, "1536x1024"),
    Platform("Facebook / LINE フィード",             "facebook_line",       1200,  628, "1536x1024"),
    # Google ディスプレイ
    Platform("Google レクタングル（300×250）",       "google_300x250",       300,  250, "1024x1024"),
    Platform("Google ハーフページ（300×600）",       "google_300x600",       300,  600, "1024x1536"),
]

# gpt-image-2生成サイズ → ブリーフ用キャンバス表記（デフォルト）
GEN_SIZE_CANVAS: dict[str, str] = {
    "1024x1024": "1080×1080px（正方形・1:1）",
    "1024x1536": "1080×1920px（縦長・9:16）",
    "1536x1024": "1200×630px（横長・3:2）",
}


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


def resize_for_selected_platforms(
    source: Image.Image, selected: list[Platform]
) -> list[tuple[Platform, Image.Image]]:
    """Return resized PIL images for the given platform subset (no disk I/O)."""
    return [(p, _smart_crop(source, p.width, p.height)) for p in selected]
