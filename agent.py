import json
import re
import anthropic


def generate_banner_prompts(
    brand_name: str,
    product: str,
    message: str,
    style: str,
    target_audience: str,
    num_variations: int = 3,
) -> list[dict]:
    """Use Claude to craft A/B test image prompts for banner ads."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=(
            "You are a senior advertising creative director specializing in digital performance ads. "
            "Generate image prompts for gpt-image-1 that produce high-converting banner creatives. "
            "Output ONLY valid JSON — no markdown fences, no explanation."
        ),
        messages=[{
            "role": "user",
            "content": f"""Create {num_variations} visually distinct A/B test variations for a banner ad campaign.

Brand: {brand_name}
Product / Service: {product}
Key Message: {message}
Visual Style Preference: {style}
Target Audience: {target_audience}

Return a JSON array with exactly {num_variations} objects:
[
  {{
    "variation": "A",
    "label": "Short descriptive label (2-3 words)",
    "prompt": "Highly detailed English prompt for gpt-image-1. NO text or typography in the image. Specify: dominant colors, composition, lighting, visual elements, mood, style. Professional advertising quality. Square format.",
    "rationale": "One sentence: why this creative will resonate with the target audience"
  }}
]

Differentiation rules (each variation must differ on at least 2):
- Color palette (warm vs cool vs neutral vs bold)
- Composition (centered vs rule-of-thirds vs asymmetric)
- Mood (energetic vs calm vs aspirational vs urgent)
- Visual style (photo-realistic vs illustrated vs abstract vs minimalist)""",
        }],
    )

    content = response.content[0].text
    match = re.search(r"\[[\s\S]*\]", content)
    if not match:
        raise ValueError(f"Claudeから有効なJSONが返りませんでした:\n{content}")
    return json.loads(match.group())
