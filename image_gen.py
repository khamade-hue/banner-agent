import base64
import io
import time
from openai import OpenAI
from PIL import Image

# (model, quality_map, size, needs_response_format)
_MODELS = [
    ("gpt-image-1", {"low": "low", "medium": "medium", "high": "high"}, "1024x1024", False),
    ("dall-e-3",    {"low": "standard", "medium": "standard", "high": "hd"}, "1024x1024", True),
]


def generate_image(prompt: str, quality: str = "high", retries: int = 2) -> Image.Image:
    """Generate an image, trying gpt-image-1 first then falling back to dall-e-3."""
    client = OpenAI()

    for model, quality_map, size, needs_fmt in _MODELS:
        q = quality_map.get(quality, list(quality_map.values())[-1])
        last_error = None

        for attempt in range(retries + 1):
            try:
                kwargs = dict(model=model, prompt=prompt, size=size, quality=q, n=1)
                if needs_fmt:
                    kwargs["response_format"] = "b64_json"

                response = client.images.generate(**kwargs)
                image_bytes = base64.b64decode(response.data[0].b64_json)
                return Image.open(io.BytesIO(image_bytes)).convert("RGB")

            except Exception as e:
                last_error = e
                err = str(e).lower()
                # Permission / model access error → skip to next model immediately
                if any(w in err for w in ("permission", "access", "not have", "model", "unsupported")):
                    break
                if attempt < retries:
                    time.sleep(5 * (attempt + 1))

        # If we broke out due to access error, try next model
        if last_error and any(
            w in str(last_error).lower()
            for w in ("permission", "access", "not have", "model", "unsupported")
        ):
            continue

        if last_error:
            raise RuntimeError(f"画像生成に失敗しました ({model}): {last_error}")

    raise RuntimeError("利用可能な画像生成モデルがありません (gpt-image-1 / dall-e-3)")
