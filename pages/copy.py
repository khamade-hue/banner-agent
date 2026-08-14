"""Page 2: コピー登録・修正"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import generate_copies
from state import delete_copy, load_copies, load_products, save_copy, update_copy

_OBJECTIVES = ["認知拡大", "クリック促進", "コンバージョン", "リターゲティング", "シーズン・キャンペーン"]

st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e1b4b 60%,#312e81 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:24px;'
    'border:1px solid rgba(139,92,246,0.3);'
    'box-shadow:0 8px 32px rgba(99,102,241,0.2),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">コピー登録・修正</h1>'
    '<p style="color:#a5b4fc;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    'バナーに使用するメインコピー・サブコピー・RTBを登録・管理します'
    '</p></div>',
    unsafe_allow_html=True,
)

# ── モード切替 ────────────────────────────────────────────────────────────────
_copy_mode = st.radio(
    "",
    ["新規登録", "登録済みを修正"],
    horizontal=True,
    index=0,
    key="copy_page_mode",
    label_visibility="collapsed",
)

st.divider()


def _copy_preview(c: dict) -> None:
    """共通コピープレビューカード"""
    rtbs = c.get("rtbs", [])
    rtb_pills = "".join(
        f'<span style="background:rgba(139,92,246,0.15);color:#c4b5fd;'
        f'border:1px solid rgba(139,92,246,0.35);border-radius:12px;'
        f'padding:2px 9px;font-size:0.72rem;margin:2px 3px 2px 0;display:inline-block">{r}</span>'
        for r in rtbs
    )
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid #334155;'
        f'border-radius:10px;padding:12px 14px;margin:6px 0">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
        f'<span style="font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;'
        f'letter-spacing:0.1em;width:64px;flex-shrink:0">メイン</span>'
        f'<span style="color:#93c5fd;font-weight:700;font-size:0.9rem">{c.get("headline","")}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
        f'<span style="font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;'
        f'letter-spacing:0.1em;width:64px;flex-shrink:0">サブ</span>'
        f'<span style="color:#a5b4fc;font-size:0.83rem">{c.get("sub_headline","")}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:flex-start;gap:8px">'
        f'<span style="font-size:0.6rem;font-weight:700;color:#475569;text-transform:uppercase;'
        f'letter-spacing:0.1em;width:64px;flex-shrink:0;padding-top:4px">RTB</span>'
        f'<div style="flex:1">{rtb_pills if rtb_pills else "<span style=\'color:#475569;font-size:0.75rem\'>なし</span>"}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 新規登録
# ══════════════════════════════════════════════════════════════════════════════
if _copy_mode == "新規登録":

    # 商品・目的選択
    try:
        products = load_products()
    except Exception as _e:
        st.error(
            "⚠️ **Supabase 接続エラー**\n\n"
            "Supabase プロジェクトが一時停止しているか、Secrets の設定が正しくない可能性があります。\n\n"
            f"エラー詳細: `{_e}`"
        )
        st.stop()

    if not products:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
            'border-radius:12px;padding:40px;text-align:center;color:#64748b">'
            '先に「商品登録・修正」ページで商品を登録してください。</div>',
            unsafe_allow_html=True,
        )
        if st.button("商品登録ページへ →", type="primary"):
            st.switch_page("pages/product.py")
        st.stop()

    col_prod, col_obj = st.columns(2)
    with col_prod:
        prod_labels = [p["product_name"] for p in products]
        sel_prod_idx = st.selectbox(
            "商品 *", range(len(products)),
            format_func=lambda i: prod_labels[i],
            key="copy_prod_sel",
        )
        selected_product = products[sel_prod_idx]
    with col_obj:
        selected_objective = st.selectbox("目的 *", _OBJECTIVES, key="copy_obj_sel")

    st.divider()

    # 登録方法
    input_method = st.radio(
        "登録方法",
        ["手動入力", "AI生成（5セット）"],
        horizontal=True,
        key="copy_input_method",
    )

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # ── 手動入力 ──────────────────────────────────────────────────────────────
    if input_method == "手動入力":
        headline = st.text_input(
            "メインコピー *",
            placeholder="例: 制作費、10分の1でいい。",
            max_chars=20,
            key="copy_hl_input",
        )
        sub_headline = st.text_input(
            "サブコピー *",
            placeholder="例: 社内に動画ノウハウがなくても大丈夫",
            max_chars=30,
            key="copy_sub_input",
        )
        st.markdown(
            '<div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;'
            'letter-spacing:0.1em;margin:12px 0 6px">RTB（Reason to Believe）</div>',
            unsafe_allow_html=True,
        )
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            rtb1 = st.text_input("RTB 1", placeholder="例: 最短3営業日で納品", max_chars=20, key="rtb1_in")
        with col_r2:
            rtb2 = st.text_input("RTB 2", placeholder="例: 修正回数無制限", max_chars=20, key="rtb2_in")
        with col_r3:
            rtb3 = st.text_input("RTB 3", placeholder="例: 著作権譲渡・商用利用OK", max_chars=20, key="rtb3_in")

        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if st.button("コピーを登録する", type="primary", use_container_width=True, key="manual_save_btn"):
            if not headline.strip() or not sub_headline.strip():
                st.error("メインコピーとサブコピーは必須です")
            else:
                try:
                    rtbs = [r.strip() for r in [rtb1, rtb2, rtb3] if r.strip()]
                    save_copy(
                        product_id=selected_product["id"],
                        product_name=selected_product["product_name"],
                        objective=selected_objective,
                        headline=headline.strip(),
                        sub_headline=sub_headline.strip(),
                        rtbs=rtbs,
                    )
                    st.success("コピーを登録しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")

    # ── AI生成 ────────────────────────────────────────────────────────────────
    else:
        if st.button("AIでコピーを生成する", type="primary", use_container_width=True, key="ai_gen_btn"):
            with st.spinner("Claude がコピーを生成中..."):
                try:
                    copy_sets = generate_copies(
                        product_name=selected_product["product_name"],
                        product_info=selected_product.get("product_info", ""),
                        objective=selected_objective,
                    )
                    st.session_state["ai_generated_copies"] = copy_sets
                    st.session_state["ai_copy_product_id"]   = selected_product["id"]
                    st.session_state["ai_copy_product_name"] = selected_product["product_name"]
                    st.session_state["ai_copy_objective"]    = selected_objective
                except Exception as e:
                    st.error(f"生成エラー: {e}")

        gen_copies = st.session_state.get("ai_generated_copies", [])
        if gen_copies:
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;text-transform:uppercase;'
                'letter-spacing:0.1em;margin:16px 0 10px">生成されたコピーセット（保存するものにチェック）</div>',
                unsafe_allow_html=True,
            )
            for i, cs in enumerate(gen_copies):
                with st.container(border=True):
                    checked = st.checkbox(
                        f"セット {i + 1}　「{cs.get('headline', '')}」",
                        key=f"ai_cs_check_{i}",
                        value=False,
                    )
                    if checked:
                        _copy_preview(cs)

            any_checked = any(st.session_state.get(f"ai_cs_check_{i}", False) for i in range(len(gen_copies)))
            if any_checked:
                if st.button("選択したコピーを登録する", type="primary", use_container_width=True, key="ai_bulk_save"):
                    count = 0
                    try:
                        for i, cs in enumerate(gen_copies):
                            if st.session_state.get(f"ai_cs_check_{i}", False):
                                save_copy(
                                    product_id=st.session_state["ai_copy_product_id"],
                                    product_name=st.session_state["ai_copy_product_name"],
                                    objective=st.session_state["ai_copy_objective"],
                                    headline=cs.get("headline", ""),
                                    sub_headline=cs.get("sub_headline", ""),
                                    rtbs=cs.get("rtbs", []),
                                )
                                count += 1
                        st.success(f"{count} 件のコピーを登録しました！")
                        for i in range(len(gen_copies)):
                            st.session_state.pop(f"ai_cs_check_{i}", None)
                        st.session_state.pop("ai_generated_copies", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"登録エラー: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 登録済みを修正
# ══════════════════════════════════════════════════════════════════════════════
else:
    try:
        all_copies = load_copies()
    except Exception as _e:
        st.error(
            "⚠️ **Supabase 接続エラー**\n\n"
            "Supabase プロジェクトが一時停止しているか、Secrets の設定が正しくない可能性があります。\n\n"
            f"エラー詳細: `{_e}`"
        )
        st.stop()

    if not all_copies:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
            'border-radius:12px;padding:40px;text-align:center;color:#64748b">'
            '登録済みコピーがありません。「新規登録」タブから登録してください。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-bottom:12px">'
            f'登録済みコピー <span style="color:#64748b;font-weight:400;font-size:0.78rem;'
            f'text-transform:none;letter-spacing:0">（{len(all_copies)} 件）</span></div>',
            unsafe_allow_html=True,
        )

        for c in reversed(all_copies):
            _ek = f"_edit_copy_{c['id']}"
            expander_label = f"[{c.get('objective', '—')}] {c.get('product_name', '—')} — {c.get('headline', '')}"
            with st.expander(expander_label, expanded=False):

                if not st.session_state.get(_ek, False):
                    _copy_preview(c)
                    st.caption(f"登録日: {c.get('created_at', '')[:10]}")
                    col_edit, col_del, _ = st.columns([1, 1, 4])
                    with col_edit:
                        if st.button("✏️ 編集", key=f"edit_copy_{c['id']}", type="secondary",
                                     use_container_width=True):
                            st.session_state[_ek] = True
                            st.rerun()
                    with col_del:
                        if st.button("🗑 削除", key=f"del_copy_{c['id']}", type="secondary",
                                     use_container_width=True):
                            delete_copy(c["id"])
                            st.rerun()

                else:
                    st.markdown(
                        '<div style="font-size:0.72rem;font-weight:700;color:#f59e0b;'
                        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px">編集中</div>',
                        unsafe_allow_html=True,
                    )
                    e_hl  = st.text_input("メインコピー *", value=c.get("headline", ""),
                                          max_chars=20, key=f"e_hl_{c['id']}")
                    e_sub = st.text_input("サブコピー *", value=c.get("sub_headline", ""),
                                          max_chars=30, key=f"e_sub_{c['id']}")
                    cur_rtbs = c.get("rtbs", [])
                    ec_r1, ec_r2, ec_r3 = st.columns(3)
                    with ec_r1:
                        e_r1 = st.text_input("RTB 1", value=cur_rtbs[0] if len(cur_rtbs) > 0 else "",
                                             max_chars=20, key=f"e_r1_{c['id']}")
                    with ec_r2:
                        e_r2 = st.text_input("RTB 2", value=cur_rtbs[1] if len(cur_rtbs) > 1 else "",
                                             max_chars=20, key=f"e_r2_{c['id']}")
                    with ec_r3:
                        e_r3 = st.text_input("RTB 3", value=cur_rtbs[2] if len(cur_rtbs) > 2 else "",
                                             max_chars=20, key=f"e_r3_{c['id']}")

                    btn_s, btn_c = st.columns(2)
                    with btn_s:
                        if st.button("保存", type="primary", use_container_width=True,
                                     key=f"save_copy_{c['id']}"):
                            if not e_hl.strip() or not e_sub.strip():
                                st.error("メインコピーとサブコピーは必須です")
                            else:
                                try:
                                    new_rtbs = [r.strip() for r in [e_r1, e_r2, e_r3] if r.strip()]
                                    update_copy(c["id"], e_hl.strip(), e_sub.strip(), new_rtbs)
                                    st.session_state[_ek] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"更新エラー: {e}")
                    with btn_c:
                        if st.button("キャンセル", use_container_width=True,
                                     key=f"cancel_copy_{c['id']}"):
                            st.session_state[_ek] = False
                            st.rerun()
