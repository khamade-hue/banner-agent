import base64
import io
import os
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont


def generate_image(
    prompt: str,
    quality: str = "high",
    reference_image: Image.Image | None = None,
    size: str = "1024x1024",
) -> Image.Image:
    """Generate image with gpt-image-2. Uses edit endpoint when reference_image is provided."""
    client = OpenAI()

    if reference_image is not None:
        try:
            return _edit_with_reference(client, prompt, reference_image, size=size)
        except Exception as e:
            raise RuntimeError(f"[gpt-image-2 edit] {e}")

    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size=size,
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


def _edit_with_reference(client: OpenAI, prompt: str, ref: Image.Image, size: str = "1024x1024") -> Image.Image:
    buf = io.BytesIO()
    ref.convert("RGBA").save(buf, "PNG")
    buf.seek(0)
    buf.name = "reference.png"

    response = client.images.edit(
        model="gpt-image-2",
        image=buf,
        prompt=(
            "[Layout reference: use only the structural zone arrangement and compositional rhythm of the "
            "reference image as a template — do NOT copy its colors, imagery, text, or brand. "
            "Apply entirely new visuals and Japanese text content as specified in the brief below.]\n\n"
            + prompt
        ),
        size=size,
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


# ── Programmatic composition ──────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Character-by-character wrap — works for Japanese (no spaces)."""
    _d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    current = ""
    for char in text:
        test = current + char
        try:
            tw = _d.textlength(test, font=font)
        except Exception:
            bb = _d.textbbox((0, 0), test, font=font)
            tw = bb[2] - bb[0]
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines or [text]


def compose_programmatic(
    img: Image.Image,
    headline: str = "",
    sub_headline: str = "",
    cta_text: str = "",
    rtbs: list[str] | None = None,
    brand_primary_hex: str = "#0f172a",
    brand_accent_hex: str = "#2563eb",
) -> Image.Image:
    """
    Post-process a gpt-image-2 banner with crisp programmatic elements:
      - Headline + sub_headline : top zone with dark gradient backing
      - RTB badge rows          : card list just above the CTA
      - CTA button              : bottom zone, rounded rect

    Call AFTER generate_image() and BEFORE smart_crop / resize.
    """
    if not any([headline, cta_text, rtbs]):
        return img

    w, h = img.size
    if h < 150 or w < 200:
        return img

    is_landscape = w > h * 1.1
    is_micro     = h < 320 or w < 320   # e.g. 300×250

    primary = _hex_to_rgb(brand_primary_hex)
    accent  = _hex_to_rgb(brand_accent_hex)

    base    = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    mx      = max(24, int(w * 0.060))   # horizontal margin

    # ── Font sizes (proportional) ─────────────────────────────────────────
    cta_h      = max(44, int(h * (0.082 if is_micro else 0.062)))
    badge_h    = max(40, int(h * (0.090 if is_micro else 0.058)))
    badge_gap  = max(6,  int(h * 0.009))
    badge_fs   = max(12, int(badge_h * 0.40))
    cta_fs     = max(12, int(cta_h   * 0.40))
    hl_fs      = max(28, int(w * (0.040 if is_landscape else 0.054)))
    sub_fs     = max(13, int(w * (0.022 if is_landscape else 0.027)))

    # ── Vertical layout (bottom → top) ───────────────────────────────────
    cta_mb = max(14, int(h * 0.022))
    cta_y  = h - cta_mb - cta_h

    n_rtbs = 0
    if rtbs and not is_landscape:
        n_rtbs = min(len(rtbs), 3)

    rtb_total = n_rtbs * (badge_h + badge_gap) - (badge_gap if n_rtbs else 0)
    rtb_mb    = max(10, int(h * 0.015)) if n_rtbs else 0
    rtb_y     = cta_y - rtb_mb - rtb_total if n_rtbs else cta_y

    # ── Headline zone (portrait only) ────────────────────────────────────
    hl_pct = 0.0
    if headline and not is_micro and not is_landscape:
        hl_pct = 0.20 if h / w > 1.4 else 0.26
    hl_zone_h = int(h * hl_pct)

    if hl_zone_h > 0:
        # Dark gradient: primary color fading downward
        grad = Image.new("RGBA", (w, hl_zone_h), (0, 0, 0, 0))
        gd   = ImageDraw.Draw(grad)
        for yg in range(hl_zone_h):
            alpha = int(178 * max(0.0, 1.0 - yg / hl_zone_h * 1.10))
            gd.line([(0, yg), (w, yg)], fill=(*primary, alpha))
        overlay.paste(grad, (0, 0), grad)

        hl_font  = _load_font(hl_fs)
        sub_font = _load_font(sub_fs)
        mw       = w - mx * 2

        hl_lines  = _wrap_text(headline, hl_font, mw)
        sub_lines = _wrap_text(sub_headline, sub_font, mw) if sub_headline else []

        hl_lh  = int(hl_fs  * 1.28)
        sub_lh = int(sub_fs * 1.30)
        blk_h  = (len(hl_lines) * hl_lh
                  + (int(hl_fs * 0.35) + len(sub_lines) * sub_lh if sub_lines else 0))
        y0 = max(int(hl_zone_h * 0.10), (hl_zone_h - blk_h) // 2)
        y0 = max(y0, int(h * 0.038))

        for line in hl_lines:
            draw.text(
                (mx, y0), line, font=hl_font,
                fill=(255, 255, 255, 255),
                stroke_width=max(1, hl_fs // 22),
                stroke_fill=(*primary, 200),
            )
            y0 += hl_lh

        if sub_lines:
            y0 += int(hl_fs * 0.30)
            for line in sub_lines:
                draw.text(
                    (mx, y0), line, font=sub_font,
                    fill=(235, 240, 248, 220),
                    stroke_width=1, stroke_fill=(*primary, 120),
                )
                y0 += sub_lh

    # ── RTB badges ────────────────────────────────────────────────────────
    if n_rtbs:
        panel_top = rtb_y - max(8, int(h * 0.012))
        panel_bot = cta_y - max(6, int(h * 0.010))
        draw.rectangle([0, panel_top, w, panel_bot], fill=(248, 249, 252, 238))

        bf    = _load_font(badge_fs)
        bar_w = max(4, int(w * 0.007))

        for i, rtb in enumerate(rtbs[:n_rtbs]):
            by  = rtb_y + i * (badge_h + badge_gap)
            bx1, bx2 = mx, w - mx
            draw.rounded_rectangle([bx1, by, bx2, by + badge_h],
                                   radius=10, fill=(255, 255, 255, 255))
            draw.rounded_rectangle([bx1, by, bx2, by + badge_h],
                                   radius=10, outline=(*primary, 35), width=1)
            draw.rounded_rectangle([bx1, by, bx1 + bar_w, by + badge_h],
                                   radius=3, fill=(*accent, 255))
            draw.text(
                (bx1 + bar_w + int(w * 0.036), by + badge_h // 2),
                rtb, font=bf, fill=(*primary, 255), anchor="lm",
            )

    # ── CTA button ────────────────────────────────────────────────────────
    if cta_text:
        cx1, cx2 = mx, w - mx
        draw.rounded_rectangle(
            [cx1, cta_y, cx2, cta_y + cta_h],
            radius=int(cta_h * 0.38),
            fill=(*accent, 255),
        )
        cf = _load_font(cta_fs)
        draw.text(
            (w // 2, cta_y + cta_h // 2), cta_text,
            font=cf, fill=(255, 255, 255, 255), anchor="mm",
        )

    result = Image.alpha_composite(base, overlay)
    return result.convert("RGB")
