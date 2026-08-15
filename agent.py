import json
import re
import anthropic


def _claude() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=5)


def recommend_patterns(
    product_name: str,
    product_info: str,
    objective: str,
    headline: str,
    sub_headline: str,
    available_patterns: list[dict],
    count: int = 2,
) -> list[tuple[str, str]]:
    """Recommend `count` distinct patterns. Returns list of (pattern_name, reason_ja)."""
    tool = {
        "name": "select_patterns",
        "description": f"最適な訴求パターンを{count}種類選択して理由を返す",
        "input_schema": {
            "type": "object",
            "required": ["selections"],
            "properties": {
                "selections": {
                    "type": "array",
                    "minItems": count,
                    "maxItems": count,
                    "description": f"異なる訴求パターンを{count}種類選ぶ。重複禁止。",
                    "items": {
                        "type": "object",
                        "required": ["pattern_name", "reason"],
                        "properties": {
                            "pattern_name": {
                                "type": "string",
                                "enum": [p["name"] for p in available_patterns],
                            },
                            "reason": {"type": "string", "description": "選択理由（1文・日本語）"},
                        },
                    },
                }
            },
        },
    }
    patterns_text = "\n".join(f"- {p['name']}: {p['desc']}" for p in available_patterns)
    response = _claude().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        tools=[tool],
        tool_choice={"type": "tool", "name": "select_patterns"},
        system="あなたはSNS広告のクリエイティブディレクターです。商品・コピー・目的に合わせて、互いに異なるアプローチの訴求パターンを複数選んでください。",
        messages=[{
            "role": "user",
            "content": f"""以下の広告に対して、それぞれ異なるアプローチになる訴求パターンを{count}種類選んでください。
同じパターンを重複して選ばないこと。バリエーション間で訴求の切り口が変わるように選ぶこと。

商品名: {product_name}
商品情報: {product_info[:400] if product_info else "（なし）"}
広告目的: {objective}
メインコピー: {headline}
サブコピー: {sub_headline}

訴求パターン一覧:
{patterns_text}""",
        }],
    )
    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if hasattr(inp, "model_dump"):
                inp = inp.model_dump()
            selections = inp.get("selections", [])
            result, seen = [], set()
            for s in selections:
                if hasattr(s, "model_dump"):
                    s = s.model_dump()
                elif not isinstance(s, dict):
                    continue
                name = s.get("pattern_name", "")
                reason = s.get("reason", "")
                if name and name not in seen:
                    seen.add(name)
                    result.append((name, reason))
            if result:
                return result
    return [(p["name"], "") for p in available_patterns[:count]]


