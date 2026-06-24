"""Page 3: 保存済み訴求軸"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_axes, delete_axis


def _pills(items: list, bg: str, color: str, border: str) -> str:
    return "".join(
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'border:1px solid {border};border-radius:20px;padding:4px 12px;'
        f'font-size:0.78rem;margin:3px 4px 3px 0;line-height:1.3;font-weight:500">{item}</span>'
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


st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e3a5f 60%,#0f4c75 100%);'
    'padding:28px 32px;border-radius:18px;margin-bottom:24px;'
    'border:1px solid rgba(59,130,246,0.25);'
    'box-shadow:0 8px 32px rgba(15,75,117,0.3),inset 0 1px 0 rgba(255,255,255,0.06)">'
    '<h1 style="color:#e2e8f0;margin:0 0 8px;font-size:1.8rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">保存済み訴求軸</h1>'
    '<p style="color:#7dd3fc;margin:0;font-size:0.875rem;line-height:1.6">'
    '「バナー生成」ページで使用する訴求軸を管理します</p>'
    '</div>',
    unsafe_allow_html=True,
)

saved_axes = load_axes()

# CTA: proceed to banner generation
if saved_axes:
    col_cta, col_refine, _ = st.columns([2, 2, 3])
    with col_cta:
        if st.button("バナー生成へ進む →", type="primary", use_container_width=True, key="goto_banner"):
            st.switch_page("pages/banner.py")
    with col_refine:
        if st.button("訴求軸を磨きこむ →", type="secondary", use_container_width=True, key="goto_refine"):
            st.switch_page("pages/analysis.py")
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

if not saved_axes:
    st.markdown(
        '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
        'border-radius:14px;padding:56px;text-align:center">'
        '<div style="font-size:2.8rem;margin-bottom:14px">🎯</div>'
        '<div style="color:#e2e8f0;font-size:1.05rem;font-weight:700;margin-bottom:8px">'
        '保存済みの訴求軸がありません</div>'
        '<div style="color:#64748b;font-size:0.85rem;margin-bottom:20px">'
        '「訴求軸の検討」ページで3C分析を実施し、「＋ 追加」を押して保存してください</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("訴求軸生成ページへ →", type="primary"):
        st.switch_page("pages/analysis.py")
    st.stop()

st.markdown(
    f'<p style="color:#475569;font-size:0.82rem;margin-bottom:16px">'
    f'<span style="color:#3b82f6;font-weight:700">{len(saved_axes)}</span>'
    f' 件の訴求軸が保存されています</p>',
    unsafe_allow_html=True,
)

BADGE_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
BADGE_GLOWS  = [
    "rgba(59,130,246,0.3)", "rgba(139,92,246,0.3)",
    "rgba(236,72,153,0.3)", "rgba(245,158,11,0.3)", "rgba(16,185,129,0.3)",
]

for idx, ax in enumerate(reversed(saved_axes)):
    color  = BADGE_COLORS[idx % len(BADGE_COLORS)]
    glow   = BADGE_GLOWS[idx % len(BADGE_GLOWS)]
    copy_s = ax.get("copy_suggestions", {})
    marker = f"saved-axis-{idx}"

    # Build copy pills inline (no blank lines — blank lines in markdown = code blocks)
    sections = (
        _copy_section("キャッチコピー", copy_s.get("headlines", []),
                      "rgba(59,130,246,0.12)", "#93c5fd", "rgba(59,130,246,0.35)") +
        _copy_section("オファー・CTA", copy_s.get("offers", []),
                      "rgba(16,185,129,0.12)", "#6ee7b7", "rgba(16,185,129,0.35)") +
        _copy_section("特徴・アイコン", copy_s.get("features", []),
                      "rgba(139,92,246,0.12)", "#c4b5fd", "rgba(139,92,246,0.35)")
    ) if copy_s else ""
    copy_html = (
        f'<div style="border-top:1px solid #334155;margin-top:12px;padding-top:12px">{sections}</div>'
        if sections else ""
    )

    # Per-card CSS: colored left border + glow on expander
    st.markdown(
        f"<style>[data-testid='stExpander']:has(.{marker}){{"
        f"border-left:4px solid {color} !important;"
        f"box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 12px {glow} !important;"
        f"}}</style>",
        unsafe_allow_html=True,
    )

    with st.expander(f"[{idx+1}]  {ax['axis']}", expanded=False):
        st.markdown(f'<div class="{marker}" style="display:none"></div>',
                    unsafe_allow_html=True)

        # Meta tags
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px">'
            f'<span style="background:rgba(255,255,255,0.05);border:1px solid #334155;'
            f'border-radius:6px;padding:2px 9px;font-size:0.73rem;color:#64748b">'
            f'📦 {ax.get("product_name","")}</span>'
            f'<span style="background:rgba(255,255,255,0.05);border:1px solid #334155;'
            f'border-radius:6px;padding:2px 9px;font-size:0.73rem;color:#64748b">'
            f'{ax.get("created_at","")[:10]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Description + target + pills
        st.markdown(
            f'<p style="color:#94a3b8;font-size:0.85rem;line-height:1.6;margin:0 0 8px">'
            f'{ax.get("description","")}</p>'
            f'<div style="background:rgba(255,255,255,0.04);border:1px solid #334155;'
            f'border-radius:8px;padding:5px 11px;font-size:0.76rem;display:inline-block;margin-bottom:4px">'
            f'<span style="color:#64748b;font-weight:600">🎯 ターゲット</span>'
            f'<span style="color:#cbd5e1;margin-left:5px">{ax.get("target_segment","—")}</span>'
            f'</div>'
            f'{copy_html}',
            unsafe_allow_html=True,
        )

        _, col_del = st.columns([8, 2])
        with col_del:
            if st.button("🗑 削除", key=f"del_axis_{ax['id']}", type="secondary",
                         use_container_width=True):
                delete_axis(ax["id"])
                st.rerun()
