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
    "required": ["axis", "description", "target_segment", "rationale", "copy_sets"],
    "properties": {
        "axis": {"type": "string"},
        "description": {"type": "string"},
        "target_segment": {"type": "string"},
        "rationale": {"type": "string"},
        "copy_sets": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "description": "3パターンのコピーセット（各セットはキャッチ1本・CTA1本・特徴4〜6項目）",
            "items": {
                "type": "object",
                "required": ["headline", "offer", "features"],
                "properties": {
                    "headline": {
                        "type": "string",
                        "description": "キャッチコピー（20文字以内、強いインパクト）",
                    },
                    "offer": {
                        "type": "string",
                        "description": "オファー・CTA（例: 今なら1件まるごと無料）",
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "バナー用特徴・ベネフィット 4〜6項目（短く簡潔に）",
                    },
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
各訴求軸の copy_sets を必ず3セット生成してください。
プロのコピーライターとしてバナーの完成形をイメージし、
headline・offer・features が1枚のバナー上で統一感を持って機能するよう設計してください。

各セットの構成:
- headline: キャッチコピー1本（20文字以内、強いインパクト）
- offer: オファー・CTA1本（「今なら○○無料」「限定○○」「無料○日トライアル」など）
- features: バナーのアイコン行に使う特徴・ベネフィット 4〜6項目（短く簡潔に）

3セットはクリエイティブコンセプト（例: 感情訴求 / 機能訴求 / 社会的証明）を
それぞれ変えて作成し、多様なバナー表現を可能にしてください。"""


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
            "あなたはデジタル広告に精通したシニアマーケティングストラテジスト兼プロのコピーライターです。"
            "3C分析（顧客・競合・自社）を実施し、バナーの完成形をイメージしながら"
            "訴求軸と刺さるコピーセットを生成することを得意としています。"
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
            c3   = inp.get("3c_analysis")
            axes = inp.get("appeal_axes")
            # Claude occasionally returns nested objects as JSON strings — parse them
            if isinstance(c3, str):
                try:
                    c3 = json.loads(c3)
                except json.JSONDecodeError:
                    pass
            if isinstance(axes, str):
                try:
                    axes = json.loads(axes)
                except json.JSONDecodeError:
                    pass
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
        system=(
            "あなたはデジタル広告に精通したシニアマーケティングストラテジスト兼プロのコピーライターです。"
            "バナーの完成形をイメージしながら、刺さるコピーセットを生成することを得意としています。"
        ),
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


_PART_LABELS = {
    "headlines": "キャッチコピー（20文字以内×3つ）",
    "offers":    "オファー・CTA（2つ）",
    "features":  "特徴・アイコン（4〜6項目、短く簡潔に）",
}


def refine_copy_part(
    axis: dict, part_key: str, target_items: list[str], instructions: str
) -> list[str]:
    """Refine specific items within a copy part, returning the complete updated list."""
    client = _claude()
    part_label = _PART_LABELS.get(part_key, part_key)
    all_items  = axis.get("copy_suggestions", {}).get(part_key, [])
    all_str    = "\n".join(f"・{item}" for item in all_items)
    target_str = "\n".join(f"・{item}" for item in target_items)

    tool = {
        "name": "submit_refined_copy",
        "description": f"改修した{part_label}の完全リストを送信する",
        "input_schema": {
            "type": "object",
            "required": ["items"],
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"改修後の{part_label}完全リスト（改修対象以外は変更しない）",
                }
            },
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_refined_copy"},
        system="あなたはデジタル広告に精通したシニアコピーライターです。",
        messages=[{
            "role": "user",
            "content": (
                f"以下の訴求軸の「{part_label}」から、指定した項目のみを改修してください。\n\n"
                f"【訴求軸】\n"
                f"軸名: {axis.get('axis','')}\n"
                f"説明: {axis.get('description','')}\n"
                f"ターゲット: {axis.get('target_segment','')}\n\n"
                f"【現在の{part_label}（全項目）】\n{all_str}\n\n"
                f"【改修対象（この項目のみ書き直す）】\n{target_str}\n\n"
                f"【改修指示】\n{instructions}\n\n"
                f"改修対象の項目を改修指示に従って書き直し、他の項目は変更せずに、"
                f"全項目を含む完全なリストを返してください。"
            ),
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            return list(block.input.get("items", []))
    raise ValueError("コピー候補の改修結果が取得できませんでした")


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
    use_product_image: bool = True,
    use_people: bool = True,
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

    _vc: list[str] = []
    if use_product_image:
        _vc.append("• PRODUCT IMAGE: Feature the product as a prominent visual element in every variation.")
    else:
        _vc.append("• PRODUCT IMAGE: Do NOT depict the physical product. Use lifestyle, abstract, or thematic imagery instead.")
    if use_people:
        _vc.append("• PEOPLE: Include human models or characters as the main visual subject where appropriate.")
    else:
        _vc.append("• PEOPLE: Do NOT include any people or human figures (no models, faces, hands, silhouettes). Use objects, scenery, or abstract visuals only.")
    visual_constraints_section = "\nVISUAL CONSTRAINTS — must apply to ALL variations:\n" + "\n".join(_vc)

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
        max_tokens=8000,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system="""You are a senior SNS banner art director writing design briefs for gpt-image-2.

## NON-NEGOTIABLE RULES (violations cause text distortion and AI artifacts)

### RULE 1 — SOLID BACKGROUNDS UNDER ALL TEXT
Every Japanese character MUST sit on a flat solid-color panel. NEVER place text over photos, gradients, or textures. A dedicated solid-color zone must exist for all headline, sub-copy, badges, and CTA text.

### RULE 2 — SHORT TEXT STRINGS
- Headline: split into lines of ≤10 Japanese characters each (2 lines max)
- Sub-copy: ≤18 characters per line
- Feature badges: ≤8 characters each, maximum 4 badges total
- CTA button text: ≤14 characters
Shorter strings render crisper. Long strings compress and distort.

### RULE 3 — MINIMAL TEXT ELEMENTS
Maximum elements per banner: 1 headline (1–2 lines) + 1 sub-line + 1 price/offer + 4 badges + 1 CTA.
Fewer elements = sharper output. Do not add decorative text or secondary headlines.

### RULE 4 — COMMERCIAL PHOTO QUALITY (NO AI AESTHETIC)
Photo zone must read like a Getty/Shutterstock editorial image:
- Soft natural light or clean studio light — NO dramatic colored lighting, no lens flare, no HDR
- Neutral or slightly desaturated color grading — NO oversaturated "AI palette"
- Clean, uncluttered setting — NO fantasy/abstract backgrounds
- Subjects: realistic, natural expressions and poses
- Style keyword to include: "clean commercial photography, shallow depth of field, white softbox, editorial"

### RULE 5 — CLEAN LAYOUT STRUCTURE
Use 2-zone layouts only: one PHOTO ZONE + one TEXT ZONE (solid color). Optional CTA bar at bottom.
Avoid: diagonal cuts, complex multi-zone layouts, overlapping zones, glass morphism.

---

## CANVAS
1080×1080px, SNS ad.

## LAYOUT ZONES
Name each zone with exact pixel dimensions and solid hex background.
Example: "LEFT TEXT PANEL: 480×1080px, solid #0A1628" / "RIGHT PHOTO ZONE: 600×1080px"

## VISUAL ZONE
One clean commercial photo in the photo zone:
- Subject, setting, action (concrete and specific)
- Lighting: soft, even, natural — specify color temperature (e.g. 5500K daylight)
- Depth of field: moderate (f/2.8), clean bokeh background
- Color: realistic, slightly desaturated mids

## TYPOGRAPHY
Each text element — specify ALL:
- Exact verbatim Japanese text (must match the copy provided exactly)
- Zone + absolute position in px from zone edges
- Font: Noto Sans JP, size in px, weight (Bold or Black only for headlines)
- Color hex, line-height (1.1–1.3 for headlines)

## CTA BAR
Full-width bar: height in px, solid color hex, centered CTA text with all specs.

## COLOR PALETTE
4–5 hex codes: primary-bg / headline-text / accent / cta-bg / cta-text

Keep each brief under 450 words. Clarity over exhaustiveness.""",
        messages=[{
            "role": "user",
            "content": f"""Write {num_variations} SNS banner design briefs (labeled {', '.join(variation_labels)}).
Each must use a DIFFERENT 2-zone layout concept chosen from: left-text/right-photo | right-text/left-photo | top-text/bottom-photo | bottom-CTA-bar with photo background behind upper solid panel.

IMPORTANT BEFORE WRITING:
- If the headline copy is longer than 10 Japanese characters, split it into 2 lines of ≤10 chars each
- Use maximum 4 feature badges, each ≤8 characters
- All text goes on solid-color panels only

BRAND: {brand_name}
{product_section}
KEY MESSAGE: {message}
TONE & MANNER: {tonmana}
TARGET AUDIENCE: {target_audience}{axis_section}{objective_section}

COPY — embed these verbatim:
{headline_section}
{offer_section}
{features_section}
{visual_constraints_section}

For each variation: layout zones → visual zone → typography (each element) → CTA bar → color palette. Under 450 words per brief.""",
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


_BANNER_PART_DESC = {
    "ビジュアル":     "VISUAL ZONE section (cinematic photo subject, setting, lighting, color grading, mood — everything about the image itself)",
    "トンマナ":       "overall tone and manner — update ALL color-related fields to match the new style: background colors, gradient hex values, accent colors, CTA bar colors, overlay colors, lighting description, color grading style, and overall mood. Keep layout zones and text copy unchanged.",
    "メインキャッチ": "Main Headline text (the large Japanese headline copy shown on the banner)",
    "オファー・CTA":  "Offer/CTA section (the offer text and CTA button/bar design and wording)",
    "特徴・アイコン": "Feature Badges section (the icon bullet point texts and icon styles)",
    "テキスト":       "the specified text element — update ONLY the exact text identified in target_element; keep all other text, layout, colors, and visual elements unchanged.",
}


def refine_banner_part(
    current_prompt: str,
    part_label: str,
    target_element: str | None,
    instructions: str,
) -> str:
    """Revise one specific section of a banner design brief, returning the full updated brief."""
    client = _claude()
    part_desc = _BANNER_PART_DESC.get(part_label, part_label)

    if target_element:
        revision_task = (
            f"Revise ONLY: {part_desc}\n"
            f"Current element to replace: 「{target_element}」\n"
            f"Revision instruction (Japanese): {instructions}"
        )
    else:
        revision_task = (
            f"Revise ONLY: {part_desc}\n"
            f"Revision instruction (Japanese): {instructions}"
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=(
            "You are a senior SNS banner ad art director. "
            "You receive a complete banner design brief and a targeted revision request. "
            "Modify ONLY the specified section as instructed — leave all other sections word-for-word unchanged. "
            "Output ONLY the complete updated design brief. No explanation, no preamble."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"REVISION REQUEST:\n{revision_task}\n\n"
                f"Rules:\n"
                f"- Change only the specified section/element\n"
                f"- All other sections (layout zones, other typography, colors, accents, other copy) must be exactly preserved\n"
                f"- Return the complete brief with the revision applied\n\n"
                f"---\nCURRENT DESIGN BRIEF:\n{current_prompt}"
            ),
        }],
    )
    return response.content[0].text.strip()


def extract_banner_copy(prompt: str) -> dict:
    """Extract Japanese copy elements from a banner design brief.

    Stage 1: regex (instant, no API).
    Stage 2: Haiku fallback if regex finds nothing.
    """
    if not prompt.strip():
        return {"headlines": [], "offers": [], "features": []}

    result = _regex_extract_copy(prompt)
    if any(result[k] for k in result):
        return result
    return _haiku_extract_copy(prompt)


def _has_jp(s: str) -> bool:
    return any("぀" <= c <= "鿿" or "＀" <= c <= "￯" for c in s)


def _regex_extract_copy(prompt: str) -> dict:
    import re

    headlines, offers, features = [], [], []
    lines = prompt.split("\n")
    in_feature = False

    for i, line in enumerate(lines):
        s = line.strip()

        # Track feature-badge section boundaries
        if re.search(r"feature\s+badge|feature\s+icon|icon\s+badge|badge[s]?\s*:", s, re.I):
            in_feature = True
        elif re.match(r"^#{1,3}\s+\S|^[A-Z][A-Z\s]{4,}$|^##", s) and i > 0:
            in_feature = False  # new major section

        # "Exact text: 「テキスト」" — most reliable
        m = re.match(r".*?exact\s+(?:japanese\s+)?text\s*[：:]\s*[「\"""]?(.+?)[」\"""]?\s*$", s, re.I)
        if m:
            t = m.group(1).strip()
            if _has_jp(t):
                ctx = "\n".join(lines[max(0, i - 8):i]).lower()
                if any(k in ctx for k in ["headline", "catch", "main text", "primary"]):
                    if t not in headlines:
                        headlines.append(t)
                elif any(k in ctx for k in ["offer", "cta", "button", "action"]):
                    if t not in offers:
                        offers.append(t)
                elif len(t) <= 30 and t not in features:
                    features.append(t)
            continue

        # "Main Headline: テキスト"
        m = re.match(r"[-•\s]*main\s+headline\s*[：:]\s*[「\"""]?(.+?)[」\"""]?\s*(?:[—–(].*)?$", s, re.I)
        if m:
            t = m.group(1).strip()
            if _has_jp(t) and t not in headlines:
                headlines.append(t)
            continue

        # "Offer/CTA: テキスト" / "CTA: テキスト"
        m = re.match(r"[-•\s]*(?:offer[/／])?cta(?:\s+text|\s+button|\s+copy)?\s*[：:]\s*[「\"""]?(.+?)[」\"""]?\s*(?:[—–(].*)?$", s, re.I)
        if m:
            t = m.group(1).strip()
            if _has_jp(t) and t not in offers:
                offers.append(t)
            continue

        # "Feature Badge: テキスト" / "Feature Badge — テキスト"
        m = re.match(r"[-•\s]*feature\s+badge\s*[：:—–]\s*[「\"""]?(.+?)[」\"""]?\s*$", s, re.I)
        if m:
            t = m.group(1).strip()
            if _has_jp(t) and len(t) <= 30 and t not in features:
                features.append(t)
            continue

        # Bullet points inside feature section
        if in_feature:
            m = re.match(r"^[•・\-\*✓★◆⊕]\s*(.+)", s)
            if m:
                t = re.sub(r"\s*[\(\（（].*", "", m.group(1)).strip()
                t = re.sub(r"\s+(?:icon|badge|symbol|—|–).*$", "", t, flags=re.I).strip()
                if t and _has_jp(t) and len(t) <= 30 and t not in features:
                    features.append(t)

    # Sweep 「」 quoted strings and classify by surrounding context
    for q in re.findall(r"「([^」]{2,40})」", prompt):
        if not _has_jp(q):
            continue
        q = q.strip()
        pos = prompt.find("「" + q + "」")
        if pos == -1:
            continue
        ctx = prompt[max(0, pos - 150):pos].lower()
        if any(k in ctx for k in ["headline", "main", "catch", "キャッチ"]):
            if q not in headlines:
                headlines.append(q)
        elif any(k in ctx for k in ["offer", "cta", "button"]):
            if q not in offers:
                offers.append(q)
        elif len(q) <= 25 and q not in features:
            features.append(q)

    return {
        "headlines": headlines[:3],
        "offers": offers[:2],
        "features": features[:8],
    }


def _haiku_extract_copy(prompt: str) -> dict:
    tool = {
        "name": "submit_copy",
        "description": "Submit extracted Japanese ad copy from the design brief",
        "input_schema": {
            "type": "object",
            "required": ["headlines", "offers", "features"],
            "properties": {
                "headlines": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Primary Japanese headline texts. "
                        "Find after 'Main Headline:', 'Exact text:' near headline sections, "
                        "or quoted Japanese text 「」 near the word headline/catch."
                    ),
                },
                "offers": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Japanese CTA/offer texts on buttons or CTA bars. "
                        "Find after 'Offer/CTA:', 'CTA:', or on CTA button elements."
                    ),
                },
                "features": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Short Japanese feature badge phrases (5–20 chars). "
                        "Find as bullet points in Feature Badges sections. "
                        "Return each badge text separately."
                    ),
                },
            },
        },
    }
    try:
        response = _claude().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_copy"},
            system=(
                "Extract Japanese advertising copy verbatim from English banner design briefs.\n"
                "- headlines: large primary Japanese text (catch copy / main headline)\n"
                "- offers: Japanese text on CTA buttons or offer lines\n"
                "- features: short Japanese badge phrases (typically bullets under Feature Badges)\n"
                "Return ONLY the Japanese text itself, never English descriptions or specs."
            ),
            messages=[{
                "role": "user",
                "content": "Extract Japanese copy from this design brief:\n\n" + prompt[:4000],
            }],
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
    except Exception:
        pass
    return {"headlines": [], "offers": [], "features": []}


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
