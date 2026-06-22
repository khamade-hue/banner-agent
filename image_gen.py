import base64
import io
import time
from openai import OpenAI
from PIL import Image


def generate_image(prompt: str, quality: str = "high", retries: int = 2) -> Image.Image:
    """Try gpt-image-1 first, fall back to dall-e-3. Raises with full error detail."""
    client = OpenAI()
    errors = []

    # ── gpt-image-1 ──────────────────────────────────────────────────────────
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality=quality,
            n=1,
        )
        return Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json))).convert("RGB")
    except Exception as e:
        errors.append(f"[gpt-image-1] {e}")

    # ── dall-e-3 (fallback) ───────────────────────────────────────────────────
    dall_e_quality = "hd" if quality == "high" else "standard"
    for attempt in range(retries + 1):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality=dall_e_quality,
                n=1,
                response_format="b64_json",
            )
            return Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json))).convert("RGB")
        except Exception as e:
            errors.append(f"[dall-e-3 attempt {attempt + 1}] {e}")
            if attempt < retries:
                time.sleep(5 * (attempt + 1))

    raise RuntimeError("\n".join(errors))
