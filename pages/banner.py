"""Page 3: バナー生成・リサイズ"""

import base64
import hashlib
import io
import os
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import extract_banner_copy, generate_banner_prompts, recommend_pattern, recommend_patterns, refine_banner_part
from image_gen import generate_image
from platforms import PLATFORMS, resize_for_selected_platforms
from state import load_banners, load_copies, load_products, save_banner_entry

# ── トンマナ定義（assets/tonmana/ のファイル名が表示名、値がAIプロンプト用説明）────
_TONMANA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tonmana")

_TONMANA_DESC: dict[str, str] = {
    "アニメ風": "anime and illustration style: vibrant clean anime-inspired artwork, expressive characters, manga-influenced typography and dynamic energetic layout",
    "インフルエンサー投稿風": "influencer post style: authentic casual lifestyle photography, warm social media aesthetic, personal and approachable tone, feels organic not staged",
    "オーソドックス": "classic orthodox advertising: clean professional layout, balanced composition, traditional ad structure with headline, visual, and CTA, high trust aesthetic",
    "キャンペーン・セール": "campaign and sale promotional: bold urgent colors (red/yellow/orange), large discount or price callout, high-energy excitement, deadline-driven tone",
    "シンプル❶｜左右分割": "simple left-right split layout: minimalist two-column design, photography on one side and text on the other, clean uncluttered composition",
    "シンプル❷｜上下分割": "simple top-bottom split layout: minimalist two-row design, image panel on top and text panel below, airy and clean presentation",
    "ダイナミックコピー": "dynamic copy-driven: oversized bold typography as the hero element, copy takes visual center stage, minimal imagery, impactful text-forward design",
    "チャット風": "chat and messaging bubble style: speech bubble graphic elements, conversational dialogue format, messaging app aesthetic, informal and friendly tone",
    "テキストのみ": "text-only typographic: pure bold typography with no photography, strong copywriting hierarchy, minimal two-color palette, high-contrast and striking",
    "ニュース風": "news and editorial style: newspaper-inspired layout with column structure, journalistic credibility tone, authoritative factual presentation",
    "ビフォーアフター": "before and after comparison: split-screen transformation reveal, clear visual contrast between problem state and solution state, persuasive side-by-side format",
    "フィルム写真風": "film photography style: analog grain texture, warm vintage color grading, light leaks and soft edges, nostalgic candid authentic aesthetic",
    "マンガ風": "manga and comic style: comic panel layout structure, speech bubbles, bold ink outline illustration, Japanese manga visual language and energy",
    "口コミ・レビュー": "testimonial and review style: user quote design with attribution, star ratings display, social proof emphasis, authentic word-of-mouth format",
    "図解": "infographic and diagram style: explanatory icons, simple charts and flows, structured information hierarchy, visual data storytelling approach",
    "比較・ランキング風": "comparison and ranking style: competitive feature comparison table, vs. format or ranking display, checklist-style advantages, clear winner positioning",
}


# ── カラープリセット（ベース色, アクセント色）─────────────────────────────────
_COLOR_PRESETS: list[tuple[str, str | None, str | None]] = [
    ("ホワイト × ブルー",   "#ffffff", "#2563eb"),
    ("ホワイト × ネイビー", "#ffffff", "#1e3a5f"),
    ("ネイビー × ホワイト", "#0f172a", "#ffffff"),
    ("ネイビー × ゴールド", "#0f172a", "#d97706"),
    ("ホワイト × レッド",   "#ffffff", "#dc2626"),
    ("ブラック × イエロー", "#1c1c1c", "#fbbf24"),
    ("ホワイト × グリーン", "#ffffff", "#16a34a"),
    ("カスタム",             None,      None),
]


@st.cache_data
def _load_tonmana_b64(path: str, max_width: int = 240) -> tuple[str, str]:
    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=75, optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


