"""Page 1: ターゲットと訴求軸の検討エージェント"""

import os
import re
import sys
import urllib.request

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import analyze_product, generate_more_axes, refine_copy_part
from state import add_axis, delete_axis, load_axes


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


def _c3_card(title: str, color: str, gradient: str, icon: str, items: list) -> str:
    rows = "".join(
        f"""<div style="margin-bottom:14px">
            <div style="font-size:0.7rem;font-weight:700;color:{color};
                 text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">{label}</div>
            <div style="color:#cbd5e1;font-size:0.875rem;line-height:1.6">{value}</div>
        </div>"""
        for label, value in items
    )
    return (
        f'<div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:14px;'
        f'padding:22px 24px;border-top:3px solid {color};'
        f'box-shadow:0 4px 24px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.04)">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">'
        f'<div style="background:{gradient};width:36px;height:36px;border-radius:10px;'
        f'display:flex;align-items:center;justify-content:center;font-size:1.1rem;'
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


def _axis_card_body(ax: dict) -> str:
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
        f'{_copy_html(ax.get("copy_suggestions", {}))}'
    )


BADGE_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
BADGE_GLOWS  = [
    "rgba(59,130,246,0.35)", "rgba(139,92,246,0.35)",
    "rgba(236,72,153,0.35)", "rgba(245,158,11,0.35)", "rgba(16,185,129,0.35)",
]

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e3a8a 60%,#1d4ed8 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:28px;'
    'border:1px solid rgba(59,130,246,0.3);'
    'box-shadow:0 8px 32px rgba(37,99,235,0.25),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
    '<div style="background:rgba(59,130,246,0.25);border:1px solid rgba(59,130,246,0.4);'
    'border-radius:8px;padding:3px 10px;font-size:0.72rem;font-weight:700;'
    'color:#93c5fd;letter-spacing:0.1em;text-transform:uppercase">Step 1 / 2</div>'
    '</div>'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">訴求軸の検討</h1>'
    '<p style="color:#93c5fd;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    '商品URLをもとに Claude が 3C 分析を実施し、SNS広告の最適な訴求軸とコピー候補を提案します'
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

