"""Page 4: 保存済みバナー"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_banners, delete_banner

st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#064e3b 60%,#065f46 100%);'
    'padding:28px 32px;border-radius:18px;margin-bottom:24px;'
    'border:1px solid rgba(16,185,129,0.3);'
    'box-shadow:0 8px 32px rgba(16,185,129,0.15),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<h1 style="color:#e2e8f0;margin:0 0 8px;font-size:1.8rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">保存済みバナー</h1>'
    '<p style="color:#6ee7b7;margin:0;font-size:0.875rem;line-height:1.6">'
    'これまでに生成・保存したバナー画像の一覧です</p>'
    '</div>',
    unsafe_allow_html=True,
)

banners = load_banners()

if not banners:
    st.markdown(
        '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
        'border-radius:14px;padding:60px;text-align:center">'
        '<div style="font-size:3rem;margin-bottom:16px">🖼️</div>'
        '<div style="color:#f1f5f9;font-size:1.05rem;font-weight:700;margin-bottom:8px">'
        'まだバナーが保存されていません</div>'
        '<div style="color:#64748b;font-size:0.875rem;margin-bottom:24px">'
        '「バナー生成」ページで画像を生成すると、ここに表示されます</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("バナー生成ページへ →", type="primary"):
        st.switch_page("pages/banner.py")
    st.stop()

banners_sorted = sorted(banners, key=lambda b: b["created_at"], reverse=True)

st.markdown(
    f'<p style="color:#475569;font-size:0.82rem;margin-bottom:20px">'
    f'<span style="color:#10b981;font-weight:700">{len(banners_sorted)}</span>'
    f' 件のバナーが保存されています</p>',
    unsafe_allow_html=True,
)

# ── 3-column grid ─────────────────────────────────────────────────────────────

COLS = 3
rows = [banners_sorted[i:i + COLS] for i in range(0, len(banners_sorted), COLS)]

for row in rows:
    cols = st.columns(COLS)
    for col, banner in zip(cols, row):
        with col:
            platforms = banner.get("platforms", [])
            first_url = platforms[0].get("public_url", "") if platforms else ""

            # DL リンク HTML
            if len(platforms) > 1:
                dl_html = "↓ " + " · ".join(
                    f'<a href="{p["public_url"]}?download={p.get("filename","banner.png")}" '
                    f'target="_blank" style="color:#3b82f6;font-size:0.72rem;font-weight:600;'
                    f'text-decoration:none">{p.get("platform_name","").replace("_"," ")}</a>'
                    for p in platforms if p.get("public_url")
                )
            elif first_url:
                fname = platforms[0].get("filename", "banner.png")
                dl_html = (
                    f'<a href="{first_url}?download={fname}" target="_blank" '
                    f'style="color:#3b82f6;font-size:0.72rem;font-weight:600;text-decoration:none">'
                    f'↓ ダウンロード</a>'
                )
            else:
                dl_html = ""

            # Image zone — clicking anywhere opens the image full-size in a new tab
            # The "⛶ 拡大" badge overlaid at top-right makes it discoverable
            if first_url:
                img_section = (
                    f'<a href="{first_url}" target="_blank" '
                    f'style="display:block;text-decoration:none;'
                    f'position:relative;height:220px;flex-shrink:0;overflow:hidden">'
                    f'<img src="{first_url}" '
                    f'style="width:100%;height:100%;object-fit:cover;display:block">'
                    f'<div style="position:absolute;top:8px;right:8px;'
                    f'background:rgba(15,23,42,0.82);backdrop-filter:blur(6px);'
                    f'-webkit-backdrop-filter:blur(6px);'
                    f'color:#f1f5f9;border:1px solid rgba(255,255,255,0.22);'
                    f'border-radius:6px;padding:5px 11px;'
                    f'font-size:0.7rem;font-weight:700;letter-spacing:0.04em;'
                    f'pointer-events:none">⛶ 拡大</div>'
                    f'</a>'
                )
            else:
                img_section = (
                    '<div style="height:220px;flex-shrink:0;display:flex;align-items:center;'
                    'justify-content:center;color:#475569;font-size:0.78rem">No image</div>'
                )

            st.markdown(
                f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;'
                f'overflow:hidden;height:320px;display:flex;flex-direction:column;'
                f'margin-bottom:8px">'
                f'{img_section}'
                f'<div style="padding:10px 12px;flex:1;overflow:hidden;display:flex;'
                f'flex-direction:column;gap:4px">'
                f'<div style="font-weight:700;font-size:0.8rem;color:#e2e8f0;'
                f'overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;'
                f'-webkit-box-orient:vertical;line-height:1.4">'
                f'[{banner["variation"]}] {banner["label"]}</div>'
                f'<div style="color:#64748b;font-size:0.72rem;flex-shrink:0">'
                f'{banner.get("axis","—")} · {banner["created_at"][:10]}</div>'
                f'<div style="margin-top:auto;flex-shrink:0">{dl_html}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("🗑 削除", key=f"del_banner_{banner['id']}", type="secondary",
                         use_container_width=True):
                delete_banner(banner["id"])
                st.rerun()

    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