def _build_tonmana_list() -> list[tuple[str, str]]:
    if not os.path.isdir(_TONMANA_DIR):
        return []
    files = sorted([
        f for f in os.listdir(_TONMANA_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ])
    return [(os.path.splitext(f)[0], os.path.join(_TONMANA_DIR, f)) for f in files]


_TONMANA_LIST = _build_tonmana_list()
_TONMANA_IMG_MAP = {name: path for name, path in _TONMANA_LIST}

_PATTERN_GROUPS = [
    {
        "label": "A｜汎用 / ベーシック",
        "desc": "どんな商品・目的にも使える基本形",
        "patterns": ["オーソドックス", "シンプル❶｜左右分割", "シンプル❷｜上下分割", "ダイナミックコピー"],
    },
    {
        "label": "B｜情報・比較",
        "desc": "理性に訴える、論理的アプローチ",
        "patterns": ["比較・ランキング風", "ビフォーアフター", "図解", "テキストのみ"],
    },
    {
        "label": "C｜共感・信頼",
        "desc": "感情と社会的証明による訴求",
        "patterns": ["口コミ・レビュー", "ニュース風", "インフルエンサー投稿風", "キャンペーン・セール"],
    },
    {
        "label": "D｜個性・スタイル",
        "desc": "特定ターゲット・世界観訴求",
        "patterns": ["フィルム写真風", "チャット風", "アニメ風", "マンガ風"],
    },
]
_TONMANA_NAMES = [p for g in _PATTERN_GROUPS for p in g["patterns"]]

_PATTERN_SHORT_DESC: dict[str, str] = {
    "アニメ風": "アニメ・イラスト調のビジュアルで親しみやすさを演出",
    "インフルエンサー投稿風": "SNS投稿のようなリアル感で自然に訴求",
    "オーソドックス": "王道の広告レイアウトで安定した訴求力",
    "キャンペーン・セール": "セール感・限定感を前面に出した訴求",
    "シンプル❶｜左右分割": "左右で画像とテキストを分けたミニマルな構成",
    "シンプル❷｜上下分割": "上下で画像とテキストを分けたミニマルな構成",
    "ダイナミックコピー": "大きなコピーをメインビジュアルにした文字中心の訴求",
    "チャット風": "会話・メッセージ形式で親近感を演出",
    "テキストのみ": "写真なし、テキストだけで力強く伝える",
    "ニュース風": "ニュース・メディア調で信頼感と情報価値を演出",
    "ビフォーアフター": "Before/After の対比で変化・効果を視覚的に伝える",
    "フィルム写真風": "フィルム感のある温かみあるビジュアルで情緒に訴える",
    "マンガ風": "マンガ・コミック調で個性的に訴求",
    "口コミ・レビュー": "ユーザーの声・レビューを前面に出して信頼を獲得",
    "図解": "図・アイコンで情報をわかりやすく整理して伝える",
    "比較・ランキング風": "競合比較やランキング形式で優位性を示す",
}


_AI_SENTINEL = "__AI_RECOMMEND__"

# 訴求パターン別・人物使用の傾向（AIにおまかせ振り分け用）
_PREFER_PEOPLE_PATTERNS = frozenset({
    "口コミ・レビュー", "インフルエンサー投稿風", "フィルム写真風",
    "チャット風", "アニメ風", "マンガ風", "ビフォーアフター",
})
_PREFER_NO_PEOPLE_PATTERNS = frozenset({
    "図解", "テキストのみ", "比較・ランキング風",
    "ダイナミックコピー", "ニュース風", "キャンペーン・セール",
})


def _assign_people_per_var(
    assignments: list[tuple[str, str]] | None,
    num_variations: int,
) -> list[bool]:
    """AIにおまかせ×複数バリエーション時に人物有無を振り分ける。
    パターンの傾向から True/False を仮置きし、True/False が最低1枠ずつになるよう補正する。"""
    if assignments:
        raw: list[bool | None] = [
            True if p in _PREFER_PEOPLE_PATTERNS
            else False if p in _PREFER_NO_PEOPLE_PATTERNS
            else None
            for p, _ in assignments
        ]
    else:
        raw = [None] * num_variations

    has_true = any(v is True for v in raw)
    has_false = any(v is False for v in raw)
    if not has_true:
        for i in range(len(raw)):
            if raw[i] is None:
                raw[i] = True
                break
        else:
            raw[0] = True
    if not has_false:
        for i in range(len(raw) - 1, -1, -1):
            if raw[i] is None:
                raw[i] = False
                break
        else:
            raw[-1] = False
    last_val = True
    for i in range(len(raw)):
        if raw[i] is None:
            raw[i] = not last_val
        last_val = bool(raw[i])
    return [bool(v) for v in raw]


def _pattern_grid() -> str:
    """訴求パターンをビジュアルグリッドで選択し、選択されたパターン名（またはAI sentinel）を返す。"""
    if not _TONMANA_LIST:
        st.warning("assets/tonmana/ に画像が見つかりません")
        return ""

    if "tonmana_sel_idx" not in st.session_state:
        st.session_state["tonmana_sel_idx"] = 0

    # ── AIにおまかせカード ────────────────────────────────────────────────────
    is_ai = st.session_state["tonmana_sel_idx"] == -1
    ai_border = "border:2px solid #8b5cf6;" if is_ai else "border:1px dashed #334155;"
    ai_bg     = "background:linear-gradient(135deg,rgba(139,92,246,0.15),rgba(99,102,241,0.06));" if is_ai else "background:rgba(255,255,255,0.02);"
    ai_lbl_c  = "#a78bfa" if is_ai else "#cbd5e1"
    ai_row    = st.columns(4)
    with ai_row[0]:
        st.markdown(
            f'<div style="font-size:0.78rem;font-weight:700;color:{ai_lbl_c};margin-bottom:3px">'
            f'{"✓ " if is_ai else ""}✨ AIにおまかせ</div>'
            f'<div style="font-size:0.65rem;color:#64748b;line-height:1.4;min-height:2.8em;margin-bottom:6px">'
            f'目的・コピーを踏まえてAIが最適なパターンを自動選択</div>'
            f'<div style="{ai_bg}{ai_border}border-radius:8px;height:72px;'
            f'display:flex;align-items:center;justify-content:center;margin-bottom:6px">'
            f'<span style="font-size:1.8rem">✨</span></div>',
            unsafe_allow_html=True,
        )
        if is_ai:
            st.markdown(
                '<div style="text-align:center;color:#a78bfa;font-size:0.7rem;'
                'font-weight:700;padding:4px 0 10px">選択中</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button("選択", key="ton_sel_ai", use_container_width=True, type="secondary"):
                st.session_state["tonmana_sel_idx"] = -1
                st.rerun()

    for g_idx, group in enumerate(_PATTERN_GROUPS):
        # グループヘッダー
        mt = "20px" if g_idx > 0 else "12px"
        st.markdown(
            f'<div style="margin:{mt} 0 8px;padding-bottom:6px;'
            f'border-bottom:1px solid #1e293b">'
            f'<span style="font-size:0.7rem;font-weight:700;color:#8b5cf6;'
            f'text-transform:uppercase;letter-spacing:0.08em">{group["label"]}</span>'
            f'<span style="font-size:0.68rem;color:#475569;margin-left:8px">{group["desc"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for c_idx, (col, name) in enumerate(zip(cols, group["patterns"])):
            idx = g_idx * 4 + c_idx
            is_sel = st.session_state["tonmana_sel_idx"] == idx
            img_path = _TONMANA_IMG_MAP.get(name, "")
            short_desc = _PATTERN_SHORT_DESC.get(name, "")
            label_color = "#a78bfa" if is_sel else "#cbd5e1"
            border = "border:2px solid #8b5cf6;" if is_sel else "border:1px solid #1e293b;"
            bg = "background:rgba(139,92,246,0.08);" if is_sel else ""

            # 画像HTML を事前に組み立てる
            if img_path:
                try:
                    b64, mime = _load_tonmana_b64(img_path)
                    img_html = (
                        f'<div style="border-radius:8px;overflow:hidden;{border}{bg}padding:2px;margin-bottom:6px">'
                        f'<img src="data:{mime};base64,{b64}" style="width:100%;display:block;border-radius:6px">'
                        f'</div>'
                    )
                except Exception:
                    img_html = (
                        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;'
                        f'height:60px;display:flex;align-items:center;justify-content:center;'
                        f'color:#475569;font-size:0.65rem;padding:4px;text-align:center;'
                        f'margin-bottom:6px">{name}</div>'
                    )
            else:
                img_html = ""

            with col:
                # 名称・概要・画像を1回のst.markdownにまとめる
                st.markdown(
                    f'<div style="font-size:0.78rem;font-weight:700;color:{label_color};margin-bottom:3px">'
                    f'{"✓ " if is_sel else ""}{name}</div>'
                    f'<div style="font-size:0.65rem;color:#64748b;line-height:1.4;min-height:2.8em;margin-bottom:6px">'
                    f'{short_desc}</div>'
                    f'{img_html}',
                    unsafe_allow_html=True,
                )
                # 選択ボタン
                if is_sel:
                    st.markdown(
                        '<div style="text-align:center;color:#a78bfa;font-size:0.7rem;'
                        'font-weight:700;padding:4px 0 10px">選択中</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button("選択", key=f"ton_sel_{idx}", use_container_width=True, type="secondary"):
                        st.session_state["tonmana_sel_idx"] = idx
                        st.rerun()

    if st.session_state["tonmana_sel_idx"] == -1:
        return _AI_SENTINEL
    return _TONMANA_NAMES[st.session_state["tonmana_sel_idx"]]

# ── CTA リスト（仮）────────────────────────────────────────────────────────────
_CTA_LIST = [
    "今すぐ無料相談",
    "詳しくはこちら",
    "無料で試す",
    "お問い合わせ",
    "資料をダウンロード",
    "3分でわかる",
    "まずは話を聞く",
    "サービスを見る",
]


# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _build_zip(results: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for v, platform_images in results:
            for platform, img in platform_images:
                fname = (
                    f"{v['variation']}_{v['label']}/"
                    f"{platform.filename}_{platform.width}x{platform.height}.png"
                )
                zf.writestr(fname, _img_to_bytes(img))
    return buf.getvalue()


def _section(label: str, margin_top: str = "24px") -> None:
    st.markdown(
        f'<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin:{margin_top} 0 10px">{label}</div>',
        unsafe_allow_html=True,
    )


# ── ヘッダー ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e1b4b 60%,#312e81 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:28px;'
    'border:1px solid rgba(139,92,246,0.3);'
    'box-shadow:0 8px 32px rgba(99,102,241,0.2),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">バナー生成・リサイズ</h1>'
    '<p style="color:#a5b4fc;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    'Claude がデザインブリーフを作成し、gpt-image-2 でバナーを生成します'
    '</p></div>',
    unsafe_allow_html=True,
)

# ── モード切替 ────────────────────────────────────────────────────────────────
_banner_mode = st.radio(
    "",
    ["新規生成", "リサイズ"],
    horizontal=True,
    index=0,
    key="banner_page_mode",
    label_visibility="collapsed",
)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 新規生成
# ══════════════════════════════════════════════════════════════════════════════
if _banner_mode == "新規生成":

    # ── STEP 1 — 商品選択 ──────────────────────────────────────────────────────
    _section("STEP 1 — 商品選択", margin_top="0")
    try:
        products = load_products()
    except Exception as _e:
        st.error(
            "⚠️ **Supabase 接続エラー**\n\n"
            "Supabase プロジェクトが一時停止しているか、Secrets の設定が正しくない可能性があります。\n\n"
            f"エラー詳細: `{_e}`"
        )
        st.stop()

    if not products:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
            'border-radius:12px;padding:40px;text-align:center;color:#64748b">'
            '先に「商品登録・修正」ページで商品を登録してください。</div>',
            unsafe_allow_html=True,
        )
        if st.button("商品登録ページへ →", type="primary"):
            st.switch_page("pages/product.py")
        st.stop()

    selected_product_idx = st.selectbox(
        "商品を選択 *",
        range(len(products)),
        format_func=lambda i: products[i]["product_name"],
        key="banner_prod_sel",
        label_visibility="collapsed",
    )
    selected_product = products[selected_product_idx]

    st.divider()

    # ── STEP 2 — コピー選択 ────────────────────────────────────────────────────
    _section("STEP 2 — コピー選択")

    try:
        copies = load_copies(product_id=selected_product["id"])
    except Exception as _e:
        st.error(f"コピー取得エラー: `{_e}`")
        st.stop()

    selected_copy: dict | None = None
    selected_cta: str = _CTA_LIST[0]

    if not copies:
        st.warning(
            f"「{selected_product['product_name']}」のコピーがまだ登録されていません。"
            "「コピー登録・修正」ページで登録してください。"
        )
    else:
        copy_labels = [
            f"[{c.get('objective', '—')}] {c.get('headline', '')} / {c.get('sub_headline', '')}"
            for c in copies
        ]
        sel_copy_idx = st.selectbox(
            "コピーを選択 *",
            range(len(copies)),
            format_func=lambda i: copy_labels[i],
            key="banner_copy_sel",
            label_visibility="collapsed",
        )
        selected_copy = copies[sel_copy_idx]

        # コピープレビュー
        rtbs = selected_copy.get("rtbs", [])
        rtb_pills = "".join(
            f'<span style="background:rgba(139,92,246,0.15);color:#c4b5fd;'
            f'border:1px solid rgba(139,92,246,0.35);border-radius:12px;'
            f'padding:2px 9px;font-size:0.72rem;margin:2px 3px 2px 0;display:inline-block">{r}</span>'
            for r in rtbs
        )
        _lbl = "font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.1em;width:64px;flex-shrink:0"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.03);border:1px solid #334155;'
            f'border-radius:10px;padding:12px 14px;margin:6px 0 12px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl}">メイン</span>'
            f'<span style="color:#93c5fd;font-weight:700;font-size:0.9rem">'
            f'{selected_copy.get("headline","")}</span></div>'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl}">サブ</span>'
            f'<span style="color:#a5b4fc;font-size:0.83rem">'
            f'{selected_copy.get("sub_headline","")}</span></div>'
            f'<div style="display:flex;align-items:flex-start;gap:8px">'
            f'<span style="{_lbl};padding-top:4px">RTB</span>'
            f'<div style="flex:1">{rtb_pills or "<span style=\'color:#475569;font-size:0.75rem\'>なし</span>"}'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )


        # CTA 選択
        st.markdown(
            '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin:12px 0 6px">'
            'CTAテキスト</div>',
            unsafe_allow_html=True,
        )
        selected_cta = st.selectbox("CTA", _CTA_LIST, label_visibility="collapsed", key="banner_cta_sel")

    st.divider()

    # ── STEP 3 — 生成枚数・訴求パターン ──────────────────────────────────────
    _section("STEP 3 — 生成枚数・訴求パターン")

    selected_platform_name = st.selectbox(
        "プラットフォーム *",
        [p.name for p in PLATFORMS],
        index=0,
        key="banner_platform",
    )

    num_variations = st.selectbox(
        "生成枚数 *", [1, 2, 3, 4, 5], index=2,
        key="banner_num_var",
    )

    st.markdown(
        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin:12px 0 8px">訴求パターン *</div>',
        unsafe_allow_html=True,
    )
    tonmana_label = _pattern_grid()

    st.divider()

    # ── STEP 4 — 詳細設定 ──────────────────────────────────────────────────────
    _section("STEP 4 — 詳細設定")

    col_ppl, col_pimg, col_plogo = st.columns(3)
    with col_ppl:
        st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">人物の使用</div>', unsafe_allow_html=True)
        _ppl_sel = st.radio("人物", ["AIにおまかせ", "使用する", "使用しない"], horizontal=True,
                            key="banner_use_people", label_visibility="collapsed")
        use_people = None if _ppl_sel == "AIにおまかせ" else (_ppl_sel == "使用する")
    with col_pimg:
        st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">商品画像の使用</div>', unsafe_allow_html=True)
        use_product_image = st.radio("商品画像", ["使用する", "使用しない"], index=1, horizontal=True,
                                     key="banner_use_pimg", label_visibility="collapsed") == "使用する"
    with col_plogo:
        st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">商品ロゴの使用</div>', unsafe_allow_html=True)
        use_product_logo = st.radio("商品ロゴ", ["使用する", "使用しない"], index=1, horizontal=True,
                                    key="banner_use_plogo", label_visibility="collapsed") == "使用する"

    col_color, col_comment = st.columns([1, 2])
    with col_color:
        st.markdown(
            '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:6px">カラー</div>',
            unsafe_allow_html=True,
        )
        _preset_labels = [p[0] for p in _COLOR_PRESETS]
        _preset_sel = st.selectbox(
            "カラーセット", _preset_labels, index=0,
            key="banner_color_preset", label_visibility="collapsed",
        )
        _preset = next(p for p in _COLOR_PRESETS if p[0] == _preset_sel)
        if _preset[1] is None:
            col_b, col_a2 = st.columns(2)
            with col_b:
                st.caption("ベース")
                brand_primary = st.color_picker("ベース", "#ffffff", key="banner_brand_primary", label_visibility="collapsed")
            with col_a2:
                st.caption("アクセント")
                brand_accent = st.color_picker("アクセント", "#2563eb", key="banner_brand_accent", label_visibility="collapsed")
        else:
            brand_primary, brand_accent = _preset[1], _preset[2]
            col_b, col_a2 = st.columns(2)
            with col_b:
                st.markdown(
                    f'<div style="font-size:0.65rem;color:#64748b;margin-bottom:3px">ベース</div>'
                    f'<div style="height:26px;border-radius:6px;background:{brand_primary};'
                    f'border:1px solid #334155"></div>',
                    unsafe_allow_html=True,
                )
            with col_a2:
                st.markdown(
                    f'<div style="font-size:0.65rem;color:#64748b;margin-bottom:3px">アクセント</div>'
                    f'<div style="height:26px;border-radius:6px;background:{brand_accent};'
                    f'border:1px solid #334155"></div>',
                    unsafe_allow_html=True,
                )
    with col_comment:
        free_comment = st.text_area(
            "その他要望（任意）",
            placeholder="例: 女性向けの温かみあるビジュアルに / ロゴを目立たせて",
            height=68,
            key="banner_free_comment",
            label_visibility="visible",
        )

    # 生成ボタン
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    generate_btn = st.button(
        "バナーを生成",
        type="primary",
        use_container_width=True,
        disabled=(copies is not None and not copies),
    )

    # ── 生成処理 ────────────────────────────────────────────────────────────────
    if generate_btn:
        if not selected_copy:
            st.error("コピーを選択してください")
            st.stop()

        selected_platforms = [p for p in PLATFORMS if p.name == selected_platform_name]
        _sel_platform = selected_platforms[0] if selected_platforms else PLATFORMS[0]
        _gen_size = _sel_platform.gen_size
        _canvas_size = _sel_platform.get_canvas_label()

        _cache_raw_base = "|".join([
            selected_product.get("id", ""),
            selected_copy.get("id", ""),
            tonmana_label, selected_cta, str(num_variations),
            str(use_product_image), str(use_product_logo), str(use_people),
            brand_primary, brand_accent, free_comment.strip(),
            *sorted(rtbs),
        ])
        _brief_cache = st.session_state.setdefault("_brief_cache", {})

        with st.status("バナーを生成中...", expanded=True) as status:

            # AI推薦パターンの選択
            resolved_label = tonmana_label
            _ai_assignments: list[tuple[str, str]] = []  # (pattern_name, reason) — 複数推薦時
            _ppl_assign: list[bool] | None = None  # per-variation people assignment

            if tonmana_label == _AI_SENTINEL:
                st.write("**Step 0 / 3** — AI が最適な訴求パターンを選択中")
                available = [
                    {"name": n, "desc": _PATTERN_SHORT_DESC.get(n, "")}
                    for n in _TONMANA_NAMES
                ]
                try:
                    if num_variations >= 2:
                        # バリエーションごとに異なるパターンを推薦
                        _ai_assignments = recommend_patterns(
                            product_name=selected_product["product_name"],
                            product_info=selected_product.get("product_info", ""),
                            objective=selected_copy.get("objective", ""),
                            headline=selected_copy.get("headline", ""),
                            sub_headline=selected_copy.get("sub_headline", ""),
                            available_patterns=available,
                            count=num_variations,
                        )
                        # 汎用/ベーシックから必ず1パターン含める
                        _basic_pats = _PATTERN_GROUPS[0]["patterns"]
                        if not any(p in _basic_pats for p, _ in _ai_assignments):
                            _used = {p for p, _ in _ai_assignments}
                            _basic_candidate = next(
                                (p for p in _basic_pats if p not in _used), _basic_pats[0]
                            )
                            # 末尾の非ベーシックパターンを置き換え
                            for _ri in range(len(_ai_assignments) - 1, -1, -1):
                                if _ai_assignments[_ri][0] not in _basic_pats:
                                    _ai_assignments[_ri] = (_basic_candidate, "汎用ベーシックパターンとして選定")
                                    break
                        _ppl_assign: list[bool] | None = (
                            _assign_people_per_var(_ai_assignments, len(_ai_assignments))
                            if use_people is None else None
                        )
                        for i, (pname, preason) in enumerate(_ai_assignments):
                            _ppl_label = (
                                f" ・ {'人物あり' if _ppl_assign[i] else '人物なし'}"
                                if _ppl_assign is not None else ""
                            )
                            st.write(f"  ✓ バリエーション{chr(65 + i)}: **{pname}**　← {preason}{_ppl_label}")
                        resolved_label = " / ".join(p for p, _ in _ai_assignments)
                    else:
                        resolved_label, ai_reason = recommend_pattern(
                            product_name=selected_product["product_name"],
                            product_info=selected_product.get("product_info", ""),
                            objective=selected_copy.get("objective", ""),
                            headline=selected_copy.get("headline", ""),
                            sub_headline=selected_copy.get("sub_headline", ""),
                            available_patterns=available,
                        )
                        st.write(f"  ✓ 選択パターン: **{resolved_label}**　← {ai_reason}")
                except Exception as _e:
                    st.warning(f"AI推薦に失敗しました。最初のパターンを使用します: {_e}")
                    resolved_label = _TONMANA_NAMES[0] if _TONMANA_NAMES else ""

            _cache_key = hashlib.md5((_cache_raw_base + resolved_label).encode()).hexdigest()

            def _load_ref(pattern_name: str) -> tuple[str, str]:
                path = _TONMANA_IMG_MAP.get(pattern_name, "")
                if not path:
                    return "", "image/jpeg"
                try:
                    return _load_tonmana_b64(path)
                except Exception:
                    return "", "image/jpeg"

            def _gen_prompt_args(tonmana_desc: str, n_var: int, ref_b64: str, ref_mime: str) -> dict:
                return dict(
                    brand_name=selected_product["product_name"],
                    product=selected_product["product_name"],
                    message=selected_copy.get("headline", ""),
                    tonmana=tonmana_desc,
                    target_audience="",
                    num_variations=n_var,
                    appeal_axis=None,
                    product_context={
                        "product_info": selected_product.get("product_info", ""),
                        "lp_colors": [f"ベース:{brand_primary}", f"アクセント:{brand_accent}"],
                    },
                    objective="",
                    headline_copy=selected_copy.get("headline", ""),
                    sub_headline_copy=selected_copy.get("sub_headline", ""),
                    offer_copy=selected_cta,
                    features=rtbs,
                    use_product_image=use_product_image,
                    use_product_logo=use_product_logo,
                    use_people=use_people,
                    free_comment=free_comment.strip(),
                    reference_image_b64=ref_b64,
                    reference_image_mime=ref_mime,
                    canvas_size=_canvas_size,
                )

            if _cache_key in _brief_cache:
                variations = _brief_cache[_cache_key]
                st.write(f"✓ キャッシュ使用 — {len(variations)} バリエーション（Step 1 スキップ）")
            else:
                st.write("**Step 1 / 3** — Claude がデザインブリーフを生成中")
                try:
                    if _ai_assignments:
                        # バリエーションごとに異なるパターンでブリーフを生成
                        variations = []
                        for i, (pname, _) in enumerate(_ai_assignments):
                            p_desc = _TONMANA_DESC.get(pname, pname)
                            ref_b64, ref_mime = _load_ref(pname)
                            _args = _gen_prompt_args(p_desc, 1, ref_b64, ref_mime)
                            if _ppl_assign is not None:
                                _args["use_people"] = _ppl_assign[i]
                            v_list = generate_banner_prompts(**_args)
                            if v_list:
                                v_list[0]["variation"] = chr(65 + i)
                                variations.append(v_list[0])
                    else:
                        tonmana_desc = _TONMANA_DESC.get(resolved_label, resolved_label)
                        ref_b64, ref_mime = _load_ref(resolved_label)
                        if use_people is None and num_variations >= 2:
                            # AIにおまかせ×手動パターン×複数枚: 人物有無を振り分けて個別生成
                            variations = []
                            _ppl_assign_manual = _assign_people_per_var(None, num_variations)
                            for i, _vppl in enumerate(_ppl_assign_manual):
                                _args = _gen_prompt_args(tonmana_desc, 1, ref_b64, ref_mime)
                                _args["use_people"] = _vppl
                                v_list = generate_banner_prompts(**_args)
                                if v_list:
                                    v_list[0]["variation"] = chr(65 + i)
                                    variations.append(v_list[0])
                        else:
                            variations = generate_banner_prompts(**_gen_prompt_args(tonmana_desc, num_variations, ref_b64, ref_mime))

                    if not variations:
                        st.error("バリエーションが生成されませんでした。再度「バナーを生成」を押してください。")
                        st.stop()
                    _brief_cache[_cache_key] = variations
                    st.write(f"✓ {len(variations)} バリエーション確定")
                except Exception as e:
                    st.error(f"プロンプト生成エラー: {e}")
                    st.stop()

            n = len(variations)
            st.write(f"**Step 2 / 3** — gpt-image-2 で {n} 枚を並列生成中")

            # 訴求パターン画像をgpt-image-2にも渡す（レイアウト参照用）
            _ref_pil_map: dict[str, Image.Image | None] = {}
            if _ai_assignments:
                for _i, (_pname, _) in enumerate(_ai_assignments):
                    _vl = chr(65 + _i)
                    _ip = _TONMANA_IMG_MAP.get(_pname, "")
                    try:
                        _ref_pil_map[_vl] = Image.open(_ip).convert("RGB") if _ip else None
                    except Exception:
                        _ref_pil_map[_vl] = None
            else:
                _ip = _TONMANA_IMG_MAP.get(resolved_label, "")
                try:
                    _shared_ref = Image.open(_ip).convert("RGB") if _ip else None
                except Exception:
                    _shared_ref = None
                for _v in variations:
                    _ref_pil_map[_v["variation"]] = _shared_ref

            results = [None] * n
            preview_cols = st.columns(n)
            col_slots = [col.empty() for col in preview_cols]

            def _gen(item):
                idx, v = item
                ref_pil = _ref_pil_map.get(v["variation"])
                img = generate_image(v["prompt"], reference_image=ref_pil, size=_gen_size)
                return idx, v, resize_for_selected_platforms(img, selected_platforms)

            gen_errors = []
            with ThreadPoolExecutor(max_workers=n) as pool:
                futures = {pool.submit(_gen, (i, v)): i for i, v in enumerate(variations)}
                done = 0
                for fut in as_completed(futures):
                    try:
                        idx, v_res, pimgs = fut.result()
                    except Exception as e:
                        gen_errors.append(str(e))
                        continue
                    done += 1
                    results[idx] = (v_res, pimgs)
                    col_slots[idx].image(
                        _img_to_bytes(pimgs[0][1]),
                        caption=f"[{v_res['variation']}] {v_res['label']}",
                        use_container_width=True,
                    )
                    st.write(f"  ✓ [{v_res['variation']}] {v_res['label']} 完了 ({done}/{n})")

            if gen_errors:
                st.error(f"画像生成エラー:\n\n```\n{gen_errors[0]}\n```")
                st.stop()

            st.write("**Step 3 / 3** — バナーを保存中")
            for v, platform_images in results:
                save_banner_entry(
                    product_name=selected_product["product_name"],
                    axis_label=selected_copy.get("headline", ""),
                    variation=v,
                    platform_images=platform_images,
                    tonmana=resolved_label,
                    objective="",
                )
            st.write(f"✓ {len(results)} バリエーションを保存しました")
            status.update(label="生成完了！", state="complete", expanded=False)

        st.session_state["gen_results"]   = results
        st.session_state["gen_product"]   = selected_product
        st.session_state["gen_copy"]      = selected_copy
        st.session_state["gen_cta"]       = selected_cta
        st.session_state["gen_platforms"] = selected_platforms
        st.session_state["gen_tonmana"]   = resolved_label

