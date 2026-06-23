"""Page 3: 保存済みバナー"""

import io
import os
import sys

import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_banners, delete_banner

st.markdown("""
<div style="background:linear-gradient(135deg,#0f2744 0%,#064e3b 60%,#065f46 100%);
     padding:32px 36px;border-radius:20px;margin-bottom:28px;
     border:1px solid rgba(16,185,129,0.3);
     box-shadow:0 8px 32px rgba(16,185,129,0.15),inset 0 1px 0 rgba(255,255,255,0.07)">
  <h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;
       line-height:1.15;letter-spacing:-0.02em">保存済みバナー</h1>
  <p style="color:#6ee7b7;margin:0;font-size:0.9rem;line-height:1.6">
      これまでに生成・保存したバナー画像の一覧です
  </p>
</div>
""", unsafe_allow_html=True)

banners = load_banners()

if not banners:
    st.markdown("""
    <div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;
         border-radius:14px;padding:60px;text-align:center">
        <div style="font-size:3rem;margin-bottom:16px">🖼️</div>
        <div style="color:#f1f5f9;font-size:1.1rem;font-weight:700;margin-bottom:8px">
            まだバナーが保存されていません
        </div>
        <div style="color:#64748b;font-size:0.875rem;margin-bottom:24px">
            「バナー生成」ページで画像を生成すると、ここに表示されます
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("バナー生成ページへ →", type="primary"):
        st.switch_page("pages/banner.py")
    st.stop()

banners_sorted = sorted(banners, key=lambda b: b["created_at"], reverse=True)

st.markdown(
    f"<p style='color:#475569;font-size:0.82rem;margin-bottom:20px'>"
    f"<span style='color:#10b981;font-weight:700'>{len(banners_sorted)}</span> 件のバナーが保存されています</p>",
    unsafe_allow_html=True,
)

for banner in banners_sorted:
    platforms    = banner.get("platforms", [])
    valid_platforms = [p for p in platforms if os.path.exists(p["path"])]

    st.markdown(f"""
    <div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:16px;
         padding:20px 24px;border:1px solid #334155;margin-bottom:8px;
         box-shadow:0 4px 16px rgba(0,0,0,0.2)">
        <div style="display:flex;align-items:flex-start;justify-content:space-between">
            <div>
                <div style="font-size:1rem;font-weight:800;color:#f1f5f9;margin-bottom:6px">
                    [{banner["variation"]}] {banner["label"]}
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:6px">
                    <span style="background:rgba(255,255,255,0.06);border:1px solid #334155;
                         border-radius:6px;padding:3px 10px;font-size:0.75rem;color:#94a3b8">
                        📦 {banner["product_name"]}
                    </span>
                    <span style="background:rgba(255,255,255,0.06);border:1px solid #334155;
                         border-radius:6px;padding:3px 10px;font-size:0.75rem;color:#94a3b8">
                        🎯 {banner["axis"]}
                    </span>
                    <span style="background:rgba(255,255,255,0.06);border:1px solid #334155;
                         border-radius:6px;padding:3px 10px;font-size:0.75rem;color:#94a3b8">
                        🎨 {banner.get("tonmana","—")}
                    </span>
                    <span style="background:rgba(255,255,255,0.06);border:1px solid #334155;
                         border-radius:6px;padding:3px 10px;font-size:0.75rem;color:#64748b">
                        {banner["created_at"][:10]}
                    </span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_del, _ = st.columns([1, 5])
    with col_del:
        if st.button("🗑 削除", key=f"del_banner_{banner['id']}", type="secondary"):
            delete_banner(banner["id"])
            st.rerun()

    if valid_platforms:
        chunk = 4
        for row_start in range(0, len(valid_platforms), chunk):
            row  = valid_platforms[row_start: row_start + chunk]
            cols = st.columns(len(row))
            for col, p in zip(cols, row):
                with col:
                    img = Image.open(p["path"])
                    st.image(
                        img,
                        caption=f"{p['platform_name']}  {p['width']}×{p['height']}",
                        use_container_width=True,
                    )
                    buf = io.BytesIO()
                    img.save(buf, "PNG")
                    st.download_button(
                        f"↓ DL",
                        data=buf.getvalue(),
                        file_name=p["filename"],
                        mime="image/png",
                        key=f"dl_{banner['id']}_{p['filename']}",
                        use_container_width=True,
                    )
    else:
        st.markdown("""
        <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);
             border-radius:8px;padding:12px 16px;font-size:0.82rem;color:#fbbf24;margin:8px 0">
            ⚠ 画像ファイルが見つかりません（Streamlit Cloud 再起動でリセットされた可能性があります）
        </div>
        """, unsafe_allow_html=True)

    with st.expander("生成プロンプトを見る"):
        st.code(banner.get("prompt", ""), language=None)

    st.markdown("<div style='margin-bottom:24px'></div>", unsafe_allow_html=True)
