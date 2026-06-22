"""Page 3: 保存済みバナー"""

import io
import os
import sys

import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_banners, delete_banner

st.title("保存済みバナー")
st.caption("これまでに生成・保存したバナー画像の一覧です")

banners = load_banners()

if not banners:
    st.info("まだバナーが保存されていません。「バナー生成」ページで画像を生成してください。")
    if st.button("バナー生成ページへ", type="primary"):
        st.switch_page("pages/banner.py")
    st.stop()

banners_sorted = sorted(banners, key=lambda b: b["created_at"], reverse=True)
st.markdown(f"**合計 {len(banners_sorted)} バリエーション** が保存されています")
st.divider()

for banner in banners_sorted:
    platforms = banner.get("platforms", [])
    valid_platforms = [p for p in platforms if os.path.exists(p["path"])]

    col_info, col_del = st.columns([6, 1])
    with col_info:
        st.markdown(f"### [{banner['variation']}] {banner['label']}")
        st.caption(
            f"商品: {banner['product_name']} ｜ "
            f"訴求軸: {banner['axis']} ｜ "
            f"トンマナ: {banner.get('tonmana', '—')} ｜ "
            f"目的: {banner.get('objective', '—')} ｜ "
            f"生成日: {banner['created_at'][:10]}"
        )
    with col_del:
        if st.button("削除", key=f"del_banner_{banner['id']}", type="secondary"):
            delete_banner(banner["id"])
            st.rerun()

    if valid_platforms:
        chunk = 4
        for row_start in range(0, len(valid_platforms), chunk):
            row = valid_platforms[row_start: row_start + chunk]
            cols = st.columns(len(row))
            for col, p in zip(cols, row):
                with col:
                    img = Image.open(p["path"])
                    st.image(
                        img,
                        caption=f"{p['platform_name']}\n{p['width']}×{p['height']}",
                        use_container_width=True,
                    )
                    buf = io.BytesIO()
                    img.save(buf, "PNG")
                    st.download_button(
                        f"↓ {p['filename']}",
                        data=buf.getvalue(),
                        file_name=p["filename"],
                        mime="image/png",
                        key=f"dl_{banner['id']}_{p['filename']}",
                        use_container_width=True,
                    )
    else:
        st.warning("画像ファイルが見つかりません（Streamlit Cloud再起動でリセットされた可能性があります）")

    with st.expander("生成プロンプトを見る"):
        st.code(banner.get("prompt", ""), language=None)

    st.divider()
