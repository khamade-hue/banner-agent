import base64
import io
from openai import OpenAI
from PIL import Image


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


def _decode(data) -> Image.Image:
    if getattr(data, "b64_json", None):
        return Image.open(io.BytesIO(base64.b64decode(data.b64_json))).convert("RGB")
    import urllib.request
    with urllib.request.urlopen(data.url) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")
