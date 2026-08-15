from dataclasses import dataclass
from PIL import Image
import os


@dataclass
class Platform:
    name: str
    filename: str
    width: int
    height: int
    gen_size: str = "1024x1024"

    @property
    def display_name(self) -> str:
        return f"{self.name}  {self.width}×{self.height}"

    def crop_margins(self) -> tuple[int, int]:
        """Returns (crop_left, crop_top) in original gen_size pixels."""
        gen_w, gen_h = (int(x) for x in self.gen_size.split("x"))
        scale = max(self.width / gen_w, self.height / gen_h)
        crop_left = round(((gen_w * scale - self.width) / 2) / scale)
        crop_top = round(((gen_h * scale - self.height) / 2) / scale)
        return crop_left, crop_top

    def get_canvas_label(self) -> str:
        """Returns actual generation canvas size with crop info for the design brief."""
        gen_w, gen_h = (int(x) for x in self.gen_size.split("x"))
        crop_left, crop_top = self.crop_margins()
        crops = []
        if crop_top > 0:
            crops.append(f"上下各{crop_top}px")
        if crop_left > 0:
            crops.append(f"左右各{crop_left}px")
        if crops:
            crop_desc = "・".join(crops) + f"クロップ後に{self.width}×{self.height}px表示"
        else:
            crop_desc = f"クロップなし・{self.width}×{self.height}px表示"
        return f"{gen_w}×{gen_h}px（{crop_desc}）"


PLATFORMS = [
    Platform("Instagram/TikTok ストーリー・リール", "instagram_story",    1080, 1920, "1024x1536"),
    Platform("Instagram フィード（縦型 4:5）",      "instagram_feed_45",  1080, 1350, "1024x1536"),
    Platform("Instagram フィード（正方形）",         "instagram_square",   1080, 1080, "1024x1024"),
    Platform("X（Twitter）",                        "twitter",            1200,  675, "1536x1024"),
    Platform("Facebook / LINE フィード",             "facebook_line",      1200,  628, "1536x1024"),
    Platform("Google レクタングル（300×250）",       "google_300x250",      300,  250, "1024x1024"),
    Platform("Google ハーフページ（300×600）",       "google_300x600",      300,  600, "1024x1536"),
]


def _smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    top = max(0, top)
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
