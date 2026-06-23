"""Page 1: ターゲットと訴求軸の検討エージェント"""

import os
import re
import sys
import urllib.request

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import analyze_product, generate_more_axes
from state import add_axis, load_axes


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
    return f"""
    <div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:14px;
         padding:22px 24px;border-top:3px solid {color};
         box-shadow:0 4px 24px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.04)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
            <div style="background:{gradient};width:36px;height:36px;border-radius:10px;
                 display:flex;align-items:center;justify-content:center;font-size:1.1rem;
                 box-shadow:0 2px 8px rgba(0,0,0,0.3)">{icon}</div>
            <span style="font-weight:700;font-size:0.95rem;color:#f1f5f9">{title}</span>
        </div>
        {rows}
    </div>"""


def _pills(items: list, bg: str, color: str, border: str) -> str:
    return "".join(
        f"""<span style="display:inline-block;background:{bg};color:{color};
             border:1px solid {border};border-radius:20px;padding:5px 13px;
             font-size:0.8rem;margin:3px 4px 3px 0;line-height:1.3;font-weight:500">{item}</span>"""
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


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0f2744 0%,#1e3a8a 60%,#1d4ed8 100%);
     padding:32px 36px;border-radius:20px;margin-bottom:28px;
     border:1px solid rgba(59,130,246,0.3);
     box-shadow:0 8px 32px rgba(37,99,235,0.25),inset 0 1px 0 rgba(255,255,255,0.07)">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div style="background:rgba(59,130,246,0.25);border:1px solid rgba(59,130,246,0.4);
           border-radius:8px;padding:3px 10px;font-size:0.72rem;font-weight:700;
           color:#93c5fd;letter-spacing:0.1em;text-transform:uppercase">Step 1 / 2</div>
  </div>
  <h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;
       line-height:1.15;letter-spacing:-0.02em">訴求軸の検討</h1>
  <p style="color:#93c5fd;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">
      商品URLをもとに Claude が 3C 分析を実施し、SNS広告の最適な訴求軸とコピー候補を提案します
  </p>
</div>
""", unsafe_allow_html=True)

# ── Input form ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:16px;
     padding:24px 28px;border:1px solid #334155;margin-bottom:24px;
     box-shadow:0 4px 16px rgba(0,0,0,0.2)">
  <div style="font-size:0.72rem;font-weight:700;color:#3b82f6;
       text-transform:uppercase;letter-spacing:0.1em;margin-bottom:16px">
      商品情報の入力
  </div>
""", unsafe_allow_html=True)

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

st.markdown("</div>", unsafe_allow_html=True)

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


