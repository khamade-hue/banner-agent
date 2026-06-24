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

# Gallery CSS (hover overlay DL button)
st.markdown(
    '<style>'
    '.bn-gallery{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}'
    '.bn-item{position:relative;width:130px;flex-shrink:0}'
    '.bn-item img{width:100%;height:auto;border-radius:8px;display:block;'
    'border:1px solid #334155}'
    '.bn-overlay{position:absolute;inset:0;background:rgba(0,0,0,0.55);'
    'display:flex;align-items:center;justify-content:center;'
    'border-radius:8px;opacity:0;transition:opacity 0.18s ease}'
    '.bn-item:hover .bn-overlay{opacity:1}'
    '.bn-dl-btn{color:#fff;font-size:0.78rem;font-weight:700;text-decoration:none;'
    'background:rgba(59,130,246,0.75);border:1px solid rgba(99,149,255,0.6);'
    'border-radius:6px;padding:5px 10px}'
    '.bn-dl-btn:hover{background:rgba(59,130,246,0.95)}'
    '</style>',
    unsafe_allow_html=True,
)

for banner in banners_sorted:
    platforms = banner.get("platforms", [])

    # Group header: label + axis + date + delete
    col_info, col_del = st.columns([9, 1])
    with col_info:
        st.markdown(
            f'<div style="margin-bottom:4px">'
            f'<span style="color:#e2e8f0;font-weight:700;font-size:0.85rem">'
            f'[{banner["variation"]}] {banner["label"]}</span>'
            f'<span style="color:#475569;font-size:0.75rem;margin-left:8px">'
            f'{banner.get("axis","—")} · {banner["created_at"][:10]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_del:
        if st.button("🗑", key=f"del_banner_{banner['id']}", type="secondary",
                     use_container_width=True):
            delete_banner(banner["id"])
            st.rerun()

    # Image gallery with hover DL overlay
    if platforms:
        imgs_html = '<div class="bn-gallery">'
        for p in platforms:
            url = p.get("public_url", "")
            if url:
                filename = p.get("filename", "banner.png")
                dl_url = f"{url}?download={filename}"
                imgs_html += (
                    f'<div class="bn-item">'
                    f'<img src="{url}" />'
                    f'<div class="bn-overlay">'
                    f'<a href="{dl_url}" target="_blank" class="bn-dl-btn">↓ DL</a>'
                    f'</div>'
                    f'</div>'
                )
        imgs_html += '</div>'
        st.markdown(imgs_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);'
            'border-radius:8px;padding:12px 16px;font-size:0.82rem;color:#fbbf24;margin:8px 0">'
            '⚠ 画像が見つかりません</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)
