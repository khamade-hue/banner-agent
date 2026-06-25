import base64
import io
import os
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont


def generate_image(
    prompt: str,
    quality: str = "high",
    reference_image: Image.Image | None = None,
) -> Image.Image:
    """Generate image with gpt-image-2. Uses edit endpoint when reference_image is provided."""
    client = OpenAI()

    if reference_image is not None:
        try:
            return _edit_with_reference(client, prompt, reference_image)
        except Exception as e:
            raise RuntimeError(f"[gpt-image-2 edit] {e}")

    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            n=1,
        )
        return _decode(response.data[0])
    except Exception as e:
        raise RuntimeError(f"[gpt-image-2] {e}")


def generate_images_batch(
    prompt: str,
    n: int = 1,
    quality: str = "high",
    reference_image: Image.Image | None = None,
) -> list[Image.Image]:
    """Generate n images in a single API call (same prompt). More efficient than n separate calls."""
    client = OpenAI()

    if reference_image is not None:
        try:
            buf = io.BytesIO()
            reference_image.convert("RGBA").save(buf, "PNG")
            buf.seek(0)
            buf.name = "reference.png"
            response = client.images.edit(
                model="gpt-image-2",
                image=buf,
                prompt=(
                    "Using the visual style, color palette, composition, and mood of the reference image "
                    f"as inspiration, create a new professional advertising banner: {prompt}"
                ),
                size="1024x1024",
                n=n,
            )
            return [_decode(d) for d in response.data]
        except Exception as e:
            raise RuntimeError(f"[gpt-image-2 edit batch] {e}")

    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            n=n,
        )
        return [_decode(d) for d in response.data]
    except Exception as e:
        raise RuntimeError(f"[gpt-image-2 batch] {e}")


def _edit_with_reference(client: OpenAI, prompt: str, ref: Image.Image) -> Image.Image:
    buf = io.BytesIO()
    ref.convert("RGBA").save(buf, "PNG")
    buf.seek(0)
    buf.name = "reference.png"

    response = client.images.edit(
        model="gpt-image-2",
        image=buf,
        prompt=(
            "Using the visual style, color palette, composition, and mood of the reference image "
            f"as inspiration, create a new professional advertising banner: {prompt}"
        ),
        size="1024x1024",
        n=1,
    )
    return _decode(response.data[0])


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        # Windows
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/yugothb.ttc",
        "C:/Windows/Fonts/YuGothB.ttc",
        # Linux (Streamlit Cloud after fonts-noto-cjk)
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def add_text_overlay(img: Image.Image, headline: str, subtext: str = "") -> Image.Image:
    """Overlay headline and subtext on a gradient at the bottom of the image."""
    if not headline:
        return img

    w, h = img.size
    # Skip overlay for very thin banners (e.g. 728×90)
    if h < 120:
        return img

    overlay_h = int(h * 0.30)
    headline_size = max(int(h * 0.054), 14)
    subtext_size = max(int(h * 0.032), 11)

    # Gradient overlay
    result = img.copy().convert("RGBA")
    gradient = Image.new("RGBA", (w, overlay_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(overlay_h):
        alpha = int(185 * (y / overlay_h))
        gd.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    result.paste(gradient, (0, h - overlay_h), gradient)
    result = result.convert("RGB")

    draw = ImageDraw.Draw(result)
    headline_font = _load_font(headline_size)
    subtext_font = _load_font(subtext_size)

    text_top = h - overlay_h + int(overlay_h * 0.22)

    draw.text(
        (w // 2, text_top),
        headline,
        font=headline_font,
        fill="white",
        anchor="mt",
        stroke_width=max(1, headline_size // 26),
        stroke_fill=(0, 0, 0),
    )

    if subtext:
        sub_y = text_top + int(headline_size * 1.4)
        draw.text(
            (w // 2, sub_y),
            subtext,
            font=subtext_font,
            fill=(220, 220, 220),
            anchor="mt",
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )

    return result


def _decode(data) -> Image.Image:
    if getattr(data, "b64_json", None):
        return Image.open(io.BytesIO(base64.b64decode(data.b64_json))).convert("RGB")
    import urllib.request
    with urllib.request.urlopen(data.url) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")