# ══════════════════════════════════════════════════════════════════════════════
# MODE A: 新規作成
# ══════════════════════════════════════════════════════════════════════════════
if mode == "新規作成":

    with st.form("analysis_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("商品名 *", placeholder="例: Craftin for Company")
        with col2:
            product_url = st.text_input("商品URL *", placeholder="https://example.com/product")
        competitor_url = st.text_input(
            "競合商品URL（任意）",
            placeholder="空欄の場合は Claude が自動でリサーチします",
        )
        submitted = st.form_submit_button(
            "3C分析・訴求軸を生成",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not product_name or not product_url:
            st.error("商品名と商品URLは必須です")
            st.stop()

        with st.status("分析中...", expanded=True) as status:
            st.write("自社ページを取得中...")
            page_content = _fetch_page_content(product_url)
            st.write(
                f"✓ 取得完了（{len(page_content)} 文字）"
                if page_content else "⚠ ページ取得失敗（URL情報のみで分析）"
            )

            competitor_content = ""
            if competitor_url.strip():
                st.write("競合ページを取得中...")
                competitor_content = _fetch_page_content(competitor_url.strip())
                st.write(
                    f"✓ 競合ページ取得完了（{len(competitor_content)} 文字）"
                    if competitor_content else "⚠ 競合ページ取得失敗"
                )
            else:
                st.write("競合URLなし → Claude が自動リサーチします")

            st.write("Claude が3C分析・訴求軸を生成中...")
            try:
                analysis = analyze_product(
                    product_name, product_url, page_content,
                    competitor_url=competitor_url.strip(),
                    competitor_content=competitor_content,
                )
            except Exception as e:
                err = str(e)
                if "overloaded" in err or "529" in err:
                    st.error("Anthropic API が一時的に混雑しています。少し待ってから再度お試しください。")
                else:
                    st.error(f"分析エラー: {e}")
                st.stop()

            status.update(label="分析完了！", state="complete", expanded=False)

        st.session_state["analysis"] = analysis
        st.session_state["analysis_product_name"] = product_name
        st.session_state["analysis_product_url"] = product_url

    if "analysis" in st.session_state:
        analysis = st.session_state["analysis"]
        product_name_s = st.session_state.get("analysis_product_name", "")
        product_url_s  = st.session_state.get("analysis_product_url", "")
        c3   = analysis.get("3c_analysis", {})
        cust = c3.get("customer", {})
        comp = c3.get("competitor", {})
        co   = c3.get("company", {})

        st.markdown(
            '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
            'letter-spacing:0.1em;margin:8px 0 14px">3C 分析結果</div>',
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

        st.markdown(
            '<div style="margin-top:36px;margin-bottom:16px">'
            '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:6px">提案訴求軸</div>'
            '<p style="color:#64748b;font-size:0.82rem;margin:0">'
            '「＋ 追加」でバナー生成ページから使用できるようになります'
            '</p></div>',
            unsafe_allow_html=True,
        )

        current_axes = analysis.get("appeal_axes", [])
        saved_axis_names = {a["axis"] for a in load_axes()}
        product_context = {
            "value_proposition": co.get("value_proposition",""),
            "strengths": co.get("strengths",""),
            "customer_needs": cust.get("needs",""),
            "pain_points": cust.get("pain_points",""),
            "differentiation": comp.get("differentiation",""),
        }

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

        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        with st.expander("＋ さらに訴求軸を追加する"):
            add_angle = st.text_input(
                "追加で検討したい観点",
                placeholder="例: 季節訴求、価格訴求、BtoB向けなど",
                key="add_angle_input",
            )
            if st.button("追加訴求軸を生成", key="gen_more_btn", type="primary"):
                with st.spinner("訴求軸を生成中..."):
                    try:
                        new_axes = generate_more_axes(product_name_s, current_axes, add_angle)
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
        st.info("保存済みの訴求軸がありません。まず「新規作成」で訴求軸を生成・保存してください。")
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

    # ── 改修指示（3ステップ）────────────────────────────────────────────────
    PART_OPTIONS = {
        "キャッチコピー": "headlines",
        "オファー・CTA":  "offers",
        "特徴・アイコン": "features",
    }

    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:20px 0 16px">改修指示</div>',
        unsafe_allow_html=True,
    )

    # ① パーツの選択
    st.markdown(
        '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:6px">'
        '① パーツの選択</div>',
        unsafe_allow_html=True,
    )
    target_part_label = st.selectbox(
        "パーツの選択",
        list(PART_OPTIONS.keys()),
        label_visibility="collapsed",
        key="refine_part_select",
    )
    part_key      = PART_OPTIONS[target_part_label]
    current_items = selected_ax.get("copy_suggestions", {}).get(part_key, [])

    # ② 具体パーツの選択
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
            "修正する項目（複数可）",
            options=current_items,
            default=current_items[:1] if current_items else [],
            label_visibility="collapsed",
            key="refine_items_multi",
        )
    else:
        selected_item = st.radio(
            "修正する項目",
            options=current_items,
            label_visibility="collapsed",
            key="refine_items_radio",
        )
        target_items = [selected_item] if selected_item else []

    # ③ 修正方法
    st.markdown(
        '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:16px 0 6px">'
        '③ 修正方法</div>',
        unsafe_allow_html=True,
    )

    if not target_items:
        st.caption("② で修正する項目を選択してください")
    else:
        refine_method = st.radio(
            "修正方法",
            ["手動で修正", "AIで修正"],
            horizontal=True,
            label_visibility="collapsed",
            key="refine_method",
        )

        if refine_method == "手動で修正":
            edited_map = {}
            for idx, item in enumerate(target_items):
                edited = st.text_area(
                    f"手動編集 {idx + 1}",
                    value=item,
                    height=68,
                    key=f"manual_edit_{idx}",
                    label_visibility="collapsed",
                )
                edited_map[item] = edited
            if st.button("上書き保存", type="primary", use_container_width=True, key="manual_save"):
                new_list = list(current_items)
                for orig, edited_val in edited_map.items():
                    if orig in new_list:
                        new_list[new_list.index(orig)] = edited_val
                refined_manual = {**selected_ax}
                refined_manual["copy_suggestions"] = {
                    **selected_ax.get("copy_suggestions", {}), part_key: new_list
                }
                delete_axis(selected_ax["id"])
                add_axis(
                    selected_ax.get("product_name", ""),
                    selected_ax.get("product_url", ""),
                    refined_manual,
                    selected_ax.get("product_context", {}),
                )
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
            if st.button("AIで磨きこむ", type="primary", use_container_width=True, key="refine_submit"):
                if not revision_instructions.strip():
                    st.error("修正指示を入力してください")
                else:
                    with st.spinner(f"「{target_part_label}」を改修中..."):
                        try:
                            new_items = refine_copy_part(
                                selected_ax, part_key, target_items, revision_instructions
                            )
                            refined_ai = {**selected_ax}
                            refined_ai["copy_suggestions"] = {
                                **selected_ax.get("copy_suggestions", {}), part_key: new_items
                            }
                            st.session_state["refined_axis"]           = refined_ai
                            st.session_state["refined_part_label"]     = target_part_label
                            st.session_state["refined_part_key"]       = part_key
                            st.session_state["refined_source_id"]      = selected_ax["id"]
                            st.session_state["refined_original_items"] = list(
                                selected_ax.get("copy_suggestions", {}).get(part_key, [])
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"改修エラー: {e}")

    # ── 改修後の訴求軸 ────────────────────────────────────────────────────────
    if "refined_axis" in st.session_state:
        refined   = st.session_state["refined_axis"]
        source_id = st.session_state.get("refined_source_id")
        p_name    = refined.get("product_name", "")
        p_url     = refined.get("product_url", "")
        p_ctx     = refined.get("product_context", {})

        part_label_display = st.session_state.get("refined_part_label", "")
        st.markdown(
            f'<div style="font-size:0.72rem;font-weight:700;color:#10b981;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin:24px 0 10px">改修後の訴求軸'
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
        part_key_r      = st.session_state.get("refined_part_key", "")
        original_items  = st.session_state.get("refined_original_items", [])
        new_items_r     = refined.get("copy_suggestions", {}).get(part_key_r, [])

        with st.container(border=True):
            st.markdown('<div class="refine-result" style="display:none"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<span style="font-size:0.85rem;color:#64748b">{refined.get("axis","")}</span>',
                unsafe_allow_html=True,
            )
            if original_items:
                st.markdown(
                    '<div style="font-size:0.67rem;font-weight:700;color:#64748b;'
                    'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 6px">修正前</div>'
                    + _pills(original_items, "rgba(255,255,255,0.04)", "#64748b", "#334155"),
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<div style="font-size:0.67rem;font-weight:700;color:#10b981;'
                'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 6px">修正後</div>'
                + _pills(new_items_r, "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.5)"),
                unsafe_allow_html=True,
            )

        col_overwrite, col_discard = st.columns([3, 1])
        with col_overwrite:
            if st.button("上書き保存", type="primary", use_container_width=True, key="ai_overwrite"):
                delete_axis(source_id)
                add_axis(p_name, p_url, refined, p_ctx)
                del st.session_state["refined_axis"]
                st.success("上書き保存しました")
                st.rerun()
        with col_discard:
            if st.button("破棄", type="secondary", use_container_width=True, key="ai_discard"):
                del st.session_state["refined_axis"]
                st.rerun()


# ── Footer hint ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.2);'
    'border-radius:10px;padding:12px 18px;margin-top:32px">'
    '<span style="color:#93c5fd;font-size:0.82rem">'
    '📋 追加した訴求軸は <strong>「保存済み訴求軸」</strong> ページで管理できます'
    '</span></div>',
    unsafe_allow_html=True,
)
