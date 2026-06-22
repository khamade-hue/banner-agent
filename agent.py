import json
import re
import anthropic


def _claude() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def analyze_product(product_name: str, product_url: str, page_content: str) -> dict:
    """3C analysis and appeal axis generation."""
    client = _claude()

    content_section = (
        f"\nページ内容（抜粋）:\n{page_content[:4000]}" if page_content.strip() else ""
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=(
            "あなたはデジタル広告に精通したシニアマーケティングストラテジストです。"
            "3C分析（顧客・競合・自社）を実施し、効果的な訴求軸を導き出すことを得意としています。"
            "出力はJSON形式のみで行ってください。マークダウンのコードブロックは使用しないでください。"
        ),
        messages=[{
            "role": "user",
            "content": f"""以下の商品について3C分析を実施し、SNS広告の訴求軸を最低3パターン提案してください。

商品名: {product_name}
商品URL: {product_url}{content_section}

以下のJSON形式で出力してください:
{{
  "3c_analysis": {{
    "customer": {{
      "needs": "顧客のニーズ・欲求",
      "pain_points": "顧客の課題・悩み",
      "demographics": "ターゲット属性"
    }},
    "competitor": {{
      "landscape": "競合状況の概観",
      "differentiation": "差別化ポイント"
    }},
    "company": {{
      "strengths": "自社・商品の強み",
      "value_proposition": "提供価値"
    }}
  }},
  "appeal_axes": [
    {{
      "axis": "訴求軸のタイトル（10文字以内）",
      "description": "この訴求軸の詳細説明",
      "target_segment": "最適なターゲットセグメント",
      "rationale": "この軸が効果的な理由"
    }}
  ]
}}

appeal_axesは最低3つ、最大5つ生成してください。各訴求軸は以下の観点で差別化してください:
- 感情訴求 vs 機能訴求
- ターゲット層の違い
- ベネフィットの切り口の違い""",
        }],
    )

    text = response.content[0].text
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"Claudeから有効なJSONが返りませんでした:\n{text}")
    return json.loads(match.group())


def generate_more_axes(
    product_name: str, existing_axes: list[dict], additional_angle: str
) -> list[dict]:
    """Generate additional appeal axes from a new angle."""
    client = _claude()

    existing = "\n".join(f"- {a['axis']}: {a['description']}" for a in existing_axes)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=(
            "あなたはデジタル広告に精通したシニアマーケティングストラテジストです。"
            "出力はJSON配列のみで行ってください。マークダウンのコードブロックは使用しないでください。"
        ),
        messages=[{
            "role": "user",
            "content": f"""商品「{product_name}」について、以下の既存の訴求軸とは異なる新しい訴求軸を2〜3パターン追加提案してください。

既存の訴求軸:
{existing}

追加で検討したい観点: {additional_angle if additional_angle else "既存と差別化された新しい切り口"}

以下のJSON配列で出力してください（既存と重複しないこと）:
[
  {{
    "axis": "訴求軸のタイトル（10文字以内）",
    "description": "この訴求軸の詳細説明",
    "target_segment": "最適なターゲットセグメント",
    "rationale": "この軸が効果的な理由"
  }}
]""",
        }],
    )

    text = response.content[0].text
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError(f"Claudeから有効なJSONが返りませんでした:\n{text}")
    return json.loads(match.group())


def generate_banner_prompts(
    brand_name: str,
    product: str,
    message: str,
    style: str,
    target_audience: str,
    num_variations: int = 3,
    appeal_axis: dict | None = None,
) -> list[dict]:
    """Use Claude to craft A/B test image prompts for banner ads."""
    client = _claude()

    axis_section = ""
    if appeal_axis:
        axis_section = f"""
Appeal Axis: {appeal_axis['axis']}
Axis Detail: {appeal_axis['description']}
Target Segment: {appeal_axis.get('target_segment', target_audience)}"""

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
Target Audience: {target_audience}{axis_section}

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


def refine_banner_prompt(original_prompt: str, revision_instructions: str) -> str:
    """Refine a banner image prompt based on user revision instructions."""
    client = _claude()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=(
            "You are a senior advertising creative director. "
            "Refine image generation prompts based on revision instructions. "
            "Output ONLY the refined English prompt — no explanation, no labels."
        ),
        messages=[{
            "role": "user",
            "content": f"""Refine the following banner image prompt based on the revision instructions.

Original prompt:
{original_prompt}

Revision instructions (in Japanese):
{revision_instructions}

Output only the refined English prompt for gpt-image-1. Maintain professional advertising quality. NO text or typography in the image.""",
        }],
    )

    return response.content[0].text.strip()
