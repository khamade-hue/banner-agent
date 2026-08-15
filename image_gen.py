import base64
import io
import os
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont


_AD_BANNER_PREFIX = (
    "Professional Japanese SNS advertising banner. "
    "Commercial quality, high-impact marketing creative optimized for social media conversion. "
    "Polished ad design with clear visual hierarchy. "
)


def generate_image(
    prompt: str,
    quality: str = "high",
    reference_image: Image.Image | None = None,
    size: str = "1024x1024",
) -> Image.Image:
    """Generate image with gpt-image-2. Uses edit endpoint when reference_image is provided."""
    client = OpenAI()
    _prompt = _AD_BANNER_PREFIX + prompt

    if reference_image is not None:
        try:
            return _edit_with_reference(client, _prompt, reference_image, size=size)
        except Exception as e:
            raise RuntimeError(f"[gpt-image-2 edit] {e}")

    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=_prompt,
            size=size,
            quality=quality,
            n=1,
        )
        return _decode(response.data[0])
    except Exception as e:
        raise RuntimeError(f"[gpt-image-2] {e}")




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


# (path, ttc_index) pairs — index 2 = Japanese face in CJK TTC files
_FONT_CANDIDATES: dict[str, list[tuple[str, int]]] = {
    # See-through serif: premium headline feel
    "serif-bold": [
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",    2),
        ("/usr/share/fonts/noto-cjk/NotoSerifCJKjp-Bold.otf",       0),
        ("/usr/share/fonts/truetype/noto/NotoSerifCJKjp-Bold.otf",  0),
        # fallback → sans bold
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",     2),
        ("C:/Windows/Fonts/yugothb.ttc",                             0),
        ("C:/Windows/Fonts/YuGothB.ttc",                             0),
        ("C:/Windows/Fonts/meiryo.ttc",                              0),
    ],
    # Regular / Medium weight for body text and badges
    "regular": [
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  2),
        ("/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",0),
        ("/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf",     0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.otf",0),
        ("C:/Windows/Fonts/meiryo.ttc",                              0),
        # fallback → bold
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",     2),
        ("/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",        0),
    ],
    # Standard bold (CTA, badges accent)
    "bold": [
        ("C:/Windows/Fonts/yugothb.ttc",                             0),
        ("C:/Windows/Fonts/YuGothB.ttc",                             0),
        ("C:/Windows/Fonts/meiryo.ttc",                              0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",     2),
        ("/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",        0),
        ("/usr/share/fonts/truetype/noto/NotoSansCJKjp-Bold.otf",   0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",   0),
    ],
}


def _load_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    for path, idx in _FONT_CANDIDATES.get(weight, _FONT_CANDIDATES["bold"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def _draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill,
    tracking: int = 0,
    stroke_width: int = 0,
    stroke_fill=None,
) -> None:
    """Draw text with per-character tracking (letter-spacing). tracking=0 is normal."""
    if tracking == 0:
        draw.text(xy, text, font=font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
        return
    x, y = xy
    _tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for char in text:
        draw.text((x, y), char, font=font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
        try:
            cw = _tmp.textlength(char, font=font)
        except Exception:
            bb = _tmp.textbbox((0, 0), char, font=font)
            cw = bb[2] - bb[0]
        x += cw + tracking


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
    Post-process a gpt-image-2 banner with crisp programmatic elements.

    Design philosophy:
    - Full-bleed photo behind ALL elements (no opaque horizontal bands)
    - Top & bottom vignette gradients for natural depth
    - Serif-bold headline with letter tracking for a refined feel
    - Semi-transparent RTB cards float on the darkened photo
    - Solid accent CTA button at the bottom

    Call AFTER generate_image() and BEFORE smart_crop / resize.
    """
    if not any([headline, cta_text, rtbs]):
        return img

    w, h = img.size
    if h < 150 or w < 200:
        return img

    is_landscape = w > h * 1.1
    is_micro     = h < 320 or w < 320

    primary = _hex_to_rgb(brand_primary_hex)
    accent  = _hex_to_rgb(brand_accent_hex)

    base    = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    mx      = max(24, int(w * 0.060))

    # ── Sizes ────────────────────────────────────────────────────────────
    cta_h     = max(44, int(h * (0.082 if is_micro else 0.062)))
    badge_h   = max(40, int(h * (0.090 if is_micro else 0.058)))
    badge_gap = max(6,  int(h * 0.009))
    badge_fs  = max(12, int(badge_h * 0.40))
    cta_fs    = max(12, int(cta_h   * 0.40))
    hl_fs     = max(28, int(w * (0.040 if is_landscape else 0.056)))
    sub_fs    = max(13, int(w * (0.022 if is_landscape else 0.026)))
    hl_track  = max(1, int(hl_fs * 0.04))  # letter tracking on headline

    # ── Layout (bottom → top) ────────────────────────────────────────────
    cta_mb = max(14, int(h * 0.022))
    cta_y  = h - cta_mb - cta_h

    n_rtbs = 0
    if rtbs and not is_landscape:
        n_rtbs = min(len(rtbs), 3)

    rtb_total = n_rtbs * (badge_h + badge_gap) - (badge_gap if n_rtbs else 0)
    rtb_mb    = max(10, int(h * 0.016)) if n_rtbs else 0
    rtb_y     = cta_y - rtb_mb - rtb_total if n_rtbs else cta_y

    # ── DEPTH: dual vignette (top + bottom gradient on photo) ────────────
    # Top vignette — behind headline
    if headline and not is_micro and not is_landscape:
        hl_pct    = 0.22 if h / w > 1.4 else 0.28
        hl_zone_h = int(h * hl_pct)
        grad_top  = Image.new("RGBA", (w, hl_zone_h), (0, 0, 0, 0))
        gtd       = ImageDraw.Draw(grad_top)
        for yg in range(hl_zone_h):
            # 0→1 curve: strong at very top, smooth fade
            t = yg / hl_zone_h
            a = int(200 * (1.0 - t) ** 1.4)
            gtd.line([(0, yg), (w, yg)], fill=(*primary, a))
        overlay.paste(grad_top, (0, 0), grad_top)
    else:
        hl_zone_h = 0

    # Bottom vignette — behind RTBs and CTA, no hard edge
    bot_grad_h = h - (hl_zone_h if hl_zone_h else int(h * 0.35))
    bot_grad_h = max(bot_grad_h, int(h * 0.42))
    grad_bot   = Image.new("RGBA", (w, bot_grad_h), (0, 0, 0, 0))
    gbd        = ImageDraw.Draw(grad_bot)
    for yg in range(bot_grad_h):
        t = yg / bot_grad_h          # 0 at top of gradient, 1 at bottom
        a = int(195 * t ** 1.6)      # accelerating curve toward bottom
        gbd.line([(0, yg), (w, yg)], fill=(*primary, a))
    overlay.paste(grad_bot, (0, h - bot_grad_h), grad_bot)

    # ── Headline text (serif-bold + tracking) ────────────────────────────
    if hl_zone_h > 0:
        hl_font  = _load_font(hl_fs,  weight="serif-bold")
        sub_font = _load_font(sub_fs, weight="regular")
        mw       = w - mx * 2

        hl_lines  = _wrap_text(headline, hl_font, mw)
        sub_lines = _wrap_text(sub_headline, sub_font, mw) if sub_headline else []

        hl_lh  = int(hl_fs  * 1.25)
        sub_lh = int(sub_fs * 1.35)
        blk_h  = (len(hl_lines) * hl_lh
                  + (int(hl_fs * 0.30) + len(sub_lines) * sub_lh if sub_lines else 0))
        y0 = max(int(hl_zone_h * 0.10), (hl_zone_h - blk_h) // 2)
        y0 = max(y0, int(h * 0.038))

        for line in hl_lines:
            # Soft drop-shadow layer (offset 2,2)
            _draw_tracked_text(
                draw, (mx + 2, y0 + 2), line, hl_font,
                fill=(*primary, 120), tracking=hl_track,
            )
            # Main crisp text
            _draw_tracked_text(
                draw, (mx, y0), line, hl_font,
                fill=(255, 255, 255, 255), tracking=hl_track,
                stroke_width=max(1, hl_fs // 26),
                stroke_fill=(*primary, 180),
            )
            y0 += hl_lh

        if sub_lines:
            y0 += int(hl_fs * 0.28)
            for line in sub_lines:
                draw.text(
                    (mx, y0), line, font=sub_font,
                    fill=(220, 228, 242, 210),
                    stroke_width=1, stroke_fill=(*primary, 100),
                )
                y0 += sub_lh

    # ── RTB badges (semi-transparent, float on vignette) ─────────────────
    if n_rtbs:
        bf    = _load_font(badge_fs, weight="regular")
        bar_w = max(4, int(w * 0.007))

        for i, rtb in enumerate(rtbs[:n_rtbs]):
            by  = rtb_y + i * (badge_h + badge_gap)
            bx1, bx2 = mx, w - mx
            # Card: white at 88% opacity → photo bleeds through subtly
            draw.rounded_rectangle([bx1, by, bx2, by + badge_h],
                                   radius=10, fill=(255, 255, 255, 224))
            draw.rounded_rectangle([bx1, by, bx2, by + badge_h],
                                   radius=10, outline=(*primary, 28), width=1)
            # Left accent bar
            draw.rounded_rectangle([bx1, by, bx1 + bar_w, by + badge_h],
                                   radius=3, fill=(*accent, 255))
            draw.text(
                (bx1 + bar_w + int(w * 0.036), by + badge_h // 2),
                rtb, font=bf, fill=(*primary, 255), anchor="lm",
            )

    # ── CTA button ───────────────────────────────────────────────────────
    if cta_text:
        cx1, cx2 = mx, w - mx
        # Subtle shadow underneath button
        draw.rounded_rectangle(
            [cx1 + 2, cta_y + 3, cx2 + 2, cta_y + cta_h + 3],
            radius=int(cta_h * 0.38), fill=(*primary, 80),
        )
        draw.rounded_rectangle(
            [cx1, cta_y, cx2, cta_y + cta_h],
            radius=int(cta_h * 0.38), fill=(*accent, 255),
        )
        cf = _load_font(cta_fs, weight="bold")
        draw.text(
            (w // 2, cta_y + cta_h // 2), cta_text,
            font=cf, fill=(255, 255, 255, 255), anchor="mm",
        )

    result = Image.alpha_composite(base, overlay)
    return result.convert("RGB")
