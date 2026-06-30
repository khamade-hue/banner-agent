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
            "description": "3パターンのコピーセット（各セットはメインキャッチ・サブキャッチ・特徴・CTA）",
            "items": {
                "type": "object",
                "required": ["headline", "sub_headline", "features", "offer"],
                "properties": {
                    "headline": {
                        "type": "string",
                        "description": "メインキャッチコピー（20文字以内、強いインパクト）",
                    },
                    "sub_headline": {
                        "type": "string",
                        "description": (
                            "サブキャッチコピー（30文字以内）。"
                            "メインキャッチを補足する一文。ターゲットの状況・サービスカテゴリ・独自価値を端的に表現。"
                            "headline・features・offerと内容が重複しないこと。"
                        ),
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "バナーのチップ形式で並列表示する特徴・ベネフィット 4〜6項目（1項目10〜20文字）。"
                            "他の2セットのfeaturesと切り口・内容が重複しないこと。"
                            "3セット合計で価格・品質・速度・サポート・実績・利便性など多面的な強みを網羅すること。"
                        ),
                    },
                    "offer": {
                        "type": "string",
                        "description": (
                            "CTA文言（例: 今すぐ資料を請求する / まず実績を確認する / 無料で相談する）。"
                            "商品情報に明記されていない割引・限定・無料体験・具体的数値は絶対に含めないこと。"
                        ),
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
- headline: メインキャッチコピー1本（20文字以内、強いインパクト）
- sub_headline: サブキャッチコピー1本（30文字以内、メインキャッチを補足する一文。
  ターゲットの状況・サービスカテゴリ・独自価値を端的に。headline・features・offerと重複しないこと）
- features: バナーのチップ形式で並列表示する特徴・ベネフィット 4〜6項目（1項目10〜20文字）
- offer: CTA文言1本（行動を促す動詞ベースの表現。具体的な割引率・限定期間・無料体験期間などは
  商品情報に明記されている場合のみ使用すること）

【絶対に守るルール】
■ 事実根拠ルール（最優先）
  提供された商品情報・LPに明記されていない以下の情報はコピーに含めないこと:
  - 割引率・金額（例: 30%オフ、5万円引き）
  - 限定オファー（例: 初回限定、今月限定、先着○名）
  - 試用期間・無料体験（例: 30日間無料、1ヶ月トライアル）
  - 導入社数・実績数値（例: 累計1000社、満足度98%）
  - その他、商品情報から確認できない具体的な数値・期間・特典

■ 商品理解ルール
  headline + features の組み合わせで、その商品を知らない人が読んでも
  「何のサービスか・誰向けか・何が得られるか」を理解できること。
  サービスカテゴリや主要な機能・価値を必ず特徴に含めること。

■ 特徴事実根拠ルール（最重要）
  featuresの各項目は、商品情報・LPに記載された事実・スペック・サービス内容のみを根拠とすること。
  商品情報を精読し、以下の項目が明記されていれば積極的に特徴として活用すること:
  - 納期・制作スピード（例: 最短即日、最短3営業日など）
  - 修正対応（例: 修正回数無制限、初稿3日以内など）
  - 対応コンテンツ・用途（例: SNS広告・採用動画・ブランディング動画）
  - 制作体制（例: 専任ディレクター制、プロクリエイターチームなど）
  - 料金体系（例: 追加費用なし・明確な料金表など）
  商品情報に記載のない機能・サービス内容を「〜できる」「〜対応」として含めること禁止。
  【NG例】「予算に合わせてプラン選択できる」← プラン選択の記載がない場合は不可
  【NG例】「最短即日納品」← 納期の記載がない場合は不可（記載があれば積極的に使うこと）

■ 特徴差別化ルール（重要）
  3セットのfeaturesは互いに重複させず、合計したときに製品の多面的な強みを網羅すること。
  各セットで取り上げる「切り口」を意図的に分散させること:
  - セット1: headlineの訴求軸に最も直結する強みで固める
  - セット2: 品質・実績・信頼性の側面から別の強みを挙げる
  - セット3: 利便性・サポート・プロセス・柔軟性の側面から挙げる
  ※上記は例示。訴求軸の性質に応じて最適な3分類を設計すること。
  【禁止】同じ事実を言い換えただけの特徴を3セットに並べること
  【禁止】価格・数字を含む特徴をセット1・2・3の全てに入れること（1セットに1項目まで）
  各セットのfeaturesはそのセットのheadlineのトーン・切り口と整合させること。

■ ヘッドライン心理起点ルール
  3セットのうち少なくとも1本は、ターゲットの「今の状況・感情・悩み」を起点にした表現にすること。
  NG（ベネフィット起点のみ）: 「高品質×低コストを両立。」
  OK（状況・悩み起点）: 「その見積もり、高すぎませんか？」「社内に動画ノウハウ、ありますか？」
  読んだ瞬間に「自分のことだ」と感じさせる共感型コピーを1本以上含めること。

■ CTAバリエーションルール
  3セットのofferは必ず異なるアクション動詞・異なる意思決定段階を使うこと。
  段階の目安:
  - 情報収集段階: 「〜を知る」「実績をチェックする」「サービスを見てみる」
  - 比較検討段階: 「料金・事例を確認する」「他社と比べてみる」「詳細を見る」
  - 意思決定段階: 「まず相談する」「1本依頼してみる」「今すぐ問い合わせる」
  同一軸の3セット内で同じ動詞を繰り返さないこと（例: 3セット全部「〜を確認する」はNG）。
  各訴求軸のターゲット層がどのファネル段階にいるかを考慮してCTAの重心を決めること。

3セットはクリエイティブコンセプト（例: 感情訴求 / 機能訴求 / 社会的証明）を
それぞれ変えて作成し、多様なバナー表現を可能にしてください。"""


def analyze_product(
    product_name: str,
    product_url: str,
    page_content: str,
    competitor_url: str = "",
    competitor_content: str = "",
    free_comment: str = "",
) -> dict:
    """3C analysis and appeal axis generation."""
    client = _claude()

    content_section = (
        f"\n自社ページ内容（抜粋）:\n{page_content[:3000]}" if page_content.strip() else ""
    )

    free_comment_section = (
        f"\n\n【クライアントからの追加指示・優先事項】\n"
        f"※ 以下の指示を最優先で訴求軸・コピーに反映してください:\n{free_comment.strip()}"
        if free_comment.strip() else ""
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
{competitor_section}{free_comment_section}

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
    product_name: str,
    existing_axes: list[dict],
    additional_angle: str,
    analysis_result: dict | None = None,
) -> list[dict]:
    """Generate additional appeal axes (with copy suggestions) from a new angle."""
    client = _claude()

    existing = "\n".join(f"- {a['axis']}: {a['description']}" for a in existing_axes)

    c3_section = ""
    if analysis_result:
        cust = analysis_result.get("customer", {})
        comp = analysis_result.get("competitor", {})
        co   = analysis_result.get("company", {})
        c3_section = f"""
【3C分析サマリー（この分析と整合する訴求軸を生成すること）】
■ 顧客
  ニーズ: {cust.get("needs", "")}
  課題・ペイン: {cust.get("pain_points", "")}
  属性: {cust.get("demographics", "")}
■ 競合
  競合状況: {comp.get("landscape", "")}
  差別化ポイント: {comp.get("differentiation", "")}
■ 自社
  強み: {co.get("strengths", "")}
  提供価値: {co.get("value_proposition", "")}
上記の3C分析を根拠に、既存軸がカバーしていない顧客ニーズ・切り口を選んで新軸を設計してください。
"""

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
{c3_section}
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
    "headlines":     "メインキャッチコピー（20文字以内×3つ）",
    "sub_headlines": "サブキャッチコピー（30文字以内×3つ）",
    "features":      "特徴・アイコン（4〜6項目、短く簡潔に）",
    "offers":        "CTA文言（3つ）",
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
    sub_headline_copy: str = "",
    offer_copy: str = "",
    features: list[str] | None = None,
    use_product_image: bool = True,
    use_product_logo: bool = False,
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
        lp_colors_line = ""
        if ctx.get("lp_colors"):
            lp_colors_line = f"\n- LP Brand Colors: {' / '.join(ctx['lp_colors'])} ← USE THESE as the base palette"
        product_section = f"""
BRAND/SERVICE DETAILS:
- Value Proposition: {ctx.get('value_proposition', '')}
- Key Strengths: {ctx.get('strengths', '')}
- Customer Needs: {ctx.get('customer_needs', '')}
- Pain Points Solved: {ctx.get('pain_points', '')}
- vs Competitors: {ctx.get('differentiation', '')}{lp_colors_line}"""

    objective_section = f"\nCampaign Objective: {objective}" if objective else ""

    headline_section = f"Main Headline: {headline_copy}" if headline_copy else "Main Headline: (generate a compelling Japanese headline)"
    sub_headline_section = (
        f"Sub-copy — REQUIRED, embed this exact text verbatim "
        f"(split into lines of ≤18 chars if needed, do NOT shorten or rewrite): 「{sub_headline_copy}」"
    ) if sub_headline_copy else ""
    offer_section = f"Offer/CTA: {offer_copy}" if offer_copy else ""
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
            "• PRODUCT LOGO: Include a small product/brand logo mark in the text panel — "
            "position it in the upper-left corner of the text zone or directly below the CTA bar. "
            "Render as a clean, simplified logotype or icon mark in white or the brand accent color. "
            "Size: 32–48px height, with 16px clearance from panel edges. "
            "Do NOT add a background box or border behind the logo."
        )
    else:
        _vc.append("• PRODUCT LOGO: Do NOT include any logo mark or logotype element in the design.")
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
        max_tokens=16000,
        tools=[banner_tool],
        tool_choice={"type": "tool", "name": "submit_banner_prompts"},
        system="""You are a senior SNS banner art director writing design briefs for gpt-image-2.

## NON-NEGOTIABLE RULES (violations cause text distortion and AI artifacts)

### RULE 1 — HIGH-CONTRAST BACKGROUNDS UNDER ALL TEXT
Every Japanese character must maintain WCAG AA contrast (≥4.5:1 against white text).
Text panels MAY use subtle dark-to-dark gradients (e.g., #0F1E35 → #1A3558) provided BOTH gradient stops are dark enough for white text — this adds richness over flat solids.
NEVER place text over photos, bright gradients, light colors, or textures.

### RULE 2 — SHORT TEXT STRINGS
- Headline: split into lines of ≤10 Japanese characters each (2 lines max)
- Sub-copy: ≤18 characters per line (if provided text is longer, wrap into 2 lines — do NOT shorten or omit)
- Feature badges: ≤8 characters each, maximum 4 badges total
- CTA button text: ≤14 characters

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
- Eyebrow label (above headline): 12–14px / Noto Sans JP Medium / accent color / letter-spacing 0.15em — short service category word (e.g. "動画制作" or "VIDEO PRODUCTION"). Placed 12–16px above headline line 1.
- Headline line 1 (category / context): 54–64px / Noto Sans JP Black / white or light color
- Headline line 2 (key proposition — price, benefit, or hook): 72–84px / Noto Sans JP Black / white or accent color — larger than line 1 to emphasize the most impactful phrase
- Sub-copy: 18–22px / Noto Sans JP Bold / line-height 1.5. If sub-copy text is explicitly provided in the COPY section, use it VERBATIM (wrap into ≤18-char lines if needed — never shorten or omit). UNIQUENESS RULE (applies only when sub-copy is NOT provided): sub-copy must state information not already in the headline or badges.
- Badge text: 14–16px / Noto Sans JP Bold
- CTA: 18–22px / Noto Sans JP Black
Headline line 2 ÷ sub-copy size ratio ≥ 3:1.
Per element: verbatim text + position in px from zone edge + font + size + color hex + line-height.
For any numeral in Japanese text: "numeral 'X' rendered in Noto Sans JP [weight] — same typeface as surrounding characters".

## ACCENT ELEMENTS (include in EVERY brief)
Inside the text panel, add BOTH:
1. Thin horizontal rule — 1–2px, accent color at 60% opacity, 60–75% of panel width — placed between headline and badge row
2. Small color bar — 4px × 28–36px, solid accent color — placed as visual anchor immediately above the headline

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
- Eyebrow label added above headline? → short service category, 12–14px, accent color, wide letter-spacing
- Badge text >8 chars? → shorten
- Text panel color = pure black? → replace with deep brand-derived dark
- Accent elements included? → thin rule + small color bar in text panel
- SCENE style chosen? → specify subject gaze/body facing toward the text panel
- Visual approach chosen (SCENE / CUTOUT / FLAT)? → pick what suits the brand best
- Badge style chosen (TEXT-ONLY / ICON+TEXT)? → pick what suits the tone best
- Badges: use RICH ICON BADGE format (rounded-square icon block with gradient ✓ + text label) — not plain text pills or Unicode prefixes
- Sub-copy provided in COPY section? → use it VERBATIM (split into ≤18-char lines). Uniqueness rule applies ONLY when sub-copy is auto-generated (not provided).
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

Output per variation: layout zones (with accent bar) → visual zone (state SCENE/CUTOUT/FLAT choice) → typography with size hierarchy → accent elements → badge row (state TEXT-ONLY/ICON+TEXT choice) → CTA bar → color palette. Under 600 words per brief.""",
        }],
    )

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "トークン制限に達しました。バリエーション数を減らして再試行してください。"
        )

    for block in response.content:
        if block.type == "tool_use":
            raw = block.input.get("variations") or []
            # Claude occasionally returns a dict {0: {...}, 1: {...}} instead of a list
            if isinstance(raw, dict):
                raw = list(raw.values())
            # Keep only dicts; drop strings/nulls that would cause TypeError downstream
            variations = [v for v in raw if isinstance(v, dict)]
            if not variations:
                raise ValueError(
                    f"Claudeがバリエーションを生成しませんでした。再度「バナーを生成」を押してください。"
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
