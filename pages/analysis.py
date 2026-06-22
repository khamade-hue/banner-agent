"""Page 1: ターゲットと訴求軸の検討エージェント"""

import os
import re
import sys
import urllib.request

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import analyze_product, generate_more_axes
from state import load_axes, add_axis, delete_axis


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


st.title("ターゲットと訴求軸の検討")
st.caption("商品URLをもとに Claude が3C分析を実施し、SNS広告の訴求軸を提案します")

# ── Input form ───────────────────────────────────────────────────────────────
with st.form("analysis_form"):
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("商品名 *", placeholder="例: プロテインバー MUSCLE BOOST")
    with col2:
        product_url = st.text_input("商品URL *", placeholder="例: https://example.com/product")
    submitted = st.form_submit_button(
        "3C分析・訴求軸を生成", type="primary", use_container_width=True
    )

if submitted:
    if not product_name or not product_url:
        st.error("商品名と商品URLは必須です")
        st.stop()

    with st.status("分析中...", expanded=True) as status:
        st.write("URLからページ内容を取得中...")
        page_content = _fetch_page_content(product_url)
        if page_content:
            st.write(f"✓ ページ内容を取得しました（{len(page_content)} 文字）")
        else:
            st.write("⚠ ページ内容の取得に失敗しました（URLの情報のみで分析します）")

        st.write("Claude が3C分析・訴求軸を生成中...")
        try:
            analysis = analyze_product(product_name, product_url, page_content)
        except Exception as e:
            st.error(f"分析エラー: {e}")
            st.stop()

        status.update(label="分析完了！", state="complete", expanded=False)

    st.session_state["analysis"] = analysis
    st.session_state["analysis_product_name"] = product_name
    st.session_state["analysis_product_url"] = product_url


# ── Analysis results ─────────────────────────────────────────────────────────
if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    product_name_s = st.session_state.get("analysis_product_name", "")
    product_url_s = st.session_state.get("analysis_product_url", "")
    c3 = analysis.get("3c_analysis", {})

    st.divider()
    st.subheader("3C分析結果")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**顧客（Customer）**")
        cust = c3.get("customer", {})
        st.markdown(f"🎯 **ニーズ:** {cust.get('needs', '—')}")
        st.markdown(f"😣 **課題:** {cust.get('pain_points', '—')}")
        st.markdown(f"👤 **属性:** {cust.get('demographics', '—')}")

    with col2:
        st.markdown("**競合（Competitor）**")
        comp = c3.get("competitor", {})
        st.markdown(f"🏢 **競合状況:** {comp.get('landscape', '—')}")
        st.markdown(f"⚡ **差別化:** {comp.get('differentiation', '—')}")

    with col3:
        st.markdown("**自社（Company）**")
        co = c3.get("company", {})
        st.markdown(f"💪 **強み:** {co.get('strengths', '—')}")
        st.markdown(f"💡 **提供価値:** {co.get('value_proposition', '—')}")

    st.divider()
    st.subheader("提案訴求軸")

    current_axes = analysis.get("appeal_axes", [])

    for i, ax in enumerate(current_axes):
        with st.container(border=True):
            col_text, col_btn = st.columns([5, 1])
            with col_text:
                st.markdown(f"#### {ax['axis']}")
                st.markdown(ax.get("description", ""))
                st.caption(f"ターゲット: {ax.get('target_segment', '—')}")
                st.caption(f"根拠: {ax.get('rationale', '—')}")
            with col_btn:
                if st.button("リストに追加", key=f"add_axis_{i}", use_container_width=True):
                    add_axis(product_name_s, product_url_s, ax)
                    st.success(f"「{ax['axis']}」を追加しました")
                    st.rerun()

    # ── Additional axis generation ────────────────────────────────────────────
    st.divider()
    with st.expander("さらに訴求軸を追加する"):
        add_angle = st.text_input(
            "追加で検討したい観点（任意）",
            placeholder="例: 季節訴求、価格訴求、BtoB向けなど",
            key="add_angle_input",
        )
        if st.button("追加訴求軸を生成", key="gen_more_btn"):
            with st.spinner("訴求軸を生成中..."):
                try:
                    new_axes = generate_more_axes(product_name_s, current_axes, add_angle)
                    analysis["appeal_axes"] = current_axes + new_axes
                    st.session_state["analysis"] = analysis
                    st.rerun()
                except Exception as e:
                    st.error(f"生成エラー: {e}")


# ── Saved axes list ───────────────────────────────────────────────────────────
st.divider()
st.subheader("保存済み訴求軸リスト")

saved_axes = load_axes()
if not saved_axes:
    st.info("まだ訴求軸が保存されていません。上記で分析を実施して「リストに追加」してください。")
else:
    for ax in saved_axes:
        with st.container(border=True):
            col_text, col_btn = st.columns([5, 1])
            with col_text:
                st.markdown(f"**{ax['axis']}** — *{ax['product_name']}*")
                st.markdown(ax.get("description", ""))
                st.caption(
                    f"ターゲット: {ax.get('target_segment', '—')} ｜ "
                    f"追加日: {ax.get('created_at', '')[:10]}"
                )
            with col_btn:
                if st.button(
                    "削除", key=f"del_{ax['id']}", type="secondary", use_container_width=True
                ):
                    delete_axis(ax["id"])
                    st.rerun()