# ══════════════════════════════════════════════════════════════════════════════
# リサイズ
# ══════════════════════════════════════════════════════════════════════════════
else:
    try:
        all_banners = load_banners()
    except Exception as _e:
        st.error(
            "⚠️ **Supabase 接続エラー**\n\n"
            "Supabase プロジェクトが一時停止しているか、Secrets の設定が正しくない可能性があります。\n\n"
            f"エラー詳細: `{_e}`"
        )
        st.stop()

    banners_with_img = [
        b for b in sorted(all_banners, key=lambda x: x["created_at"], reverse=True)
        if b.get("platforms")
    ]

    if not banners_with_img:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
            'border-radius:12px;padding:40px;text-align:center;color:#64748b">'
            '保存済みバナーがありません。まず「新規生成」でバナーを生成してください。</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    # ── バナー選択 ────────────────────────────────────────────────────────────
    _section("リサイズするバナーを選択", margin_top="0")

    st.markdown(
        "<style>[data-testid='stColumn']:has(.resize-sel-marker){"
        "outline:3px solid #8b5cf6;border-radius:12px;padding:4px !important}</style>",
        unsafe_allow_html=True,
    )

    if ("resize_sel_idx" not in st.session_state
            or st.session_state["resize_sel_idx"] >= len(banners_with_img)):
        st.session_state["resize_sel_idx"] = 0

    n_cols = 3
    for row_start in range(0, len(banners_with_img), n_cols):
        row = banners_with_img[row_start:row_start + n_cols]
        cols = st.columns(n_cols)
        for c_idx, (col, b) in enumerate(zip(cols, row)):
            idx = row_start + c_idx
            is_sel = st.session_state["resize_sel_idx"] == idx
            with col:
                if is_sel:
                    st.markdown('<div class="resize-sel-marker" style="display:none"></div>',
                                unsafe_allow_html=True)
                img_url = b["platforms"][0].get("public_url", "")
                if img_url:
                    st.image(img_url, use_container_width=True)
                short_lbl = f"[{b.get('variation','')}] {b.get('label','')}"
                st.caption(short_lbl[:32] + ("…" if len(short_lbl) > 32 else ""))
                if is_sel:
                    st.markdown(
                        '<div style="text-align:center;color:#8b5cf6;font-size:0.72rem;'
                        'font-weight:700;margin-bottom:4px">✓ 選択中</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button("選択", key=f"resize_sel_{idx}",
                                 use_container_width=True, type="secondary"):
                        st.session_state["resize_sel_idx"] = idx
                        st.rerun()

    sel_resize_banner = banners_with_img[st.session_state["resize_sel_idx"]]

    # ── プラットフォーム選択 ──────────────────────────────────────────────────
    _section("出力プラットフォーム")
    selected_resize_platform_names = st.multiselect(
        "プラットフォームを選択 *",
        [p.name for p in PLATFORMS],
        default=[PLATFORMS[0].name],
        key="resize_platforms",
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    resize_btn = st.button("リサイズを実行", type="primary", use_container_width=True)

    if resize_btn:
        if not selected_resize_platform_names:
            st.error("プラットフォームを1つ以上選択してください")
        else:
            src_url = sel_resize_banner["platforms"][0].get("public_url", "")
            try:
                img_bytes = requests.get(src_url, timeout=15).content
                src_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            except Exception as e:
                st.error(f"元画像の読み込みに失敗しました: {e}")
                st.stop()

            target_platforms = [p for p in PLATFORMS if p.name in selected_resize_platform_names]
            resized_imgs = resize_for_selected_platforms(src_img, target_platforms)
            st.session_state["resize_results"] = resized_imgs
            st.session_state["resize_banner"]  = sel_resize_banner

    # リサイズ結果表示
    if st.session_state.get("resize_results"):
        resized_imgs = st.session_state["resize_results"]

        st.divider()
        st.markdown(
            '<div style="background:linear-gradient(135deg,rgba(16,185,129,0.12),'
            'rgba(16,185,129,0.04));border:1px solid rgba(16,185,129,0.35);border-radius:12px;'
            'padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
            '<div style="color:#10b981;font-size:1.1rem">✓</div>'
            f'<div style="color:#10b981;font-weight:700;font-size:0.9rem">'
            f'{len(resized_imgs)} サイズにリサイズしました</div></div>',
            unsafe_allow_html=True,
        )

        chunk = 4
        for row_start in range(0, len(resized_imgs), chunk):
            row_r = resized_imgs[row_start:row_start + chunk]
            rcols = st.columns(len(row_r))
            for col, (platform, img) in zip(rcols, row_r):
                with col:
                    st.image(img, caption=f"{platform.name}\n{platform.width}×{platform.height}",
                             use_container_width=True)
                    fname = f"{platform.filename}_{platform.width}x{platform.height}.png"
                    st.download_button(
                        f"↓ {fname}",
                        data=_img_to_bytes(img),
                        file_name=fname,
                        mime="image/png",
                        key=f"resize_dl_{platform.filename}",
                        use_container_width=True,
                    )

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for platform, img in resized_imgs:
                fname = f"{platform.filename}_{platform.width}x{platform.height}.png"
                zf.writestr(fname, _img_to_bytes(img))
        st.download_button(
            "ZIP でダウンロード",
            data=zip_buf.getvalue(),
            file_name=f"resized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            key="resize_zip_dl",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 生成結果表示（新規生成モードのみ）
# ══════════════════════════════════════════════════════════════════════════════
if _banner_mode == "新規生成" and st.session_state.get("gen_results"):
    results           = st.session_state["gen_results"]
    current_product   = st.session_state.get("gen_product", {})
    current_copy      = st.session_state.get("gen_copy", {})
    current_platforms = st.session_state.get("gen_platforms", [])

    st.divider()

    st.markdown(
        f'<div style="background:linear-gradient(135deg,rgba(16,185,129,0.12),'
        f'rgba(16,185,129,0.04));border:1px solid rgba(16,185,129,0.35);border-radius:12px;'
        f'padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
        f'<div style="color:#10b981;font-size:1.1rem">✓</div>'
        f'<div>'
        f'<div style="color:#10b981;font-weight:700;font-size:0.9rem">'
        f'{len(results)} バリエーション × {len(current_platforms)} プラットフォーム を生成・保存しました</div>'
        f'<div style="color:#6ee7b7;font-size:0.78rem;margin-top:2px">'
        f'「保存済みバナー」ページからいつでも確認・ダウンロードできます</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    col_title, col_saved, col_dl = st.columns([3, 1, 1])
    with col_title:
        st.caption(
            f"商品: {current_product.get('product_name', '—')} ｜ "
            f"コピー: {current_copy.get('headline', '—')} ｜ "
            f"訴求パターン: {st.session_state.get('gen_tonmana', '—')}"
        )
    with col_saved:
        if st.button("保存済みバナー →", type="secondary", use_container_width=True, key="goto_saved"):
            st.switch_page("pages/saved_banners.py")
    with col_dl:
        st.download_button(
            "ZIP でダウンロード",
            data=_build_zip(results),
            file_name=f"banners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True,
        )

    st.divider()

    n_res = len(results)
    thumb_cols = st.columns(n_res)
    for (v_t, pimgs_t), _col in zip(results, thumb_cols):
        with _col:
            st.image(_img_to_bytes(pimgs_t[0][1]), use_container_width=True)
            st.caption(f"[{v_t['variation']}] {v_t['label']}")

    st.divider()

    for tab_idx, (v, platform_images) in enumerate(results):
        with st.expander(f"[{v['variation']}]  {v['label']}", expanded=(tab_idx == 0)):
            st.markdown(f"**戦略:** {v['rationale']}")
            with st.expander("生成プロンプトを見る"):
                st.code(v["prompt"], language=None)

            st.markdown("**プラットフォーム別プレビュー**")
            chunk = 4
            for row_start in range(0, len(platform_images), chunk):
                row   = platform_images[row_start: row_start + chunk]
                n_row = len(row)
                if n_row == 1:
                    _lc, _mc, _rc = st.columns([1, 2, 1])
                    render_cols = [_mc]
                else:
                    render_cols = st.columns(n_row)
                for col, (platform, img) in zip(render_cols, row):
                    with col:
                        st.image(img, caption=f"{platform.name}\n{platform.width}×{platform.height}",
                                 use_container_width=True)
                        st.download_button(
                            f"↓ {platform.filename}_{platform.width}x{platform.height}.png",
                            data=_img_to_bytes(img),
                            file_name=f"{platform.filename}_{platform.width}x{platform.height}.png",
                            mime="image/png",
                            key=f"dl_{tab_idx}_{platform.filename}",
                            use_container_width=True,
                        )

            st.divider()
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px">パーツ別修正</div>',
                unsafe_allow_html=True,
            )

            _prompt_key = f"_varcopy_{hashlib.md5(v['prompt'].encode()).hexdigest()[:12]}"
            if _prompt_key not in st.session_state:
                with st.spinner("テキスト要素を解析中..."):
                    try:
                        st.session_state[_prompt_key] = extract_banner_copy(v["prompt"])
                    except Exception:
                        st.session_state[_prompt_key] = {
                            "headlines": [], "sub_headlines": [], "offers": [], "features": []
                        }
            _var_copy = st.session_state[_prompt_key]

            REVISION_PARTS = ["訴求パターン", "ビジュアル", "テキスト"]
            sel_part = st.radio(
                "① 修正するパーツ",
                REVISION_PARTS,
                horizontal=True,
                key=f"rev_part_{tab_idx}",
            )

            target_elem      = None
            rev_instructions = ""
            rev_part_label   = sel_part

            if sel_part == "訴求パターン":
                _cur_ton = st.session_state.get("gen_tonmana", _TONMANA_NAMES[0] if _TONMANA_NAMES else "")
                _ton_idx = _TONMANA_NAMES.index(_cur_ton) if _cur_ton in _TONMANA_NAMES else 0
                _new_ton = st.selectbox(
                    "② 新しい訴求パターン",
                    _TONMANA_NAMES,
                    index=_ton_idx,
                    key=f"rev_ton_{tab_idx}",
                )
                rev_instructions = f"Change the tone and manner to: {_TONMANA_DESC.get(_new_ton, _new_ton)}"

            elif sel_part == "ビジュアル":
                st.markdown(
                    '<div style="color:#475569;font-size:0.78rem;padding:6px 0">'
                    'ビジュアル全体が対象です — ③に修正指示を入力してください</div>',
                    unsafe_allow_html=True,
                )
                rev_instructions = st.text_area(
                    "③ 修正指示",
                    placeholder="例: もっとインパクトのある写真に / 屋外シーンに変更",
                    key=f"rev_inst_{tab_idx}",
                    height=80,
                )

            else:
                _text_items: list[tuple[str, str]] = []
                for _h in _var_copy.get("headlines", []):
                    _text_items.append(("メインキャッチ", _h))
                for _sh in _var_copy.get("sub_headlines", []):
                    _text_items.append(("サブキャッチ", _sh))
                for _o in _var_copy.get("offers", []):
                    _text_items.append(("オファー・CTA", _o))
                for _f in _var_copy.get("features", []):
                    _text_items.append(("特徴・アイコン", _f))

                if _text_items:
                    _sel_text = st.selectbox(
                        "② 修正する要素",
                        [t for _, t in _text_items],
                        key=f"rev_elem_{tab_idx}",
                    )
                    rev_part_label = next(
                        (cat for cat, txt in _text_items if txt == _sel_text), "テキスト"
                    )
                    target_elem = _sel_text
                else:
                    _raw_elem = st.text_input(
                        "② 修正する要素",
                        placeholder="テキストを入力（空欄可）",
                        key=f"rev_elem_raw_{tab_idx}",
                    )
                    target_elem = _raw_elem.strip() or None

                rev_instructions = st.text_area(
                    "③ 修正指示",
                    placeholder="例: より短く簡潔に / インパクトを強めて",
                    key=f"rev_inst_{tab_idx}",
                    height=80,
                )

            if st.button(
                f"「{sel_part}」を修正して再生成",
                key=f"rev_part_btn_{tab_idx}",
                type="primary",
                use_container_width=True,
            ):
                if sel_part != "トンマナ" and not rev_instructions.strip():
                    st.warning("③ に修正指示を入力してください")
                else:
                    with st.spinner(f"「{sel_part}」を修正して再生成中..."):
                        try:
                            new_prompt = refine_banner_part(
                                v["prompt"], rev_part_label, target_elem, rev_instructions
                            )
                            new_base_img = generate_image(new_prompt)
                            new_platform_images = resize_for_selected_platforms(
                                new_base_img, current_platforms
                            )
                            part_suffix = f" [{sel_part}修正]"
                            base_label  = v["label"].split(" [")[0]
                            updated_v   = {**v, "prompt": new_prompt, "label": base_label + part_suffix}
                            save_banner_entry(
                                product_name=current_product.get("product_name", ""),
                                axis_label=current_copy.get("headline", ""),
                                variation=updated_v,
                                platform_images=new_platform_images,
                                tonmana=st.session_state.get("gen_tonmana", ""),
                                objective="",
                            )
                            updated = list(st.session_state["gen_results"])
                            updated[tab_idx] = (updated_v, new_platform_images)
                            st.session_state["gen_results"] = updated
                            st.rerun()
                        except Exception as e:
                            st.error(f"修正エラー: {e}")
