"""Page: 保存済み訴求軸"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import delete_axis, load_axes

# ── Copy helpers (same as analysis.py) ───────────────────────────────────────

_SET_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899"]


def _pills(items: list, bg: str, color: str, border: str) -> str:
    return "".join(
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'border:1px solid {border};border-radius:20px;padding:5px 13px;'
        f'font-size:0.8rem;margin:3px 4px 3px 0;line-height:1.3;font-weight:500">{item}</span>'
        for item in items
    )


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


def _copy_flat_html(copy_s: dict) -> str:
    """Fallback for old-format axes without copy_sets."""
    def _section(label, items, bg, color, border):
        if not items:
            return ""
        return (
            f'<div style="margin-bottom:8px">'
            f'<div style="font-size:0.67rem;font-weight:700;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-bottom:5px">{label}</div>'
            f'{_pills(items, bg, color, border)}'
            f'</div>'
        )
    sections = (
        _section("キャッチコピー", copy_s.get("headlines", []),
                 "rgba(59,130,246,0.15)", "#93c5fd", "rgba(59,130,246,0.4)") +
        _section("オファー・CTA", copy_s.get("offers", []),
                 "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.4)") +
        _section("特徴・アイコン", copy_s.get("features", []),
                 "rgba(139,92,246,0.15)", "#c4b5fd", "rgba(139,92,246,0.4)")
    )
    if not sections:
        return ""
    return (
        f'<div style="border-top:1px solid #334155;margin-top:14px;padding-top:14px">'
        f'{sections}</div>'
    )


def _axis_card_body(ax: dict) -> str:
    copy_html = (
        _copy_sets_html(ax["copy_sets"])
        if ax.get("copy_sets")
        else _copy_flat_html(ax.get("copy_suggestions", {}))
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
        f'<span style="color:#64748b;font-weight:600">📦 商品</span>'
        f'<span style="color:#cbd5e1;margin-left:5px">{ax.get("product_name","—")}</span>'
        f'</div>'
        f'<div style="background:rgba(255,255,255,0.05);border:1px solid #334155;'
        f'border-radius:8px;padding:4px 11px;font-size:0.76rem;color:#64748b">'
        f'{ax.get("created_at","")[:10]}'
        f'</div></div>'
        f'{copy_html}'
    )


# ── Page header ───────────────────────────────────────────────────────────────

BADGE_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"]
BADGE_GLOWS  = [
    "rgba(59,130,246,0.35)", "rgba(139,92,246,0.35)",
    "rgba(236,72,153,0.35)", "rgba(245,158,11,0.35)", "rgba(16,185,129,0.35)",
]

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

# ── Axis cards ────────────────────────────────────────────────────────────────

for idx, ax in enumerate(reversed(saved_axes)):
    color  = BADGE_COLORS[idx % len(BADGE_COLORS)]
    glow   = BADGE_GLOWS[idx % len(BADGE_GLOWS)]
    marker = f"saved-axis-{idx}"

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

        col_title, col_del = st.columns([9, 1])
        with col_title:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px">'
                f'<div style="display:inline-flex;align-items:center;justify-content:center;'
                f'width:28px;height:28px;border-radius:50%;background:{color};'
                f'color:white;font-weight:800;font-size:12px;flex-shrink:0;'
                f'box-shadow:0 2px 8px {glow}">{idx + 1}</div>'
                f'<span style="font-size:1.0rem;font-weight:800;color:#f1f5f9;'
                f'letter-spacing:-0.01em">{ax["axis"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("🗑", key=f"del_axis_{ax['id']}", type="secondary",
                         use_container_width=True, help="削除"):
                delete_axis(ax["id"])
                st.rerun()

        st.markdown(_axis_card_body(ax), unsafe_allow_html=True)
