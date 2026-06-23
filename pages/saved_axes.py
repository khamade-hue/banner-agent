"""Page 3: 保存済み訴求軸"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_axes, delete_axis


def _pills(items: list, bg: str, color: str, border: str) -> str:
    return "".join(
        f"""<span style="display:inline-block;background:{bg};color:{color};
             border:1px solid {border};border-radius:20px;padding:4px 12px;
             font-size:0.78rem;margin:3px 4px 3px 0;line-height:1.3;font-weight:500">{item}</span>"""
        for item in items
    )


st.markdown("""
<div style="background:linear-gradient(135deg,#0f2744 0%,#1e3a5f 60%,#0f4c75 100%);
     padding:32px 36px;border-radius:20px;margin-bottom:28px;
     border:1px solid rgba(59,130,246,0.25);
     box-shadow:0 8px 32px rgba(15,75,117,0.3),inset 0 1px 0 rgba(255,255,255,0.06)">
  <h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;
       line-height:1.15;letter-spacing:-0.02em">保存済み訴求軸</h1>
  <p style="color:#7dd3fc;margin:0;font-size:0.9rem;line-height:1.6">
      「バナー生成」ページで使用する訴求軸を管理します
  </p>
</div>
""", unsafe_allow_html=True)

saved_axes = load_axes()

if not saved_axes:
    st.markdown("""
    <div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;
         border-radius:14px;padding:60px;text-align:center">
        <div style="font-size:3rem;margin-bottom:16px">🎯</div>
        <div style="color:#e2e8f0;font-size:1.1rem;font-weight:700;margin-bottom:8px">
            保存済みの訴求軸がありません
        </div>
        <div style="color:#64748b;font-size:0.875rem;margin-bottom:24px">
            「訴求軸の検討」ページで3C分析を実施し、「＋ バナー生成で使う」を押して保存してください
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("訴求軸の検討ページへ →", type="primary"):
        st.switch_page("pages/analysis.py")
    st.stop()

st.markdown(
    f"<p style='color:#475569;font-size:0.82rem;margin-bottom:20px'>"
    f"<span style='color:#3b82f6;font-weight:700'>{len(saved_axes)}</span> 件の訴求軸が保存されています</p>",
    unsafe_allow_html=True,
)

BADGE_COLORS = ["#3b82f6","#8b5cf6","#ec4899","#f59e0b","#10b981"]
BADGE_GLOWS  = [
    "rgba(59,130,246,0.3)","rgba(139,92,246,0.3)",
    "rgba(236,72,153,0.3)","rgba(245,158,11,0.3)","rgba(16,185,129,0.3)",
]

for idx, ax in enumerate(reversed(saved_axes)):
    color = BADGE_COLORS[idx % len(BADGE_COLORS)]
    glow  = BADGE_GLOWS[idx % len(BADGE_GLOWS)]
    copy_s = ax.get("copy_suggestions", {})

    st.markdown(f"""
    <div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:16px;
         padding:22px 26px;border:1px solid #334155;margin-bottom:6px;
         border-left:4px solid {color};
         box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 10px {glow}">

        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                 width:28px;height:28px;border-radius:50%;background:{color};
                 color:white;font-weight:800;font-size:12px;flex-shrink:0">{idx+1}</div>
            <span style="font-size:1.05rem;font-weight:800;color:#e2e8f0;
                  letter-spacing:-0.01em">{ax["axis"]}</span>
        </div>

        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px">
            <span style="background:rgba(255,255,255,0.05);border:1px solid #334155;
                 border-radius:6px;padding:3px 10px;font-size:0.74rem;color:#64748b">
                📦 {ax["product_name"]}
            </span>
            <span style="background:rgba(255,255,255,0.05);border:1px solid #334155;
                 border-radius:6px;padding:3px 10px;font-size:0.74rem;color:#64748b">
                {ax.get("created_at","")[:10]}
            </span>
        </div>

        <p style="color:#94a3b8;font-size:0.86rem;line-height:1.6;margin:0 0 10px">
            {ax.get("description","")}
        </p>

        <div style="background:rgba(255,255,255,0.04);border:1px solid #1e3a5f;
             border-radius:8px;padding:6px 12px;font-size:0.78rem;margin-bottom:12px;display:inline-block">
            <span style="color:#64748b;font-weight:600">🎯 ターゲット</span>
            <span style="color:#cbd5e1;margin-left:6px">{ax.get("target_segment","—")}</span>
        </div>
    """, unsafe_allow_html=True)

    if copy_s:
        if copy_s.get("headlines"):
            st.markdown(f"""
            <div style="margin-bottom:8px">
                <div style="font-size:0.67rem;font-weight:700;color:#64748b;text-transform:uppercase;
                     letter-spacing:0.1em;margin-bottom:5px">キャッチコピー</div>
                {_pills(copy_s["headlines"],"rgba(59,130,246,0.12)","#93c5fd","rgba(59,130,246,0.35)")}
            </div>""", unsafe_allow_html=True)
        if copy_s.get("offers"):
            st.markdown(f"""
            <div style="margin-bottom:8px">
                <div style="font-size:0.67rem;font-weight:700;color:#64748b;text-transform:uppercase;
                     letter-spacing:0.1em;margin-bottom:5px">オファー・CTA</div>
                {_pills(copy_s["offers"],"rgba(16,185,129,0.12)","#6ee7b7","rgba(16,185,129,0.35)")}
            </div>""", unsafe_allow_html=True)
        if copy_s.get("features"):
            st.markdown(f"""
            <div style="margin-bottom:4px">
                <div style="font-size:0.67rem;font-weight:700;color:#64748b;text-transform:uppercase;
                     letter-spacing:0.1em;margin-bottom:5px">特徴・アイコン</div>
                {_pills(copy_s["features"],"rgba(139,92,246,0.12)","#c4b5fd","rgba(139,92,246,0.35)")}
            </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🗑 削除", key=f"del_axis_{ax['id']}", type="secondary"):
        delete_axis(ax["id"])
        st.rerun()

    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)
