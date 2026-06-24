import json
import re
import anthropic


def _claude() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=5)


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


# ── Shared schema for a single appeal axis (used by both tools) ───────────────
_AXIS_ITEM_SCHEMA = {
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
}

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
                "items": _AXIS_ITEM_SCHEMA,
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
                "items": _AXIS_ITEM_SCHEMA,
            }
        },
    },
}

_COPY_INSTRUCTIONS = """
各訴求軸の copy_suggestions を必ず生成してください:
- headlines: その訴求軸に合ったキャッチコピー候補を3つ（各20文字以内、インパクト重視）
- offers: バナーで使えるオファー・CTA候補を2つ（「今なら○○無料」「限定○○」など）
- features: バナーのアイコン行で使える特徴・ベネフィットを4〜6項目（短く簡潔に）"""


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
        max_tokens=8000,
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
{_COPY_INSTRUCTIONS}""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            c3 = inp.get("3c_analysis")
            axes = inp.get("appeal_axes")
            if not isinstance(c3, dict):
                raise ValueError(f"3c_analysis が dict ではありません: {type(c3)} / {inp}")
            if not isinstance(axes, list) or not axes:
                raise ValueError(f"appeal_axes が空または list ではありません: {type(axes)} / {inp}")
            return {"3c_analysis": c3, "appeal_axes": axes}
    raise ValueError("ツール呼び出し結果が取得できませんでした")


