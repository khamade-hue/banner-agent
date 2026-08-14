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


def generate_copies(
    product_name: str,
    product_info: str,
    objective: str,
) -> list[dict]:
    """Generate 5 copy sets (headline, sub_headline, rtbs×3) for a product."""
    client = _claude()

    tool = {
        "name": "submit_copies",
        "description": "5セットのコピーを送信する",
        "input_schema": {
            "type": "object",
            "required": ["copy_sets"],
            "properties": {
                "copy_sets": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "required": ["headline", "sub_headline", "rtbs"],
                        "properties": {
                            "headline": {
                                "type": "string",
                                "description": "メインコピー（20文字以内、強いインパクト）",
                            },
                            "sub_headline": {
                                "type": "string",
                                "description": "サブコピー（30文字以内、メインコピーを補足する一文）",
                            },
                            "rtbs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 3,
                                "maxItems": 3,
                                "description": "RTB（Reason to Believe）3つ（各10〜20文字）",
                            },
                        },
                    },
                }
            },
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_copies"},
        system=(
            "あなたはデジタル広告に精通したシニアコピーライターです。"
            "商品情報をもとに、バナー広告用のコピーセットを生成します。"
        ),
        messages=[{
            "role": "user",
            "content": f"""以下の商品について、SNS広告バナー用のコピーセットを5パターン生成してください。

商品名: {product_name}
商品情報: {product_info or "（商品情報なし）"}
広告目的: {objective}

各セットの構成:
- headline: メインコピー（20文字以内、強いインパクト）
- sub_headline: サブコピー（30文字以内、メインコピーを補足する一文）
- rtbs: RTB 3本（各10〜20文字、商品の具体的な強みや特徴）

【ルール】
- 5セットはそれぞれ異なる切り口・訴求角度にすること（感情訴求・機能訴求・実績訴求など）
- 商品情報に記載のない事実・数値は含めないこと
- RTBは商品の実際の特徴・強みを具体的に表現すること""",
        }],
    )

    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if hasattr(inp, "model_dump"):
                inp = inp.model_dump()
            elif not isinstance(inp, dict):
                inp = {}
            copy_sets = inp.get("copy_sets", [])
            result = []
            for cs in copy_sets:
                if isinstance(cs, dict):
                    result.append(cs)
                elif hasattr(cs, "model_dump"):
                    result.append(cs.model_dump())
                elif hasattr(cs, "__dict__"):
                    result.append(vars(cs))
            return result
    raise ValueError("コピー生成結果が取得できませんでした")


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
    sub_headline_copy: str = "",
    offer_copy: str = "",
    features: list[str] | None = None,
    use_product_image: bool = True,
    use_product_logo: bool = False,
    use_people: bool = True,
    free_comment: str = "",
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
        lp_colors_line = ""
        if ctx.get("lp_colors"):
            lp_colors_line = f"- LP Brand Colors: {' / '.join(ctx['lp_colors'])} ← USE THESE as the base palette"
        parts = []
        if ctx.get("value_proposition"): parts.append(f"- Value Proposition: {ctx['value_proposition']}")
        if ctx.get("strengths"):         parts.append(f"- Key Strengths: {ctx['strengths']}")
        if ctx.get("customer_needs"):    parts.append(f"- Customer Needs: {ctx['customer_needs']}")
        if ctx.get("pain_points"):       parts.append(f"- Pain Points Solved: {ctx['pain_points']}")
        if ctx.get("differentiation"):   parts.append(f"- vs Competitors: {ctx['differentiation']}")
        if ctx.get("product_info"):      parts.append(f"- Product Details: {ctx['product_info'][:800]}")
        if lp_colors_line:               parts.append(lp_colors_line)
        if parts:
            product_section = "\nBRAND/SERVICE DETAILS:\n" + "\n".join(parts)

    objective_section = f"\nCampaign Objective: {objective}" if objective else ""

    headline_section = f"Main Headline: {headline_copy}" if headline_copy else "Main Headline: (generate a compelling Japanese headline)"
    sub_headline_section = (
        f"Sub-copy — REQUIRED, embed this exact text verbatim "
        f"(split into lines of ≤18 chars if needed, do NOT shorten or rewrite): 「{sub_headline_copy}」"
    ) if sub_headline_copy else ""
    offer_section = (
        f"Offer/CTA — place this ENTIRE text verbatim in the CTA bar only: 「{offer_copy}」"
        f" Do NOT split it — do NOT place any portion of this text outside the CTA bar as a separate element."
    ) if offer_copy else ""
    features_section = ""
    if features:
        features_section = "Feature Badges:\n" + "\n".join(f"• {f}" for f in features)

    _vc: list[str] = []
    if use_product_image:
        _vc.append("• PRODUCT IMAGE: Feature the product as a prominent visual element in every variation.")
    else:
        _vc.append("• PRODUCT IMAGE: Do NOT depict the physical product. Use lifestyle, abstract, or thematic imagery instead.")
    if use_product_logo:
        _vc.append(
            "• PRODUCT LOGO: Include a small product/brand logo mark in the TEXT PANEL ONLY — "
            "position it in the upper-left corner of the text panel (above the headline). "
            "Render as a clean, simplified logotype or icon mark in white or the brand accent color. "
            "Size: 32–48px height, with 16px clearance from panel edges. "
            "Do NOT place the logo in the CTA bar. Do NOT add a background box or border behind the logo."
        )
    else:
        _vc.append("• PRODUCT LOGO: Do NOT include any logo mark or logotype element in the design.")
    if use_people:
        _vc.append("• PEOPLE: Include human models or characters as the main visual subject where appropriate.")
    else:
        _vc.append(
            "• PEOPLE: Do NOT include any people or human figures (no models, faces, hands, silhouettes). "
            "INSTEAD, each variation MUST use a DISTINCTLY DIFFERENT visual concept from the list below — "
            "never use the same concept for two variations. Assign concepts in order (variation A → concept 1, B → concept 2, etc.):\n"
            "  CONCEPT 1 — EDITING SOFTWARE ON SCREEN: laptop or monitor at 15–25° angle displaying a professional "
            "video editing timeline (color-graded footage, audio waveforms, color wheels). "
            "Screen content looks premium. Soft environmental lighting reflects off the bezel. "
            "Background: dark studio blur.\n"
            "  CONCEPT 2 — THUMBNAIL MONTAGE / FILM STRIP: multiple video thumbnails or frames arranged as a "
            "dynamic film-strip or mosaic grid — cinematic landscapes, dramatic scenes, brand-colored frames. "
            "Composition suggests volume and variety of content. "
            "Use perspective/depth so the strip recedes into the background. High visual energy.\n"
            "  CONCEPT 3 — PRODUCTION EQUIPMENT CLOSE-UP: extreme close-up of cinema camera lens, "
            "a lighting rig with practicals glowing, or an audio/video mixing console with illuminated faders. "
            "Dramatic side-lighting, shallow DoF (f/1.4), rich dark tones. "
            "No people — pure equipment as hero subject.\n"
            "  CONCEPT 4 — STUDIO ENVIRONMENT: wide or medium shot of an empty editing suite, "
            "production floor, or green-screen stage. Multiple screens glowing in a dark room, "
            "practical light sources visible, cinematic atmosphere.\n"
            "  If there are more variations than concepts, cycle back. "
            "Do NOT use flat geometric shapes, generic icons, or abstract patterns in any concept. "
            "Always aim for cinematic commercial photography aesthetics."
        )
    visual_constraints_section = "\nVISUAL CONSTRAINTS — must apply to ALL variations:\n" + "\n".join(_vc)

    variation_labels = [chr(65 + i) for i in range(num_variations)]

    # Per-variation visual concept assignment (人物なし・複数バリエーション時)
    _no_people_concepts = [
        "CONCEPT 1 — EDITING SOFTWARE ON SCREEN: laptop or dual monitor at 15–25° angle showing a professional video editing timeline (color-graded footage, audio waveforms, color wheels). Dark studio background, soft bezel reflection. Do NOT use any other concept.",
        "CONCEPT 2 — THUMBNAIL MONTAGE / FILM STRIP: multiple video frames/thumbnails arranged as a dynamic film-strip or mosaic grid receding in perspective. High visual energy, diverse cinematic scenes. No monitors or editing UI. Do NOT use any other concept.",
        "CONCEPT 3 — PRODUCTION EQUIPMENT CLOSE-UP: extreme close-up of cinema camera lens, lighting rig with practicals glowing, or mixing console with illuminated faders. Dramatic side-lighting, shallow DoF f/1.4. No screens or editing software. Do NOT use any other concept.",
        "CONCEPT 4 — STUDIO ENVIRONMENT: empty editing suite or production floor. Multiple screens glowing in a dark room, practical light sources visible. Wide or medium shot. Do NOT use any other concept.",
    ]
    if not use_people and num_variations > 1:
        concept_lines = "\n".join(
            f"  Variation {label}: {_no_people_concepts[i % len(_no_people_concepts)]}"
            for i, label in enumerate(variation_labels)
        )
        variation_concepts_section = (
            f"\nVISUAL CONCEPT ASSIGNMENT (人物なし — mandatory, one concept per variation):\n"
            f"Each variation MUST use ONLY its assigned concept below. "
            f"Using the same concept for two variations is a violation.\n"
            f"{concept_lines}"
        )
    else:
        variation_concepts_section = ""

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
        max_tokens=16000,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system="""You are a senior SNS banner art director writing design briefs for gpt-image-2.

## NON-NEGOTIABLE RULES (violations cause text distortion and AI artifacts)

### RULE 0 — NO EYEBROW / CATEGORY LABEL (HIGHEST PRIORITY — CHECK THIS FIRST)
NEVER write any eyebrow label, service-category text, or descriptor above the headline.
Concretely banned: "VIDEO PRODUCTION", "動画制作", "動画制作サービス", "CORPORATE VIDEO", or any word/phrase that names the service category and sits above or before headline line 1.
The text panel starts with: brand logo → [no text until headline line 1]. Nothing in between.
If you are tempted to add a category label, stop and delete it.

### RULE 1 — HIGH-CONTRAST BACKGROUNDS UNDER ALL TEXT
Every Japanese character must maintain WCAG AA contrast (≥4.5:1 against white text).
Text panels MAY use subtle dark-to-dark gradients (e.g., #0F1E35 → #1A3558) provided BOTH gradient stops are dark enough for white text — this adds richness over flat solids.
NEVER place text over photos, bright gradients, light colors, or textures.

### RULE 2 — SHORT TEXT STRINGS
- Headline: split into lines of ≤10 Japanese characters each (2 lines max)
- Sub-copy: ≤18 characters per line (if provided text is longer, wrap into 2 lines — do NOT shorten or omit)
- Feature badges: ≤8 characters each, maximum 4 badges total
- CTA button text: ≤14 characters preferred; if explicitly provided text is longer, keep it verbatim (max 2 lines inside the CTA bar) — do NOT move part of it outside the bar

### RULE 3 — MINIMAL TEXT ELEMENTS
Maximum: 1 headline (1–2 lines) + 1 sub-line + 1 price/offer + 4 badges + 1 CTA. No decorative text.

### RULE 4 — COMMERCIAL QUALITY VISUALS
PHOTO ZONE: "clean commercial photography, shallow depth of field, white softbox, editorial" — soft natural light, neutral color grading, realistic subjects. NO dramatic lighting, lens flare, oversaturated AI palette.
CUTOUT ZONE (when chosen): isolated subject on pure white (#FFFFFF) with soft drop shadow — no backdrop.
FLAT/ICON ZONE (when chosen): geometric shapes + outlined icons in brand colors — no photography.

### RULE 5 — CLEAN LAYOUT STRUCTURE
2-zone layouts only: VISUAL ZONE + TEXT ZONE (solid color). Optional full-width CTA bar at bottom.
Avoid diagonal cuts, multi-zone complexity, glass morphism, overlapping zones.

### RULE 6 — UNIFORM TYPEFACE (CRITICAL)
ALL characters in the same text element — Japanese + numerals + symbols — MUST use the same Noto Sans JP weight.
NEVER mix Western/serif numerals with Japanese text. Write explicitly: "all characters including numerals/symbols: Noto Sans JP [weight]".

### RULE 7 — NO EYEBROW LABEL (CRITICAL)
Do NOT include any eyebrow label, category label, or service-type text above or below the headline.
BANNED elements: "VIDEO PRODUCTION", "動画制作", "CORPORATE VIDEO", or any short uppercase/category descriptor separate from the main headline.
The banner headline begins directly with Headline line 1 — no preceding text of any kind.

---

## CANVAS
1080×1080px, SNS ad.

## LAYOUT ZONES
Name each zone with exact pixel dimensions and hex background.
TEXT PANEL: Use a rich dark-to-dark gradient derived from the brand palette. Both stops must be dark (luminance <60) so white text stays readable. Examples: "linear-gradient(160deg, #0F1E35 0%, #1A3558 100%)" or "linear-gradient(180deg, #1C1230 0%, #2D1B5E 100%)". NEVER use pure black (#000000) as either stop.
Add a 4–6px vertical accent bar in the brand accent color along the inner edge of the text panel (between panel and visual zone). The accent bar itself MAY use a 2-stop gradient (e.g., accent-color → accent-color-bright) for extra shine.

## VISUAL ZONE
Choose the most appropriate approach — DEFAULT to SCENE unless the brand clearly calls for otherwise:

- SCENE [DEFAULT — use for B2B, production services, consulting, HR, finance, education, and most physical-product brands]: commercial photo — subject + setting + action; 5500K daylight; f/2.8; slightly desaturated. GAZE DIRECTION: subject's eyes and body must face toward the text panel. Specify: "subject facing [left/right] toward text panel, gaze directed inward toward copy zone".
- CUTOUT [use for e-commerce, physical products, food/beverage, consumer apps where showing the product in isolation is the clearest communication]: subject or product isolated on pure white (#FFFFFF), soft drop shadow (0 8px 24px rgba(0,0,0,0.12)), no background.
- FLAT [use ONLY for pure software/SaaS products with no physical form and no relatable human use-case, e.g. a developer API, data pipeline tool, or abstract B2B platform. Do NOT use for: video production, creative agencies, HR, consulting, education, physical products, or any brand where a real person or real product photo would be more convincing.]: flat geometric shapes + brand-colored backgrounds + simple outlined icons (64×64px grid) — no photography.

When in doubt, choose SCENE. A real person or real product is almost always more persuasive than flat illustration.
State which approach you chose and why (one sentence in the rationale field).

## TYPOGRAPHY
Strict hierarchy — for each element specify ALL:
- Eyebrow label / category text: do NOT include anywhere. See RULE 7.
- Headline line 1 (first line of main headline — a phrase from the copy, NOT a category label): 54–64px / Noto Sans JP Black / white or light color
- Headline line 2 (key proposition — price, benefit, or hook): 72–84px / Noto Sans JP Black / white or accent color — larger than line 1 to emphasize the most impactful phrase
- Sub-copy: 18–22px / Noto Sans JP Bold / line-height 1.5. If sub-copy text is explicitly provided in the COPY section, use it VERBATIM (wrap into ≤18-char lines if needed — never shorten or omit). UNIQUENESS RULE (applies only when sub-copy is NOT provided): sub-copy must state information not already in the headline or badges.
- Badge text: 14–16px / Noto Sans JP Bold
- CTA: 18–22px / Noto Sans JP Black
Headline line 2 ÷ sub-copy size ratio ≥ 3:1.
Per element: verbatim text + position in px from zone edge + font + size + color hex + line-height.
For any numeral in Japanese text: "numeral 'X' rendered in Noto Sans JP [weight] — same typeface as surrounding characters".

## ACCENT ELEMENTS (include in EVERY brief)
Inside the text panel, add ONE accent element only:
1. Thin horizontal rule — 1–2px, accent color at 60% opacity, 60–75% of panel width — placed between headline and badge row

Do NOT add any small bar, pip, or color mark above headline line 1. The LAYOUT ZONES vertical accent bar (along the panel/photo border) is the only vertical accent allowed.

## DEPTH & DIMENSIONALITY (mandatory — include ALL of the following in every brief)
Flat 2D results are a failure. Explicitly describe each depth cue below in the brief using image-description language (not CSS).

1. SUBJECT OVERLAP (highest impact — always specify this):
   The photo-zone subject's shoulder, arm, or body edge must cross the boundary between photo zone and text panel by 30–50px, overlapping INTO the text panel. The subject is 100% SOLID and OPAQUE — no transparency, no ghosting, no blending. The depth illusion comes entirely from a hard cast shadow that falls onto the dark text panel surface BEHIND the subject. Write in the brief: "the subject's [body part] extends 30–50px past the zone boundary into the text panel — subject is fully opaque and solid, casting a distinct shadow onto the panel surface beneath them."
   FRAME SAFETY: All body parts (hands, arms, feet) must be FULLY VISIBLE within the image frame — no limbs cropped at the frame edge. Keep at least 30px clearance between any extremity and the frame boundary. The overlap is only at the internal zone boundary, never at the outer frame edge.

2. PHOTO DEPTH:
   Specify VERY SHALLOW depth of field (f/1.4–f/2.0): subject razor-sharp, background melts into smooth circular bokeh. If the composition naturally allows it, consider adding a blurred foreground element (desk edge, plant leaf, glass edge) to create a third depth plane — but only when it enhances the scene. Do not force a foreground element if it would look unnatural or cluttered.

3. BADGE LIFT:
   Each badge floats visibly above the text panel surface — describe "a soft cast shadow falls directly below each badge, suggesting the badge is elevated 4–6px off the panel surface."

4. PANEL LIGHT SOURCE:
   The text panel is lit from the upper-center as if by a recessed ceiling light: the top-center of the panel is slightly lighter, fading to deeper dark at the bottom corners — giving the panel physical curvature and preventing it from looking like a flat painted surface.

5. ZONE EDGE DEPTH:
   At the edge where text panel meets photo zone, the photo zone appears to be set slightly behind the text panel plane — describe "a soft shadow falls from the text panel edge onto the photo zone, as if the text panel is a raised layer in front of the photo."

## BADGE DESIGN
Use RICH ICON BADGES — NOT plain text pills or raw Unicode characters as prefixes.
Each badge is a horizontal unit: [icon block] + [text label]

ICON BLOCK (left side of every badge):
- Shape: rounded square, 22–26px × 22–26px, corner-radius 5–6px
- Border: 1.5px solid, light gray (#D8D8D8) or 15%-tint of the brand accent color
- Background: white (#FFFFFF) or near-white (#F8F8F8)
- Mark inside: a bold checkmark (✓) drawn as a thick-stroke graphic element — NOT a text character. Render the stroke in a 2-stop diagonal gradient: brand accent color (bottom-left) → lighter/brighter variant of the accent or a complementary brand color (top-right). The checkmark should read like a modern app icon.

TEXT LABEL (right side, 8–10px gap from icon block):
- Font: Noto Sans JP Bold, 14–16px
- Color: white or high-contrast light color against the dark text panel

OUTER BADGE CONTAINER (wraps icon block + text label together):
- Background: transparent or ≤8% tint of accent color
- Border: 1px, accent color at 25–35% opacity, corner-radius 6–8px
- Padding: 6–8px vertical, 10–12px horizontal

All badges use the IDENTICAL icon block design — same size, same gradient direction, same border — for visual rhythm.

## CTA BAR
Full-width, height 72–96px. Use a gradient fill (e.g., accent-color → accent-color-bright, left-to-right) for a premium feel. Centered CTA text with full typography spec.
The CTA bar contains the CTA text ONLY — no logo, no sub-text, no icon. Brand logo belongs in the text panel, never in the CTA bar.
If the provided CTA text exceeds 14 characters, render it as-is across 1–2 lines within the bar — do NOT split it into a separate element outside the bar.

## COLOR PALETTE
Base on LP Brand Colors if provided. Stay true to brand — adapt only for contrast/readability.
NEVER use pure #000000 as the text panel color — use a deep brand-derived dark.
List 4–5 hex codes: panel-bg / headline-text / accent / cta-bg / cta-text

Keep each brief under 600 words. Precision over exhaustiveness.""",
        messages=[{
            "role": "user",
            "content": f"""Write {num_variations} SNS banner design briefs (labeled {', '.join(variation_labels)}).
Each must use a DIFFERENT 2-zone layout chosen from: left-text/right-photo | right-text/left-photo | top-text/bottom-photo | bottom-CTA-bar with upper solid text panel.

CHECKLIST before writing each brief:
- Headline >10 chars? → split into 2 lines of ≤10 chars
- Headline line 2 = most impactful phrase (price/hook)? → make it 72–84px, larger than line 1
- Eyebrow label / category text above headline? → do NOT include — omit entirely
- Badge text >8 chars? → shorten
- Text panel color = pure black? → replace with deep brand-derived dark
- Accent elements included? → thin rule + small color bar in text panel
- SCENE style chosen? → specify subject gaze/body facing toward the text panel; subject body/shoulder overlaps zone boundary by 30–50px INTO the text panel (REQUIRED for depth)
- Depth cues included? → subject overlap + badge lift shadows + panel light source + zone edge shadow — ALL 5 mandatory
- Visual approach chosen (SCENE / CUTOUT / FLAT)? → pick what suits the brand best
- Badge style chosen (TEXT-ONLY / ICON+TEXT)? → pick what suits the tone best
- Badges: use RICH ICON BADGE format (rounded-square icon block with gradient ✓ + text label) — not plain text pills or Unicode prefixes
- Sub-copy provided in COPY section? → use it VERBATIM (split into ≤18-char lines). Uniqueness rule applies ONLY when sub-copy is auto-generated (not provided).
- Offer/CTA text provided? → place the COMPLETE string in the CTA bar, every word. Example: if provided text is「キャンペーン実施中！今なら1本無料」the CTA bar must show「キャンペーン実施中！今なら1本無料」in full — do NOT extract「キャンペーン実施中！」as a separate badge, label, or text element outside the bar.
- MIXED-FONT PREVENTION: any numeral/symbol in Japanese? → "Noto Sans JP [weight] — same typeface, no Western numerals"

BRAND: {brand_name}
{product_section}
KEY MESSAGE: {message}
TONE & MANNER: {tonmana}
TARGET AUDIENCE: {target_audience}{axis_section}{objective_section}

COPY — embed verbatim:
{headline_section}
{sub_headline_section}
{offer_section}
{features_section}
{visual_constraints_section}
{variation_concepts_section}

Output per variation: layout zones (with accent bar) → visual zone (state SCENE/CUTOUT/FLAT choice) → typography with size hierarchy → accent elements → badge row (state TEXT-ONLY/ICON+TEXT choice) → CTA bar → color palette. Under 600 words per brief.
{f"ADDITIONAL CREATIVE INSTRUCTIONS: {free_comment.strip()}" if free_comment.strip() else ""}""",
        }],
    )

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "トークン制限に達しました。バリエーション数を減らして再試行してください。"
        )

    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if hasattr(inp, "model_dump"):
                inp = inp.model_dump()
            elif not isinstance(inp, dict):
                inp = {}
            raw = inp.get("variations") or []
            if isinstance(raw, dict):
                raw = list(raw.values())
            variations = []
            for v in raw:
                if isinstance(v, dict):
                    variations.append(v)
                elif hasattr(v, "model_dump"):
                    variations.append(v.model_dump())
                elif hasattr(v, "__dict__"):
                    variations.append(vars(v))
            if not variations:
                raise ValueError(
                    "Claudeがバリエーションを生成しませんでした。再度「バナーを生成」を押してください。"
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

    headlines, sub_headlines, offers, features = [], [], [], []
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
                if any(k in ctx for k in ["sub-copy", "sub_copy", "sub copy", "supporting", "サブ"]):
                    if t not in sub_headlines:
                        sub_headlines.append(t)
                elif any(k in ctx for k in ["headline", "catch", "main text", "primary"]):
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

        # "Sub-copy: テキスト" / "Supporting copy: テキスト"
        m = re.match(
            r"[-•\s]*(?:sub[-\s]?copy|supporting\s+copy|sub[-\s]?headline|sub[-\s]?catch)"
            r"\s*[：:]\s*[「\"""]?(.+?)[」\"""]?\s*(?:[—–(].*)?$",
            s, re.I,
        )
        if m:
            t = m.group(1).strip()
            if _has_jp(t) and t not in sub_headlines:
                sub_headlines.append(t)
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
        if any(k in ctx for k in ["sub-copy", "sub copy", "supporting", "sub_copy"]):
            if q not in sub_headlines:
                sub_headlines.append(q)
        elif any(k in ctx for k in ["headline", "main", "catch", "キャッチ"]):
            if q not in headlines:
                headlines.append(q)
        elif any(k in ctx for k in ["offer", "cta", "button"]):
            if q not in offers:
                offers.append(q)
        elif len(q) <= 25 and q not in features:
            features.append(q)

    return {
        "headlines":     headlines[:3],
        "sub_headlines": sub_headlines[:2],
        "offers":        offers[:2],
        "features":      features[:8],
    }


def _haiku_extract_copy(prompt: str) -> dict:
    tool = {
        "name": "submit_copy",
        "description": "Submit extracted Japanese ad copy from the design brief",
        "input_schema": {
            "type": "object",
            "required": ["headlines", "sub_headlines", "offers", "features"],
            "properties": {
                "headlines": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Primary Japanese headline texts. "
                        "Find after 'Main Headline:', 'Exact text:' near headline sections, "
                        "or quoted Japanese text 「」 near the word headline/catch."
                    ),
                },
                "sub_headlines": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Japanese sub-copy / supporting line texts. "
                        "Find after 'Sub-copy:', 'Supporting copy:', or near the word sub/supporting."
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
            max_tokens=700,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_copy"},
            system=(
                "Extract Japanese advertising copy verbatim from English banner design briefs.\n"
                "- headlines: large primary Japanese text (catch copy / main headline)\n"
                "- sub_headlines: smaller supporting Japanese text below the headline (sub-copy line)\n"
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
                inp = block.input
                inp.setdefault("sub_headlines", [])
                return inp
    except Exception:
        pass
    return {"headlines": [], "sub_headlines": [], "offers": [], "features": []}


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