def recommend_pattern(
    product_name: str,
    product_info: str,
    objective: str,
    headline: str,
    sub_headline: str,
    available_patterns: list[dict],
) -> tuple[str, str]:
    """Recommend the best banner pattern. Returns (pattern_name, reason_ja)."""
    tool = {
        "name": "select_pattern",
        "description": "最適な訴求パターンを選択して理由を返す",
        "input_schema": {
            "type": "object",
            "required": ["pattern_name", "reason"],
            "properties": {
                "pattern_name": {
                    "type": "string",
                    "enum": [p["name"] for p in available_patterns],
                    "description": "選択した訴求パターンの名称",
                },
                "reason": {
                    "type": "string",
                    "description": "選択理由（1〜2文、日本語）",
                },
            },
        },
    }
    patterns_text = "\n".join(
        f"- {p['name']}: {p['desc']}" for p in available_patterns
    )
    response = _claude().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        tools=[tool],
        tool_choice={"type": "tool", "name": "select_pattern"},
        system="あなたはSNS広告のクリエイティブディレクターです。商品・コピー・目的に最も適した訴求パターンを選んでください。",
        messages=[{
            "role": "user",
            "content": f"""以下の広告に最適な訴求パターンを1つ選んでください。

商品名: {product_name}
商品情報: {product_info[:400] if product_info else "（なし）"}
広告目的: {objective}
メインコピー: {headline}
サブコピー: {sub_headline}

訴求パターン一覧:
{patterns_text}""",
        }],
    )
    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if hasattr(inp, "model_dump"):
                inp = inp.model_dump()
            return inp.get("pattern_name", available_patterns[0]["name"]), inp.get("reason", "")
    return available_patterns[0]["name"], ""


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
    reference_image_b64: str = "",
    reference_image_mime: str = "image/jpeg",
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
            lp_colors_line = f"- Brand Colors (MANDATORY — apply identically to ALL variations, no per-variation changes): {' / '.join(ctx['lp_colors'])}"
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

    _user_text = f"""以下の情報をもとに、SNSバナー広告のデザインブリーフを{num_variations}パターン（{' / '.join(variation_labels)}）作成してください。

---

【商品・サービス情報】
ブランド名: {brand_name}
{product_section}

【コピー】
メインコピー: {headline_section}
{sub_headline_section}
{offer_section}
{features_section}

【広告目的】{objective_section if objective_section else "（未指定）"}

【訴求パターン】
{tonmana}

【ビジュアル制約】
{visual_constraints_section}
{variation_concepts_section}
{f"【追加要望】{free_comment.strip()}" if free_comment.strip() else ""}

---

各バリエーションを書く前に、まず商品・コピーが伝えたいことの核心を自分の言葉で整理してください。
そのうえで、訴求パターンの構造的本質をどう活かすかを考え、デザインブリーフに落とし込んでください。
バリエーションごとに構図・ビジュアル表現を変えて、それぞれ異なるアプローチにしてください。

【カラー固定ルール】全バリエーション共通のカラーパレットを使用すること。Variation Aで確定したhexコードをB以降も踏襲し、アクセントカラー・CTAバー色・ヘッドライン文字色を変更しないこと。"""

    if reference_image_b64:
        _user_content: str | list = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": reference_image_mime,
                    "data": reference_image_b64,
                },
            },
            {
                "type": "text",
                "text": (
                    "上の画像は選択された訴求パターンの参考例です。"
                    "このパターンが持つ構成の本質（レイアウトの構造・情報の見せ方・視覚的なリズム）を読み取ってください。"
                    "ただし、色・被写体・テキスト内容はそのままコピーせず、下記の商品・コピー情報に合わせて最適化してください。\n\n"
                ) + _user_text,
            },
        ]
    else:
        _user_content = _user_text

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system="""あなたはSNS広告のクリエイティブディレクターです。
商品情報・コピー・訴求パターンをもとに、gpt-image-2で1080×1080pxのSNSバナー画像を生成するためのデザインブリーフを作成します。

## ブリーフを書く前の思考順序

デザインブリーフを書き始める前に、必ず以下の順序で理解を固めてください。

**STEP 1 — 商品・コピーを深く理解する**
- この商品・サービスは誰の何を解決するのか
- ヘッドラインが伝えようとしているメッセージの核心は何か
- サブコピー・RTBはどんな根拠・補強をしているか
- 目的（認知・クリック・CV）は何か

**STEP 2 — 訴求パターンとの接合を考える**
- 選択されたパターンの構造的本質は何か（レイアウト・視覚スタイル・情報の見せ方）
- STEP 1で理解した商品・コピーを、このパターンで表現したとき何が際立つか
- 参照画像は構成の参考として使い、色・被写体・テキストは商品に合わせて最適化する
- パターンが指定する構造から外れた汎用レイアウトに引き戻さないこと

**STEP 3 — デザインブリーフを書く**
STEP 1・2の理解を土台に、gpt-image-2が描ける具体的な画像描写として記述する。

---

## 画像内テキストのルール

AIは長い文字列を正確に描画できません。必ず守ってください。

- ヘッドライン：1行10文字以内・最大2行
- サブコピー：1行18文字以内（長い場合は折り返す。省略・書き換え禁止）
- バッジ・ラベル類：1個8文字以内・最大4個
- CTA：指定テキストを全文そのままCTA領域に配置する（分割・省略禁止）
- ヘッドラインの前後にカテゴリ名・サービス種別テキストを加えない
- 同一テキスト要素内の日本語・数字・記号はすべてNoto Sans JP同一ウェイトで統一する

---

## ビジュアル品質

- 商業広告として成立するリアリティと質感を意識する
- 写真を使う場合：自然光・浅い被写界深度・リアルな被写体・落ち着いた色調
- グラフィック・イラストを使う場合：パターンのスタイルに合った一貫した表現
- 避けること：AIっぽい過飽和カラー・不自然な照明・歪んだ顔・ステレオタイプな演出

---

## テキストの可読性

- テキストと背景のコントラストを十分に確保する（WCAG AA 4.5:1以上を目安に）
- テキストを写真の上に配置する場合は、半透明パネルや影で可読性を担保する

---

## カラー

- 提供されたブランドカラー（プライマリ・アクセント）を必ずベースにパレットを構成する
- Variation Aでカラーパレット（4〜5色・役割ラベル付きhexコード）を確定する
- Variation B以降は同一パレットを踏襲する（アクセントカラーの変更禁止）

---

## バリエーション間の一貫性ルール（CRITICAL）

同じ広告セットの複数バリエーションは「同一ブランドの別クリエイティブ」として扱う。

**全バリエーション共通で固定する要素：**
- カラーパレット全色（プライマリ・アクセント・背景・テキスト色・CTA色すべて）
- CTAバーの色・テキストスタイル・フォントウェイト
- ヘッドラインの文字色
- 訴求パターンが規定するレイアウト基本方向（左右分割ならB以降も左右分割）

**バリエーションごとに変えてよい要素：**
- ビジュアルコンセプト（被写体・構図・照明・雰囲気）のみ

バリエーション間でアクセントカラーが変わっている場合は誤りです。

---

## 出力フォーマット（バリエーションごと）

① レイアウト構造（パターンの構成をどう具体化するか）
② ビジュアル（何を描くか・照明・構図・雰囲気）
③ テキスト配置（各要素のテキスト verbatim・位置・サイズ・色）
④ カラーパレット（hex コード）

1バリエーションあたり400〜500語。具体的かつ簡潔に。""",
        messages=[{"role": "user", "content": _user_content}],
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
