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
                    "required": ["axis", "description", "target_segment", "rationale", "copy_suggestions"],
                    "properties": {
                        "axis": {"type": "string"},
                        "description": {"type": "string"},
                        "target_segment": {"type": "string"},
                        "rationale": {"type": "string"},
                        "copy_suggestions": {
                            "type": "object",
                            "required": ["headlines", "offers", "features"],
                            "properties": {
                                "headlines": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "キャッチコピー候補 3つ（各20文字以内）",
                                },
                                "offers": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "オファー・CTA候補 2つ",
                                },
                                "features": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "バナー用特徴・ベネフィット 4〜6項目",
                                },
                            },
                        },
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
        max_tokens=4096,
        tools=[_ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "submit_analysis"},
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

appeal_axesは必ず3つ以上5つ以内で生成してください。各訴求軸は以下の観点で差別化してください:
- 感情訴求 vs 機能訴求
- ターゲット層の違い
- ベネフィットの切り口の違い

各訴求軸のcopy_suggestionsも必ず生成してください:
- headlines: その訴求軸に合ったキャッチコピー候補を3つ（各20文字以内、インパクト重視）
- offers: バナーで使えるオファー・CTA候補を2つ（「今なら○○無料」「限定○○」など）
- features: バナーのアイコン行で使える特徴・ベネフィットを4〜6項目（短く簡潔に）""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            result = {
                "3c_analysis": dict(block.input.get("3c_analysis", {})),
                "appeal_axes": list(block.input.get("appeal_axes", [])),
            }
            if not result["appeal_axes"]:
                raise ValueError(
                    f"Claudeが訴求軸を生成しませんでした。返却データ: {block.input}"
                )
            return result
    raise ValueError("ツール呼び出し結果が取得できませんでした")


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
        tool_choice={"type": "tool", "name": "submit_axes"},
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
            axes = list(block.input.get("axes", []))
            if not axes:
                raise ValueError(f"訴求軸が取得できませんでした。返却データ: {block.input}")
            return axes
    raise ValueError("ツール呼び出し結果が取得できませんでした")


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
    headline_copy: str = "",
    offer_copy: str = "",
    features: list[str] | None = None,
) -> list[dict]:
    """Use Claude to craft design-brief-style prompts for gpt-image-2 banner generation."""
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
BRAND/SERVICE DETAILS:
- Value Proposition: {ctx.get('value_proposition', '')}
- Key Strengths: {ctx.get('strengths', '')}
- Customer Needs: {ctx.get('customer_needs', '')}
- Pain Points Solved: {ctx.get('pain_points', '')}
- vs Competitors: {ctx.get('differentiation', '')}"""

    objective_section = f"\nCampaign Objective: {objective}" if objective else ""

    headline_section = f"Main Headline: {headline_copy}" if headline_copy else "Main Headline: (generate a compelling Japanese headline)"
    offer_section = f"Offer/CTA: {offer_copy}" if offer_copy else ""
    features_section = ""
    if features:
        features_section = "Feature Badges:\n" + "\n".join(f"• {f}" for f in features)

    variation_labels = [chr(65 + i) for i in range(num_variations)]

    banner_tool = {
        "name": "submit_banner_prompts",
        "description": "Submit design brief prompts for gpt-image-2 banner ad generation",
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
                        "required": ["variation", "label", "prompt", "rationale"],
                        "properties": {
                            "variation": {"type": "string"},
                            "label": {"type": "string"},
                            "prompt": {"type": "string", "description": "Complete design brief in Japanese+English for gpt-image-2, including all text content"},
                            "rationale": {"type": "string"},
                        },
                    },
                }
            },
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system=(
            "You are an expert SNS banner ad art director writing design briefs for gpt-image-2.\n\n"
            "Write comprehensive, specific design briefs that gpt-image-2 executes directly — like briefing a skilled graphic designer.\n\n"
            "Your briefs MUST include:\n"
            "• Layout structure: split panels / diagonal division / layered depth / etc.\n"
            "• VISUAL ZONE (REQUIRED): every brief must have at least one zone with impactful visual imagery — "
            "cinematic photography of a person or scene, lifestyle shot, product/service imagery, abstract graphic art, or UI mockup. "
            "Describe exactly what this visual shows and its photographic style. Do NOT create text-only layouts.\n"
            "• ALL text to render: state exact Japanese text verbatim — gpt-image-2 renders Japanese text reliably when explicitly specified\n"
            "• Typography: font weight, color, size hierarchy, placement for every text element\n"
            "• Color palette: specific colors, gradients, accent usage\n"
            "• Brand placement: brand name/logo position and style\n"
            "• Production quality: real commercial advertising standard\n\n"
            "Do NOT write abstract scene descriptions. Write actionable design briefs with specific visual and textual content.\n"
            "Square 1:1 format (1080×1080px) for SNS ads."
        ),
        messages=[{
            "role": "user",
            "content": f"""Create {num_variations} distinct banner ad design brief variations (labeled {', '.join(variation_labels)}).

BRAND & SERVICE:
Brand Name: {brand_name}
{product_section}

MARKETING CONTEXT:
Key Message: {message}
Tone & Manner: {tonmana}
Target Audience: {target_audience}{axis_section}{objective_section}

COPY TO EMBED IN THE IMAGE:
{headline_section}
{offer_section}
{features_section}

For each variation, write a complete design brief covering:
1. Layout: visual architecture (split panels, diagonal, layered, full-bleed photo + overlay, etc.)
2. Visual zones: specify each zone's content and style in detail
3. Color & atmosphere: exact palette, gradients, lighting treatment
4. Text placement: verbatim Japanese text for every element, with position / size / weight / color
5. Brand element: how the brand name appears
6. Production quality cues: cinematic lighting, studio quality, editorial photography, etc.

Each variation must use a meaningfully different layout concept.
The output prompt will be passed directly to gpt-image-2 — make it exhaustive and specific.""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return list(block.input.get("variations", []))
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
