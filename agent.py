import json
import re
import anthropic


def _claude() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _parse_json(text: str, is_array: bool = False):
    """Fallback text-based JSON extraction (used only for generate_banner_prompts)."""
    clean = re.sub(r"```(?:json)?\s*|```", "", text).strip()
    pattern = r"\[[\s\S]*\]" if is_array else r"\{[\s\S]*\}"
    match = re.search(pattern, clean)
    if not match:
        raise ValueError(f"Claudeから有効なJSONが返りませんでした:\n{text}")
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"JSONの解析に失敗しました: {e}")


_ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "3C分析と訴求軸の結果を送信する",
    "input_schema": {
        "type": "object",
        "required": ["3c_analysis", "appeal_axes"],
        "properties": {
            "3c_analysis": {
                "type": "object",
                "required": ["customer", "competitor", "company"],
                "properties": {
                    "customer": {
                        "type": "object",
                        "properties": {
                            "needs": {"type": "string"},
                            "pain_points": {"type": "string"},
                            "demographics": {"type": "string"},
                        },
                    },
                    "competitor": {
                        "type": "object",
                        "properties": {
                            "landscape": {"type": "string"},
                            "differentiation": {"type": "string"},
                        },
                    },
                    "company": {
                        "type": "object",
                        "properties": {
                            "strengths": {"type": "string"},
                            "value_proposition": {"type": "string"},
                        },
                    },
                },
            },
            "appeal_axes": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["axis", "description", "target_segment", "rationale"],
                    "properties": {
                        "axis": {"type": "string"},
                        "description": {"type": "string"},
                        "target_segment": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            },
        },
    },
}