def generate_more_axes(
    product_name: str, existing_axes: list[dict], additional_angle: str
) -> list[dict]:
    """Generate additional appeal axes (with copy suggestions) from a new angle."""
    client = _claude()

    existing = "\n".join(f"- {a['axis']}: {a['description']}" for a in existing_axes)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[_AXES_TOOL],
        tool_choice={"type": "tool", "name": "submit_axes"},
        system="あなたはデジタル広告に精通したシニアマーケティングストラテジストです。",
        messages=[{
            "role": "user",
            "content": f"""商品「{product_name}」について、以下の既存の訴求軸とは異なる新しい訴求軸を2〜3パターン追加提案してください。

既存の訴求軸:
{existing}

追加で検討したい観点: {additional_angle if additional_angle else "既存と差別化された新しい切り口"}
既存と重複しないこと。
{_COPY_INSTRUCTIONS}""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            axes = list(block.input.get("axes", []))
            if not axes:
                raise ValueError(f"訴求軸が取得できませんでした。返却データ: {block.input}")
            return axes
    raise ValueError("ツール呼び出し結果が取得できませんでした")


def refine_axis(existing_axis: dict, revision_instructions: str) -> dict:
    """Refine an existing appeal axis based on user revision instructions."""
    client = _claude()

    copy_str = json.dumps(existing_axis.get("copy_suggestions", {}), ensure_ascii=False)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[{
            "name": "submit_refined_axis",
            "description": "改修した訴求軸を送信する",
            "input_schema": _AXIS_ITEM_SCHEMA,
        }],
        tool_choice={"type": "tool", "name": "submit_refined_axis"},
        system="あなたはデジタル広告に精通したシニアマーケティングストラテジストです。",
        messages=[{
            "role": "user",
            "content": (
                f"以下の訴求軸を、改修指示に基づいて磨きこんでください。\n\n"
                f"【既存の訴求軸】\n"
                f"軸名: {existing_axis.get('axis','')}\n"
                f"説明: {existing_axis.get('description','')}\n"
                f"ターゲット: {existing_axis.get('target_segment','')}\n"
                f"根拠: {existing_axis.get('rationale','')}\n"
                f"コピー候補: {copy_str}\n\n"
                f"【改修指示】\n{revision_instructions}\n\n"
                f"改修指示を反映しつつ、マーケティング的に有効な訴求軸に仕上げてください。"
                f"copy_suggestions（headlines 3つ・offers 2つ・features 4〜6項目）を必ず含めてください。"
            ),
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("訴求軸の改修結果が取得できませんでした")


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
                    "items": {
                        "type": "object",
                        "required": ["variation", "label", "prompt", "rationale"],
                        "properties": {
                            "variation": {"type": "string"},
                            "label": {"type": "string"},
                            "prompt": {
                                "type": "string",
                                "description": "Complete production-ready design brief for gpt-image-2 (500-700 words). Must cover: layout zones with exact proportions, visual zone with cinematic photo description, ALL text elements verbatim in Japanese with px size/weight/color/position, accent elements, full hex color palette.",
                            },
                            "rationale": {"type": "string"},
                        },
                    },
                }
            },
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system="""You are a senior SNS banner ad art director. Your job is to write exhaustive, production-ready design briefs that a graphic designer (or gpt-image-2) can execute pixel-perfectly without asking any questions.

Each brief must specify ALL of the following — omitting any item is not acceptable:

## CANVAS
- 1080×1080px square, SNS ad format

## LAYOUT ZONES
Divide the canvas into named zones with exact proportions (e.g. "LEFT PANEL: 48% width, full height"). Each zone must have:
- Exact dimensions as % of canvas
- Background: specific hex color, gradient (hex1 → hex2, direction), or photo
- Any overlays: geometric shapes, color washes, opacity values

## VISUAL ZONE (REQUIRED — every brief must have one)
Describe a cinematic photograph or high-end illustration occupying at least one zone. Specify:
- Subject: who/what is shown (age, appearance, clothing, expression, action)
- Setting: environment details, props, background elements
- Composition: framing, angle, depth of field (e.g. f/1.4 shallow bokeh)
- Lighting: sources, quality, color temperature (e.g. warm amber softbox, cool key light)
- Color grading: tones, LUT style (e.g. cool highlights, desaturated mids, cinematic)
- Mood: the emotional atmosphere the image conveys

## TYPOGRAPHY (every text element)
For each text element, specify ALL of:
- Exact Japanese text verbatim (copy word-for-word from the brief instructions)
- Position: zone name + alignment (e.g. "top-left of LEFT PANEL, 40px from top, 32px from left")
- Font size in px
- Font weight (Thin/Regular/Medium/Bold/Black)
- Font: Noto Sans JP or similar Japanese sans-serif
- Color: hex code
- Letter-spacing, line-height if relevant

## ACCENT ELEMENTS
- Divider lines: thickness in px, color hex, exact position
- Icon badges: style (outline/filled), size, color, label text
- CTA bar: dimensions, gradient, text specs
- Geometric overlays: shape, opacity, color, position

## COLOR PALETTE
List all hex codes used, with role (background / headline / accent / CTA / etc.)

Write at commercial advertising quality. gpt-image-2 renders Japanese text reliably when specified verbatim.""",
        messages=[{
            "role": "user",
            "content": f"""Write {num_variations} distinct banner ad design briefs (labeled {', '.join(variation_labels)}). Each must use a meaningfully different layout concept (e.g. vertical split / diagonal / full-bleed photo with overlay / stacked zones / asymmetric grid).

BRAND: {brand_name}
{product_section}
KEY MESSAGE: {message}
TONE & MANNER: {tonmana}
TARGET AUDIENCE: {target_audience}{axis_section}{objective_section}

COPY TO EMBED VERBATIM IN THE IMAGE:
{headline_section}
{offer_section}
{features_section}

For each variation, deliver a complete brief covering every section listed in your instructions (canvas, layout zones, visual zone, typography for every element, accent elements, color palette). Be specific and exhaustive — this brief goes directly to the image renderer.""",
        }],
    )

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "トークン制限に達しました。バリエーション数を減らして再試行してください。"
        )

    for block in response.content:
        if block.type == "tool_use":
            variations = list(block.input.get("variations", []))
            if not variations:
                raise ValueError(
                    f"Claudeがバリエーションを生成しませんでした (stop_reason={response.stop_reason})"
                )
            return variations
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
