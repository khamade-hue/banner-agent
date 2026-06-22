import base64
import io
import time
from openai import OpenAI
from PIL import Image


def generate_image(prompt: str, quality: str = "high", retries: int = 2) -> Image.Image:
    """Generate an image with gpt-image-1 and return as PIL Image."""
    client = OpenAI()
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024",
                quality=quality,
                n=1,
            )
            image_bytes = base64.b64decode(response.data[0].b64_json)
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 5 * (attempt + 1)
                print(f"    リトライ {attempt + 1}/{retries} ({wait}秒後)...")
                time.sleep(wait)

    raise RuntimeError(f"画像生成に失敗しました: {last_error}")