_AXES_TOOL = {
    "name": "submit_axes",
    "description": "追加の訴求軸を送信する",
    "input_schema": {
        "type": "object",
        "required": ["axes"],
        "properties": {
            "axes": {
                "type": "array",
                "minItems": 2,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["axis", "description", "target_segment", "rationale"],
                    "properties": {
                        "axis": {"type": "string"},
                        "description": {"type": "string"},
                        "target_segment": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            }
        },
    },
}


def analyze_product(
    product_name: str,
    product_url: str,
    page_content: str,
    competitor_url: str = "",
    competitor_content: str = "",
) -> dict:
    """3C analysis and appeal axis generation."""
    client = _claude()

    content_section = (
        f"\n自社ページ内容（抜粋）:\n{page_content[:3000]}" if page_content.strip() else ""
    )

    if competitor_url and competitor_content.strip():
        competitor_section = f"""
【競合情報（指定URL）】
競合URL: {competitor_url}
競合ページ内容（抜粋）:
{competitor_content[:2500]}

上記の競合商品を中心に詳細な競合分析を実施し、自社商品が勝てる差別化ポイントを明確にしてください。"""
    else:
        competitor_section = """
【競合情報】
競合URLは指定されていません。あなたの知識をベースに、この商品カテゴリの主要競合（3〜5社）を
特定し、各社の強み・市場ポジション・差別化ポイントを分析してください。
競合landscape フィールドには特定した競合企業名と概要を含めてください。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[_ANALYSIS_TOOL],
        tool_choice={"type": "any"},
        system=(
            "あなたはデジタル広告に精通したシニアマーケティングストラテジストです。"
            "3C分析（顧客・競合・自社）を実施し、効果的な訴求軸を導き出すことを得意としています。"
        ),
        messages=[{
            "role": "user",
            "content": f"""以下の商品について3C分析を実施し、SNS広告の訴求軸を最低3パターン提案してください。

商品名: {product_name}
商品URL: {product_url}{content_section}
{competitor_section}

appeal_axesは最低3つ、最大5つ生成してください。各訴求軸は以下の観点で差別化してください:
- 感情訴求 vs 機能訴求
- ターゲット層の違い
- ベネフィットの切り口の違い""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("分析結果が取得できませんでした")


def generate_more_axes(
    product_name: str, existing_axes: list[dict], additional_angle: str
) -> list[dict]:
    """Generate additional appeal axes from a new angle."""
    client = _claude()

    existing = "\n".join(f"- {a['axis']}: {a['description']}" for a in existing_axes)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        tools=[_AXES_TOOL],
        tool_choice={"type": "any"},
        system="あなたはデジタル広告に精通したシニアマーケティングストラテジストです。",
        messages=[{
            "role": "user",
            "content": f"""商品「{product_name}」について、以下の既存の訴求軸とは異なる新しい訴求軸を2〜3パターン追加提案してください。

既存の訴求軸:
{existing}

追加で検討したい観点: {additional_angle if additional_angle else "既存と差別化された新しい切り口"}
既存と重複しないこと。""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input["axes"]
    raise ValueError("訴求軸が取得できませんでした")


def generate_banner_prompts(
    brand_name: str,
    product: str,
    message: str,
    tonmana: str,
    target_audience: str,
    num_variations: int = 3,
    appeal_axis: dict | None = None,
    product_context: dict | None = None,
    objective: str = "",
) -> list[dict]:
    """Use Claude to craft A/B test image prompts for banner ads."""
    client = _claude()

    ctx = product_context or {}
    axis_section = ""
    if appeal_axis:
        axis_section = f"""
Appeal Axis: {appeal_axis['axis']}
Axis Detail: {appeal_axis['description']}
Target Segment: {appeal_axis.get('target_segment', target_audience)}"""

    product_section = ""
    if ctx:
        product_section = f"""
PRODUCT DETAILS:
- Value Proposition: {ctx.get('value_proposition', '')}
- Key Strengths: {ctx.get('strengths', '')}
- Customer Needs: {ctx.get('customer_needs', '')}
- Customer Pain Points: {ctx.get('pain_points', '')}
- Competitive Differentiation: {ctx.get('differentiation', '')}"""

    objective_section = f"\nCampaign Objective: {objective}" if objective else ""

    variation_labels = [chr(65 + i) for i in range(num_variations)]

    banner_tool = {
        "name": "submit_banner_prompts",
        "description": "Submit A/B test banner ad image prompts with Japanese copy",
        "input_schema": {
            "type": "object",
            "required": ["variations"],
            "properties": {
                "variations": {
                    "type": "array",
                    "minItems": num_variations,
                    "maxItems": num_variations,
                    "items": {
                        "type": "object",
                        "required": ["variation", "label", "prompt", "headline", "subtext", "rationale"],
                        "properties": {
                            "variation": {"type": "string"},
                            "label": {"type": "string"},
                            "prompt": {"type": "string"},
                            "headline": {"type": "string", "description": "キャッチコピー（20文字以内）"},
                            "subtext": {"type": "string", "description": "サブコピー（30文字以内）"},
                            "rationale": {"type": "string"},
                        },
                    },
                }
            },
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        tools=[banner_tool],
        tool_choice={"type": "any"},
        system=(
            "You are a senior advertising creative director specializing in high-converting SNS banner ads. "
            "Your task: craft image prompts that visualize the EMOTIONAL OUTCOME customers experience AFTER using this product — "
            "NOT the product itself, its features, or generic category imagery. "
            "Ask yourself: what does the customer's life, work, or self-image look like after this product transforms them? "
            "Show that transformed moment — achievement, confidence, relief, joy, status, empowerment. "
            "Also generate punchy Japanese copy (キャッチコピー) for each variation."
        ),
        messages=[{
            "role": "user",
            "content": f"""Create {num_variations} visually distinct A/B test banner ad variations (labeled {', '.join(variation_labels)}).

BRAND & PRODUCT:
Brand / Product Name: {brand_name}
Product URL: {appeal_axis.get('product_url', '') if appeal_axis else ''}
{product_section}

CREATIVE STRATEGY:
Key Message: {message}
Tone & Manner: {tonmana}
Target Audience: {target_audience}{axis_section}{objective_section}

For each variation output:

1. image prompt (English):
   - Visualize the EMOTIONAL OUTCOME — the customer's transformed state AFTER using this product
   - Show a person, scene, or atmosphere that embodies the feeling this product delivers
   - Do NOT show the product, equipment, or literal product category
   - Apply Tone & Manner ({tonmana}) to color palette, lighting, and visual style
   - Keep the bottom 25% of the composition relatively simple (solid color, gradient, or uncluttered background) — this area will have text overlaid
   - Variations must differ on at least 2 of: subject, color palette, composition, mood
   - NO text, numbers, or typography anywhere in the image
   - Square format, professional advertising quality

2. headline (Japanese, ≤20 chars): キャッチコピー — punchy, benefit-focused, speaks directly to the target's desire
3. subtext (Japanese, ≤30 chars): サブコピー — brief supporting message that complements the headline""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input["variations"]
    raise ValueError("バナープロンプトが取得できませんでした")


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