# ── Analysis results ──────────────────────────────────────────────────────────
if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    product_name_s = st.session_state.get("analysis_product_name", "")
    product_url_s  = st.session_state.get("analysis_product_url", "")
    c3   = analysis.get("3c_analysis", {})
    cust = c3.get("customer", {})
    comp = c3.get("competitor", {})
    co   = c3.get("company", {})

    # ── 3C cards ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;
         letter-spacing:0.1em;margin:8px 0 14px">3C 分析結果</div>
    """, unsafe_allow_html=True)

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

    # ── Appeal axes ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:36px;margin-bottom:16px">
        <div style="font-size:0.72rem;font-weight:700;color:#3b82f6;text-transform:uppercase;
             letter-spacing:0.1em;margin-bottom:6px">提案訴求軸</div>
        <p style="color:#64748b;font-size:0.82rem;margin:0">
            「＋ 追加」でバナー生成ページから使用できるようになります
        </p>
    </div>
    """, unsafe_allow_html=True)

    current_axes = analysis.get("appeal_axes", [])
    BADGE_COLORS  = ["#3b82f6","#8b5cf6","#ec4899","#f59e0b","#10b981"]
    BADGE_GLOWS   = [
        "rgba(59,130,246,0.35)", "rgba(139,92,246,0.35)",
        "rgba(236,72,153,0.35)", "rgba(245,158,11,0.35)", "rgba(16,185,129,0.35)",
    ]

    saved_axis_names = {a["axis"] for a in load_axes()}

    for i, ax in enumerate(current_axes):
        color  = BADGE_COLORS[i % len(BADGE_COLORS)]
        glow   = BADGE_GLOWS[i % len(BADGE_GLOWS)]
        copy_s = ax.get("copy_suggestions", {})

        # Build copy pills HTML inline
        copy_html = ""
        if copy_s:
            sections = (
                _copy_section("キャッチコピー", copy_s.get("headlines", []),
                              "rgba(59,130,246,0.15)", "#93c5fd", "rgba(59,130,246,0.4)") +
                _copy_section("オファー・CTA", copy_s.get("offers", []),
                              "rgba(16,185,129,0.15)", "#6ee7b7", "rgba(16,185,129,0.4)") +
                _copy_section("特徴・アイコン", copy_s.get("features", []),
                              "rgba(139,92,246,0.15)", "#c4b5fd", "rgba(139,92,246,0.4)")
            )
            if sections:
                copy_html = (
                    f'<div style="border-top:1px solid #334155;margin-top:14px;padding-top:14px">'
                    f'{sections}</div>'
                )

        col_card, col_btn = st.columns([10, 2])

        with col_card:
            st.markdown(f"""
            <div style="background:linear-gradient(145deg,#1e293b,#162032);border-radius:16px;
                 padding:22px 24px;border:1px solid #334155;
                 border-left:4px solid {color};
                 box-shadow:0 4px 20px rgba(0,0,0,0.25),-4px 0 12px {glow}">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                    <div style="display:inline-flex;align-items:center;justify-content:center;
                         width:30px;height:30px;border-radius:50%;background:{color};
                         color:white;font-weight:800;font-size:12px;flex-shrink:0;
                         box-shadow:0 2px 8px {glow}">{i+1}</div>
                    <span style="font-size:1.05rem;font-weight:800;color:#f1f5f9;
                          letter-spacing:-0.01em">{ax["axis"]}</span>
                </div>
                <p style="color:#94a3b8;font-size:0.85rem;line-height:1.65;margin:0 0 12px">
                    {ax.get("description","")}
                </p>
                <div style="display:flex;flex-wrap:wrap;gap:6px">
                    <div style="background:rgba(255,255,255,0.05);border:1px solid #334155;
                         border-radius:8px;padding:4px 11px;font-size:0.76rem">
                        <span style="color:#64748b;font-weight:600">🎯 ターゲット</span>
                        <span style="color:#cbd5e1;margin-left:5px">{ax.get("target_segment","—")}</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.05);border:1px solid #334155;
                         border-radius:8px;padding:4px 11px;font-size:0.76rem">
                        <span style="color:#64748b;font-weight:600">💡 根拠</span>
                        <span style="color:#cbd5e1;margin-left:5px">{ax.get("rationale","—")}</span>
                    </div>
                </div>
                {copy_html}
            </div>
            """, unsafe_allow_html=True)

        with col_btn:
            if ax["axis"] in saved_axis_names:
                st.markdown("""
                <div style="display:flex;flex-direction:column;align-items:center;
                     justify-content:flex-start;padding-top:18px;gap:5px">
                    <div style="width:32px;height:32px;border-radius:50%;
                         background:rgba(16,185,129,0.15);border:2px solid #10b981;
                         display:flex;align-items:center;justify-content:center;
                         color:#10b981;font-size:15px;font-weight:800">✓</div>
                    <div style="color:#10b981;font-size:0.68rem;font-weight:700;
                         text-align:center;line-height:1.3">保存済み</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                if st.button("＋ 追加", key=f"add_axis_{i}", type="primary",
                             use_container_width=True):
                    product_context = {
                        "value_proposition": co.get("value_proposition",""),
                        "strengths": co.get("strengths",""),
                        "customer_needs": cust.get("needs",""),
                        "pain_points": cust.get("pain_points",""),
                        "differentiation": comp.get("differentiation",""),
                    }
                    add_axis(product_name_s, product_url_s, ax, product_context)
                    st.rerun()

        st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    # ── Additional axes ────────────────────────────────────────────────────────
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


st.markdown("""
<div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.2);
     border-radius:10px;padding:12px 18px;margin-top:32px">
    <span style="color:#93c5fd;font-size:0.82rem">
        📋 追加した訴求軸は <strong>「保存済み訴求軸」</strong> ページで管理できます
    </span>
</div>
""", unsafe_allow_html=True)
