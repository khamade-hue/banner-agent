"""Page 1: ターゲットと訴求軸の検討エージェント"""

import os
import re
import sys
import urllib.request

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import analyze_product, generate_more_axes, refine_copy_part
from state import add_axis, delete_axis, load_axes, load_products


def _fetch_page_content(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]
    except Exception:
        return ""


def _extract_lp_colors(url: str) -> list[str]:
    """Fetch LP and extract dominant brand colors from CSS / inline styles."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    css_chunks    = re.findall(r"<style[^>]*>([\s\S]*?)</style>", html, re.IGNORECASE)
    inline_chunks = re.findall(r'style="([^"]*)"', html)
    target = " ".join(css_chunks + inline_chunks)

    counts: dict[str, int] = {}
    for m in re.finditer(r"#([0-9a-fA-F]{6})\b", target):
        h = m.group(1).upper()
        r_val, g_val, b_val = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = (r_val + g_val + b_val) / 3
        if lum < 20 or lum > 235:  # skip near-black / near-white
            continue
        counts[f"#{h}"] = counts.get(f"#{h}", 0) + 1

    return sorted(counts, key=lambda c: counts[c], reverse=True)[:6]


def _c3_card(title: str, color: str, gradient: str, icon: str, items: list) -> str:
    rows = "".join(
        f'<div style="margin-bottom:12px">'
        f'<div style="font-size:0.7rem;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px">{label}</div>'
        f'<div style="color:#cbd5e1;font-size:0.875rem;line-height:1.6">{value}</div>'
        f'</div>'
        for label, value in items
    )
    return (
        f'<div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:14px;'
        f'padding:20px 22px;border-top:3px solid {color};margin-bottom:10px;'
        f'box-shadow:0 4px 24px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.04)">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">'
        f'<div style="background:{gradient};width:34px;height:34px;border-radius:10px;'
        f'display:flex;align-items:center;justify-content:center;font-size:1rem;'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.3)">{icon}</div>'
        f'<span style="font-weight:700;font-size:0.95rem;color:#f1f5f9">{title}</span>'
        f'</div>{rows}</div>'
    )


def _pills(items: list, bg: str, color: str, border: str) -> str:
    return "".join(
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'border:1px solid {border};border-radius:20px;padding:5px 13px;'
        f'font-size:0.8rem;margin:3px 4px 3px 0;line-height:1.3;font-weight:500">{item}</span>'
        for item in items
    )


def _copy_section(label: str, items: list, bg: str, color: str, border: str) -> str:
    if not items:
        return ""
    return (
        f'<div style="margin-bottom:8px">'
        f'<div style="font-size:0.67rem;font-weight:700;color:#64748b;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin-bottom:5px">{label}</div>'
        f'{_pills(items, bg, color, border)}'
        f'</div>'
    )


def _copy_html(copy_s: dict) -> str:
    if not copy_s:
        return ""
    sections = (
        _copy_section("キャッチコピー", copy_s.get("headlines", []),
                      "rgba(59,130,246,0.15)", "#93c5fd", "rgba(59,130,246,0.4)") +
        _copy_section("オファー・CTA", copy_s.get("offers", []),
                      "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.4)") +
        _copy_section("特徴・アイコン", copy_s.get("features", []),
                      "rgba(139,92,246,0.15)", "#c4b5fd", "rgba(139,92,246,0.4)")
    )
    if not sections:
        return ""
    return (
        f'<div style="border-top:1px solid #334155;margin-top:14px;padding-top:14px">'
        f'{sections}</div>'
    )


_SET_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899"]


def _copy_sets_html(copy_sets: list) -> str:
    if not copy_sets:
        return ""
    cards = ""
    for i, cs in enumerate(copy_sets):
        color = _SET_COLORS[i % len(_SET_COLORS)]
        feat_pills = _pills(
            cs.get("features", []),
            "rgba(139,92,246,0.12)", "#c4b5fd", "rgba(139,92,246,0.35)",
        )
        _lbl = (
            f'font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;'
            f'letter-spacing:0.1em;flex-shrink:0;width:68px'
        )
        cards += (
            f'<div style="border:1px solid {color}33;border-left:3px solid {color};'
            f'border-radius:10px;padding:12px 14px;margin-bottom:10px;'
            f'background:rgba(255,255,255,0.02)">'
            f'<div style="font-size:0.6rem;font-weight:700;color:{color};text-transform:uppercase;'
            f'letter-spacing:0.12em;margin-bottom:10px">セット {i + 1}</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl}">メインキャッチ</span>'
            f'<span style="background:rgba(59,130,246,0.15);color:#93c5fd;'
            f'border:1px solid rgba(59,130,246,0.4);border-radius:14px;'
            f'padding:3px 11px;font-size:0.82rem;font-weight:600">{cs.get("headline","")}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl}">サブキャッチ</span>'
            f'<span style="background:rgba(99,102,241,0.12);color:#a5b4fc;'
            f'border:1px solid rgba(99,102,241,0.35);border-radius:14px;'
            f'padding:3px 11px;font-size:0.8rem">{cs.get("sub_headline","")}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl};padding-top:5px">特徴</span>'
            f'<div style="flex:1">{feat_pills}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px">'
            f'<span style="{_lbl}">CTA</span>'
            f'<span style="background:rgba(16,185,129,0.12);color:#6ee7b7;'
            f'border:1px solid rgba(16,185,129,0.35);border-radius:14px;'
            f'padding:3px 11px;font-size:0.8rem">{cs.get("offer","")}</span>'
            f'</div>'
            f'</div>'
        )
    return (
        f'<div style="border-top:1px solid #334155;margin-top:14px;padding-top:14px">{cards}</div>'
    )


def _axis_card_body(ax: dict) -> str:
    copy_html = (
        _copy_sets_html(ax["copy_sets"])
        if ax.get("copy_sets")
        else _copy_html(ax.get("copy_suggestions", {}))
    )
    return (
        f'<p style="color:#94a3b8;font-size:0.85rem;line-height:1.65;margin:8px 0 10px">'
        f'{ax.get("description","")}</p>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px">'
        f'<div style="background:rgba(255,255,255,0.05);border:1px solid #334155;'
        f'border-radius:8px;padding:4px 11px;font-size:0.76rem">'
        f'<span style="color:#64748b;font-weight:600">🎯 ターゲット</span>'
        f'<span style="color:#cbd5e1;margin-left:5px">{ax.get("target_segment","—")}</span>'
        f'</div>'
        f'<div style="background:rgba(255,255,255,0.05);border:1px solid #334155;'
        f'border-radius:8px;padding:4px 11px;font-size:0.76rem">'
        f'<span style="color:#64748b;font-weight:600">💡 根拠</span>'
        f'<span style="color:#cbd5e1;margin-left:5px">{ax.get("rationale","—")}</span>'
        f'</div></div>'
        f'{copy_html}'
    )


BADGE_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
BADGE_GLOWS  = [
    "rgba(59,130,246,0.35)", "rgba(139,92,246,0.35)",
    "rgba(236,72,153,0.35)", "rgba(245,158,11,0.35)", "rgba(16,185,129,0.35)",
]

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e3a8a 60%,#1d4ed8 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:24px;'
    'border:1px solid rgba(59,130,246,0.3);'
    'box-shadow:0 8px 32px rgba(37,99,235,0.25),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
    '<div style="background:rgba(59,130,246,0.25);border:1px solid rgba(59,130,246,0.4);'
    'border-radius:8px;padding:3px 10px;font-size:0.72rem;font-weight:700;'
    'color:#93c5fd;letter-spacing:0.1em;text-transform:uppercase">Step 1 / 2</div>'
    '<div style="color:#475569;font-size:0.75rem">次: バナー生成</div>'
    '</div>'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">訴求軸生成</h1>'
    '<p style="color:#93c5fd;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    '登録済みの商品を選択し、Claude が 3C 分析を実施して SNS 広告の最適な訴求軸とコピー候補を提案します'
    '</p></div>',
    unsafe_allow_html=True,
)

# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio(
    "生成方法",
    ["新規作成", "既存の磨きこみ"],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown(
    f'<div style="color:#64748b;font-size:0.78rem;margin:2px 0 20px;padding-left:2px">'
    f'{"登録済みの商品を選択して 3C 分析と訴求軸を自動生成します" if mode == "新規作成" else "保存済みの訴求軸のコピーを手動またはAIで磨きこみます"}'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# MODE A: 新規作成
# ══════════════════════════════════════════════════════════════════════════════
if mode == "新規作成":
    products = load_products()

    if not products:
        st.markdown(
            '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
            'border-radius:14px;padding:48px;text-align:center">'
            '<div style="font-size:2.5rem;margin-bottom:14px">📦</div>'
            '<div style="color:#f1f5f9;font-size:1.05rem;font-weight:700;margin-bottom:8px">'
            '商品がまだ登録されていません</div>'
            '<div style="color:#64748b;font-size:0.85rem;margin-bottom:20px">'
            '先に「商品登録」ページで商品情報を登録してください</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("商品を登録する →", type="primary"):
            st.switch_page("pages/product.py")
        st.stop()

    # ── ① 商品選択 ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:8px">① 商品選択</div>',
        unsafe_allow_html=True,
    )
    product_opts = {p["product_name"]: p for p in reversed(products)}
    sel_product_name = st.selectbox(
        "商品を選択 *",
        list(product_opts.keys()),
        label_visibility="collapsed",
        key="sel_product",
    )
    sel_product = product_opts[sel_product_name]

    col_prev, col_url = st.columns([3, 2])
    with col_prev:
        if sel_product.get("product_info"):
            info_text = sel_product["product_info"]
            preview   = info_text[:200] + ("…" if len(info_text) > 200 else "")
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.03);border:1px solid #334155;'
                f'border-radius:10px;padding:10px 14px;font-size:0.78rem;color:#94a3b8;'
                f'line-height:1.6;margin-top:8px">{preview}</div>',
                unsafe_allow_html=True,
            )
    with col_url:
        competitor_badge = (
            '<div style="font-size:0.7rem;color:#64748b;margin-top:6px">競合情報あり ✓</div>'
            if sel_product.get("competitor_info") else ""
        )
        st.markdown(
            f'<div style="margin-top:8px">'
            f'<div style="font-size:0.7rem;color:#64748b;margin-bottom:3px">商品URL</div>'
            f'<div style="font-size:0.75rem;color:#93c5fd;word-break:break-all">'
            f'{sel_product.get("product_url", "—")}</div>'
            f'{competitor_badge}</div>',
            unsafe_allow_html=True,
        )

    # ── ② フリーコメント ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:20px 0 8px">② フリーコメント（任意）</div>',
        unsafe_allow_html=True,
    )
    free_comment = st.text_area(
        "フリーコメント",
        placeholder="例: 30代女性がメインターゲット / 今月は認知拡大を優先したい / 競合との差別化はスピードと価格",
        height=90,
        label_visibility="collapsed",
        key="free_comment",
    )

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    if st.button("3C分析・訴求軸を生成", type="primary", use_container_width=True, key="gen_analysis"):
        with st.status("分析中...", expanded=True) as status:
            page_content = sel_product.get("product_info", "")
            if page_content:
                st.write(f"✓ 商品情報を使用（{len(page_content)} 文字）")
            else:
                st.write("自社ページを取得中...")
                page_content = _fetch_page_content(sel_product.get("product_url", ""))
                st.write(
                    f"✓ 取得完了（{len(page_content)} 文字）"
                    if page_content else "⚠ ページ取得失敗（URL情報のみで分析）"
                )

            competitor_content = sel_product.get("competitor_info", "")
            if competitor_content:
                st.write("✓ 競合情報あり → 使用します")
            else:
                st.write("競合情報なし → Claude が自動リサーチします")

            # LPブランドカラーを抽出（分析テキストとは別にURLから取得）
            _product_url_for_colors = sel_product.get("product_url", "")
            if _product_url_for_colors:
                st.write("LPブランドカラーを抽出中...")
                lp_colors = _extract_lp_colors(_product_url_for_colors)
                st.write(
                    f"✓ ブランドカラー {len(lp_colors)} 色を取得: {' '.join(lp_colors)}"
                    if lp_colors else "⚠ カラー取得できず（スキップ）"
                )
            else:
                lp_colors = []

            st.write("Claude が3C分析・訴求軸を生成中...")
            try:
                analysis = analyze_product(
                    sel_product["product_name"],
                    sel_product.get("product_url", ""),
                    page_content,
                    competitor_content=competitor_content,
                    free_comment=free_comment,
                )
            except Exception as e:
                err = str(e)
                if "overloaded" in err or "529" in err:
                    st.error("Anthropic API が一時的に混雑しています。少し待ってから再度お試しください。")
                else:
                    st.error(f"分析エラー: {e}")
                st.stop()

            status.update(label="分析完了！", state="complete", expanded=False)

        st.session_state["analysis"]          = analysis
        st.session_state["analysis_lp_colors"] = lp_colors
        st.session_state["analysis_product_name"] = sel_product["product_name"]
        st.session_state["analysis_product_url"]  = sel_product.get("product_url", "")

    if "analysis" in st.session_state:
        analysis = st.session_state["analysis"]
        product_name_s = st.session_state.get("analysis_product_name", "")
        product_url_s  = st.session_state.get("analysis_product_url", "")
        c3   = analysis.get("3c_analysis", {})
        cust = c3.get("customer", {})
        comp = c3.get("competitor", {})
        co   = c3.get("company", {})

        current_axes     = analysis.get("appeal_axes", [])
        saved_axes_list  = load_axes()
        saved_axis_names = {a["axis"] for a in saved_axes_list}
        product_context  = {
            "value_proposition": co.get("value_proposition",""),
            "strengths": co.get("strengths",""),
            "customer_needs": cust.get("needs",""),
            "pain_points": cust.get("pain_points",""),
            "differentiation": comp.get("differentiation",""),
            "lp_colors": st.session_state.get("analysis_lp_colors", []),
        }

        # ── 3C 分析の詳細（先頭に表示）────────────────────────────────────────
        with st.expander("3C 分析の詳細を見る", expanded=True):
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px">3C 分析結果</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_c3_card(
                "顧客 Customer", "#3b82f6", "linear-gradient(135deg,#1d4ed8,#3b82f6)", "👥",
                [("ニーズ", cust.get("needs","—")),
                 ("課題・ペイン", cust.get("pain_points","—")),
                 ("属性", cust.get("demographics","—"))],
            ), unsafe_allow_html=True)
            st.markdown(_c3_card(
                "競合 Competitor", "#f43f5e", "linear-gradient(135deg,#be123c,#f43f5e)", "⚔️",
                [("競合状況", comp.get("landscape","—")),
                 ("差別化ポイント", comp.get("differentiation","—"))],
            ), unsafe_allow_html=True)
            st.markdown(_c3_card(
                "自社 Company", "#10b981", "linear-gradient(135deg,#059669,#10b981)", "🏢",
                [("強み", co.get("strengths","—")),
                 ("提供価値", co.get("value_proposition","—"))],
            ), unsafe_allow_html=True)

        # ── 提案訴求軸 ────────────────────────────────────────────────────────
        st.markdown(
            '<div style="margin-top:20px;margin-bottom:16px">'
            '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:6px">提案訴求軸</div>'
            '<p style="color:#64748b;font-size:0.82rem;margin:0">'
            '「＋ 追加」を押してバナー生成で使えるように保存してください'
            '</p></div>',
            unsafe_allow_html=True,
        )

        for i, ax in enumerate(current_axes):
            color  = BADGE_COLORS[i % len(BADGE_COLORS)]
            glow   = BADGE_GLOWS[i % len(BADGE_GLOWS)]
            marker = f"axis-card-{i}"

            st.markdown(
                f"<style>[data-testid='stVerticalBlockBorderWrapper']:has(.{marker}){{"
                f"border-left:4px solid {color} !important;"
                f"border-radius:16px !important;"
                f"box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 12px {glow} !important;"
                f"}}</style>",
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.markdown(f'<div class="{marker}" style="display:none"></div>',
                            unsafe_allow_html=True)
                col_title, col_btn = st.columns([8, 2])
                with col_title:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px">'
                        f'<div style="display:inline-flex;align-items:center;justify-content:center;'
                        f'width:28px;height:28px;border-radius:50%;background:{color};'
                        f'color:white;font-weight:800;font-size:12px;flex-shrink:0;'
                        f'box-shadow:0 2px 8px {glow}">{i+1}</div>'
                        f'<span style="font-size:1.0rem;font-weight:800;color:#f1f5f9;'
                        f'letter-spacing:-0.01em">{ax["axis"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if ax["axis"] in saved_axis_names:
                        st.markdown(
                            '<div style="display:flex;flex-direction:column;align-items:center;gap:4px">'
                            '<div style="width:28px;height:28px;border-radius:50%;'
                            'background:rgba(16,185,129,0.15);border:2px solid #10b981;'
                            'display:flex;align-items:center;justify-content:center;'
                            'color:#10b981;font-size:13px;font-weight:800">✓</div>'
                            '<div style="color:#10b981;font-size:0.67rem;font-weight:700;'
                            'text-align:center">保存済み</div>'
                            '</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        if st.button("＋ 追加", key=f"add_axis_{i}", type="primary",
                                     use_container_width=True):
                            add_axis(product_name_s, product_url_s, ax, product_context)
                            st.rerun()
                st.markdown(_axis_card_body(ax), unsafe_allow_html=True)

        # ── 次のアクション ─────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
        saved_count = len(saved_axes_list)
        if saved_count > 0:
            col_cta, col_info = st.columns([3, 2])
            with col_cta:
                if st.button("バナー生成へ進む →", type="primary",
                             use_container_width=True, key="goto_banner"):
                    st.switch_page("pages/banner.py")
            with col_info:
                st.markdown(
                    f'<div style="height:38px;display:flex;align-items:center">'
                    f'<span style="color:#10b981;font-size:0.8rem;font-weight:600">'
                    f'✓ {saved_count} 件の訴求軸を保存中</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.2);'
                'border-radius:10px;padding:12px 16px">'
                '<span style="color:#93c5fd;font-size:0.82rem">'
                '上の訴求軸に「＋ 追加」を押して保存すると、バナー生成へ進めます'
                '</span></div>',
                unsafe_allow_html=True,
            )

        # ── さらに訴求軸を追加 ─────────────────────────────────────────────────
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        with st.expander("さらに違う角度で訴求軸を追加生成する"):
            st.caption("別の切り口（季節訴求・価格訴求・BtoB向けなど）を指定して追加できます")
            add_angle = st.text_input(
                "追加で検討したい観点",
                placeholder="例: 季節訴求、価格訴求、BtoB向けなど",
                key="add_angle_input",
            )
            if st.button("追加訴求軸を生成", key="gen_more_btn", type="primary"):
                with st.spinner("訴求軸を生成中..."):
                    try:
                        new_axes = generate_more_axes(product_name_s, current_axes, add_angle, analysis_result=c3)
                        analysis["appeal_axes"] = current_axes + new_axes
                        st.session_state["analysis"] = analysis
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成エラー: {e}")



# ══════════════════════════════════════════════════════════════════════════════
# MODE B: 既存の磨きこみ
# ══════════════════════════════════════════════════════════════════════════════
else:
    saved_axes = load_axes()

    if not saved_axes:
        st.markdown(
            '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
            'border-radius:14px;padding:40px;text-align:center">'
            '<div style="color:#f1f5f9;font-size:1rem;font-weight:700;margin-bottom:8px">'
            '保存済みの訴求軸がありません</div>'
            '<div style="color:#64748b;font-size:0.85rem">'
            'まず「新規作成」で訴求軸を生成・保存してください</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    # ── 訴求軸セレクタ ────────────────────────────────────────────────────────
    axis_options = {f"{a['product_name']} — {a['axis']}": a for a in saved_axes}
    selected_label = st.selectbox(
        "磨きこむ訴求軸を選択",
        list(axis_options.keys()),
        key="refine_axis_select",
    )
    selected_ax = axis_options[selected_label]

    # ── 現在の訴求軸（読み取り専用）──────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:16px 0 10px">現在の訴求軸</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<style>[data-testid='stVerticalBlockBorderWrapper']:has(.refine-current){"
        "border-left:4px solid #475569 !important;border-radius:16px !important;"
        "opacity:0.75;}</style>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown('<div class="refine-current" style="display:none"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<span style="font-size:1.0rem;font-weight:800;color:#f1f5f9">'
            f'{selected_ax["axis"]}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(_axis_card_body(selected_ax), unsafe_allow_html=True)

    # ── 改修指示 ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:20px 0 16px">改修指示</div>',
        unsafe_allow_html=True,
    )

    copy_sets = selected_ax.get("copy_sets", [])

    if copy_sets:
        # ══════════════════════════════════════════════════
        # セット形式フロー: ①セット選択 → ②パーツ選択 → ③修正方法
        # ══════════════════════════════════════════════════

        # ① セットの選択
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:8px">'
            '① セットの選択</div>',
            unsafe_allow_html=True,
        )
        set_labels = [f"セット {i + 1}" for i in range(len(copy_sets))]
        set_sel = st.radio(
            "セットの選択",
            set_labels,
            horizontal=True,
            label_visibility="collapsed",
            key="refine_set_select",
        )
        set_idx  = set_labels.index(set_sel)
        sel_set  = copy_sets[set_idx]
        _sc      = _SET_COLORS[set_idx % len(_SET_COLORS)]

        feat_pills_prev = "".join(
            f'<span style="display:inline-block;background:rgba(139,92,246,0.12);color:#c4b5fd;'
            f'border:1px solid rgba(139,92,246,0.35);border-radius:14px;padding:3px 10px;'
            f'font-size:0.77rem;margin:2px 3px 2px 0">{f}</span>'
            for f in sel_set.get("features", [])
        )
        _lbl_r = (
            f'font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;'
            f'letter-spacing:0.1em;flex-shrink:0;width:68px'
        )
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);'
            f'border-left:3px solid {_sc};border-radius:10px;padding:12px 16px;margin:10px 0 20px">'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl_r}">メインキャッチ</span>'
            f'<span style="background:rgba(59,130,246,0.15);color:#93c5fd;'
            f'border:1px solid rgba(59,130,246,0.4);border-radius:14px;'
            f'padding:3px 12px;font-size:0.82rem;font-weight:600">{sel_set.get("headline","")}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl_r}">サブキャッチ</span>'
            f'<span style="background:rgba(99,102,241,0.12);color:#a5b4fc;'
            f'border:1px solid rgba(99,102,241,0.35);border-radius:14px;'
            f'padding:3px 12px;font-size:0.8rem">{sel_set.get("sub_headline","")}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
            f'<span style="{_lbl_r};padding-top:5px">特徴</span>'
            f'<div style="flex:1">{feat_pills_prev}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px">'
            f'<span style="{_lbl_r}">CTA</span>'
            f'<span style="background:rgba(16,185,129,0.12);color:#6ee7b7;'
            f'border:1px solid rgba(16,185,129,0.35);border-radius:14px;'
            f'padding:3px 12px;font-size:0.8rem">{sel_set.get("offer","")}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ② パーツの選択
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:8px">'
            '② パーツの選択</div>',
            unsafe_allow_html=True,
        )
        PART_MAP = {"メインキャッチ": "headline", "サブキャッチ": "sub_headline", "特徴": "features", "CTA": "offer"}
        part_label = st.radio(
            "パーツの選択",
            list(PART_MAP.keys()),
            horizontal=True,
            label_visibility="collapsed",
            key="refine_part_select",
        )
        part_key      = PART_MAP[part_label]
        current_value = sel_set.get(part_key, [] if part_key == "features" else "")

        # ③ 修正方法
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:16px 0 8px">'
            '③ 修正方法</div>',
            unsafe_allow_html=True,
        )
        refine_method = st.radio(
            "修正方法",
            ["手動で修正", "AIで修正"],
            horizontal=True,
            label_visibility="collapsed",
            key="refine_method",
        )

        if refine_method == "手動で修正":
            if part_key == "features":
                edited_text = st.text_area(
                    "特徴（1行1つ）",
                    value="\n".join(current_value),
                    height=110,
                    key="manual_feat_edit",
                    label_visibility="collapsed",
                )
                if st.button("上書き保存", type="primary", use_container_width=True,
                             key="manual_feat_save"):
                    new_feats = [f.strip() for f in edited_text.split("\n") if f.strip()]
                    new_sets = [{**s} for s in copy_sets]
                    new_sets[set_idx]["features"] = new_feats
                    new_ax = {**selected_ax, "copy_sets": new_sets}
                    delete_axis(selected_ax["id"])
                    add_axis(selected_ax.get("product_name", ""),
                             selected_ax.get("product_url", ""),
                             new_ax, selected_ax.get("product_context", {}))
                    st.success("上書き保存しました")
                    st.rerun()
            else:
                edited = st.text_area(
                    part_label, value=current_value, height=68,
                    key="manual_single_edit", label_visibility="collapsed",
                )
                if st.button("上書き保存", type="primary", use_container_width=True,
                             key="manual_single_save"):
                    new_sets = [{**s} for s in copy_sets]
                    new_sets[set_idx][part_key] = edited.strip()
                    new_ax = {**selected_ax, "copy_sets": new_sets}
                    delete_axis(selected_ax["id"])
                    add_axis(selected_ax.get("product_name", ""),
                             selected_ax.get("product_url", ""),
                             new_ax, selected_ax.get("product_context", {}))
                    st.success("上書き保存しました")
                    st.rerun()

        else:  # AIで修正
            revision_instructions = st.text_area(
                "修正指示",
                placeholder="例: もっと感情的に訴えるコピーにして / 価格訴求を前面に出して",
                height=90,
                label_visibility="collapsed",
                key="refine_instructions",
            )
            flat_key     = {"headline": "headlines", "sub_headline": "sub_headlines", "features": "features", "offer": "offers"}[part_key]
            target_items = current_value if part_key == "features" else [current_value]

            if st.button("AIで磨きこむ", type="primary", use_container_width=True,
                         key="refine_submit"):
                if not revision_instructions.strip():
                    st.error("修正指示を入力してください")
                else:
                    with st.spinner(f"「{part_label}」を改修中..."):
                        try:
                            new_items = refine_copy_part(
                                selected_ax, flat_key, target_items, revision_instructions
                            )
                            if part_key == "features":
                                new_value = new_items
                            else:
                                orig_vals = {cs.get(part_key, "") for cs in copy_sets}
                                changed   = [v for v in new_items if v not in orig_vals]
                                new_value = changed[0] if changed else (
                                    new_items[set_idx] if set_idx < len(new_items) else current_value
                                )
                            st.session_state["refine_result"] = {
                                "set_idx":   set_idx,
                                "part_key":  part_key,
                                "part_label": part_label,
                                "new_value": new_value,
                                "original":  current_value,
                                "source_id": selected_ax["id"],
                            }
                            st.rerun()
                        except Exception as e:
                            st.error(f"改修エラー: {e}")

        # ── 改修結果の表示 ────────────────────────────────────────────────────
        refine_result = st.session_state.get("refine_result", {})
        if refine_result and refine_result.get("source_id") == selected_ax["id"]:
            r_set_idx    = refine_result["set_idx"]
            r_part_key   = refine_result["part_key"]
            r_part_label = refine_result.get("part_label", r_part_key)
            r_new_value  = refine_result["new_value"]
            r_original   = refine_result["original"]

            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#10b981;text-transform:uppercase;'
                f'letter-spacing:0.1em;margin:24px 0 10px">改修後'
                f'<span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.5);'
                f'border-radius:4px;padding:2px 8px;margin-left:8px;font-size:0.65rem;'
                f'text-transform:none;letter-spacing:0">'
                f'セット{r_set_idx + 1}「{r_part_label}」を改修</span></div>',
                unsafe_allow_html=True,
            )

            def _disp(val, bg, color, border):
                if isinstance(val, list):
                    return "".join(
                        f'<span style="display:inline-block;background:{bg};color:{color};'
                        f'border:1px solid {border};border-radius:14px;'
                        f'padding:3px 10px;font-size:0.8rem;margin:2px 3px 2px 0">{v}</span>'
                        for v in val
                    )
                return (
                    f'<span style="background:{bg};color:{color};border:1px solid {border};'
                    f'border-radius:14px;padding:3px 14px;font-size:0.85rem;font-weight:600">{val}</span>'
                )

            color_r = BADGE_COLORS[2]
            glow_r  = BADGE_GLOWS[2]
            st.markdown(
                f"<style>[data-testid='stVerticalBlockBorderWrapper']:has(.refine-result){{"
                f"border-left:4px solid {color_r} !important;border-radius:16px !important;"
                f"box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 12px {glow_r} !important;"
                f"}}</style>",
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.markdown('<div class="refine-result" style="display:none"></div>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:0.67rem;font-weight:700;color:#64748b;'
                    'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">修正前</div>'
                    + _disp(r_original, "rgba(255,255,255,0.04)", "#64748b", "#334155")
                    + '<div style="font-size:0.67rem;font-weight:700;color:#10b981;'
                    'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 6px">修正後</div>'
                    + _disp(r_new_value, "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.5)"),
                    unsafe_allow_html=True,
                )

            col_overwrite, col_discard = st.columns([3, 1])
            with col_overwrite:
                if st.button("上書き保存", type="primary", use_container_width=True,
                             key="ai_overwrite"):
                    new_sets = [{**s} for s in copy_sets]
                    new_sets[r_set_idx][r_part_key] = r_new_value
                    new_ax = {**selected_ax, "copy_sets": new_sets}
                    delete_axis(selected_ax["id"])
                    add_axis(selected_ax.get("product_name", ""),
                             selected_ax.get("product_url", ""),
                             new_ax, selected_ax.get("product_context", {}))
                    del st.session_state["refine_result"]
                    st.success("上書き保存しました")
                    st.rerun()
            with col_discard:
                if st.button("破棄", type="secondary", use_container_width=True,
                             key="ai_discard"):
                    del st.session_state["refine_result"]
                    st.rerun()

    else:
        # ── 旧形式フォールバック（copy_sets なし）──────────────────────────────
        _cs = selected_ax.get("copy_suggestions", {})
        OLD_PARTS = {
            "キャッチコピー": "headlines",
            "オファー・CTA":  "offers",
            "特徴・アイコン": "features",
        }

        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:6px">'
            '① パーツの選択</div>',
            unsafe_allow_html=True,
        )
        target_part_label = st.selectbox(
            "パーツの選択", list(OLD_PARTS.keys()),
            label_visibility="collapsed", key="refine_part_select",
        )
        part_key      = OLD_PARTS[target_part_label]
        current_items = _cs.get(part_key, [])

        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:16px 0 6px">'
            '② 具体パーツの選択</div>',
            unsafe_allow_html=True,
        )
        if not current_items:
            st.caption("このパーツにコピー候補がありません")
            target_items = []
        elif part_key == "features":
            target_items = st.multiselect(
                "修正する項目（複数可）", options=current_items,
                default=current_items[:1] if current_items else [],
                label_visibility="collapsed", key="refine_items_multi",
            )
        else:
            selected_item = st.radio(
                "修正する項目", options=current_items,
                label_visibility="collapsed", key="refine_items_radio",
            )
            target_items = [selected_item] if selected_item else []

        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:16px 0 6px">'
            '③ 修正方法</div>',
            unsafe_allow_html=True,
        )
        if not target_items:
            st.caption("② で修正する項目を選択してください")
        else:
            refine_method = st.radio(
                "修正方法", ["手動で修正", "AIで修正"],
                horizontal=True, label_visibility="collapsed", key="refine_method",
            )
            if refine_method == "手動で修正":
                edited_map = {}
                for idx, item in enumerate(target_items):
                    edited = st.text_area(
                        f"手動編集 {idx + 1}", value=item, height=68,
                        key=f"manual_edit_{idx}", label_visibility="collapsed",
                    )
                    edited_map[item] = edited
                if st.button("上書き保存", type="primary", use_container_width=True,
                             key="manual_save"):
                    new_list = list(current_items)
                    for orig, edited_val in edited_map.items():
                        if orig in new_list:
                            new_list[new_list.index(orig)] = edited_val
                    refined_manual = {**selected_ax, "copy_suggestions": {**_cs, part_key: new_list}}
                    delete_axis(selected_ax["id"])
                    add_axis(selected_ax.get("product_name", ""),
                             selected_ax.get("product_url", ""),
                             refined_manual, selected_ax.get("product_context", {}))
                    st.success("上書き保存しました")
                    st.rerun()
            else:
                revision_instructions = st.text_area(
                    "修正指示",
                    placeholder="例: もっと感情的に訴えるコピーにして / 価格訴求を前面に出して",
                    height=90, label_visibility="collapsed", key="refine_instructions",
                )
                if st.button("AIで磨きこむ", type="primary", use_container_width=True,
                             key="refine_submit"):
                    if not revision_instructions.strip():
                        st.error("修正指示を入力してください")
                    else:
                        with st.spinner(f"「{target_part_label}」を改修中..."):
                            try:
                                new_items = refine_copy_part(
                                    selected_ax, part_key, target_items, revision_instructions
                                )
                                refined_ai = {**selected_ax,
                                              "copy_suggestions": {**_cs, part_key: new_items}}
                                st.session_state["refined_axis"]           = refined_ai
                                st.session_state["refined_part_label"]     = target_part_label
                                st.session_state["refined_part_key"]       = part_key
                                st.session_state["refined_source_id"]      = selected_ax["id"]
                                st.session_state["refined_target_items"]   = list(target_items)
                                st.session_state["refined_original_items"] = list(
                                    _cs.get(part_key, []))
                                st.rerun()
                            except Exception as e:
                                st.error(f"改修エラー: {e}")

            if "refined_axis" in st.session_state:
                refined   = st.session_state["refined_axis"]
                source_id = st.session_state.get("refined_source_id")
                p_name    = refined.get("product_name", "")
                p_url     = refined.get("product_url", "")
                p_ctx     = refined.get("product_context", {})

                part_label_display = st.session_state.get("refined_part_label", "")
                st.markdown(
                    f'<div style="font-size:0.72rem;font-weight:700;color:#10b981;'
                    f'text-transform:uppercase;letter-spacing:0.1em;margin:24px 0 10px">改修後の訴求軸'
                    f'<span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.5);'
                    f'border-radius:4px;padding:2px 8px;margin-left:8px;font-size:0.65rem;'
                    f'text-transform:none;letter-spacing:0">「{part_label_display}」を改修</span></div>',
                    unsafe_allow_html=True,
                )
                color_r = BADGE_COLORS[2]
                glow_r  = BADGE_GLOWS[2]
                st.markdown(
                    f"<style>[data-testid='stVerticalBlockBorderWrapper']:has(.refine-result){{"
                    f"border-left:4px solid {color_r} !important;border-radius:16px !important;"
                    f"box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 12px {glow_r} !important;"
                    f"}}</style>",
                    unsafe_allow_html=True,
                )
                part_key_r     = st.session_state.get("refined_part_key", "")
                target_items_r = st.session_state.get("refined_target_items", [])
                original_set   = set(st.session_state.get("refined_original_items", []))
                all_new_items  = refined.get("copy_suggestions", {}).get(part_key_r, [])
                changed_items  = [item for item in all_new_items if item not in original_set]

                with st.container(border=True):
                    st.markdown('<div class="refine-result" style="display:none"></div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<span style="font-size:0.85rem;color:#64748b">{refined.get("axis","")}</span>',
                        unsafe_allow_html=True,
                    )
                    if target_items_r:
                        st.markdown(
                            '<div style="font-size:0.67rem;font-weight:700;color:#64748b;'
                            'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 6px">修正前</div>'
                            + _pills(target_items_r, "rgba(255,255,255,0.04)", "#64748b", "#334155"),
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        '<div style="font-size:0.67rem;font-weight:700;color:#10b981;'
                        'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 6px">修正後</div>'
                        + _pills(changed_items or all_new_items[:len(target_items_r)],
                                 "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.5)"),
                        unsafe_allow_html=True,
                    )

                col_overwrite, col_discard = st.columns([3, 1])
                with col_overwrite:
                    if st.button("上書き保存", type="primary", use_container_width=True,
                                 key="ai_overwrite"):
                        delete_axis(source_id)
                        add_axis(p_name, p_url, refined, p_ctx)
                        del st.session_state["refined_axis"]
                        st.success("上書き保存しました")
                        st.rerun()
                with col_discard:
                    if st.button("破棄", type="secondary", use_container_width=True,
                                 key="ai_discard"):
                        del st.session_state["refined_axis"]
                        st.rerun()
