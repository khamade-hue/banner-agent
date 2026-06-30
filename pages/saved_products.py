"""Page: 登録済み商品"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import delete_product, load_products, update_product

st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#134e2e 60%,#166534 100%);'
    'padding:28px 32px;border-radius:18px;margin-bottom:24px;'
    'border:1px solid rgba(34,197,94,0.25);'
    'box-shadow:0 8px 32px rgba(22,101,52,0.25),inset 0 1px 0 rgba(255,255,255,0.06)">'
    '<h1 style="color:#e2e8f0;margin:0 0 8px;font-size:1.8rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">登録済み商品</h1>'
    '<p style="color:#86efac;margin:0;font-size:0.875rem;line-height:1.6">'
    '登録した商品の確認・編集・削除ができます</p>'
    '</div>',
    unsafe_allow_html=True,
)

products = load_products()

col_reg, _ = st.columns([2, 5])
with col_reg:
    if st.button("＋ 商品を新規登録", type="primary", use_container_width=True):
        st.switch_page("pages/product.py")

st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

if not products:
    st.markdown(
        '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
        'border-radius:14px;padding:60px;text-align:center">'
        '<div style="font-size:3rem;margin-bottom:16px">📦</div>'
        '<div style="color:#f1f5f9;font-size:1.05rem;font-weight:700;margin-bottom:8px">'
        'まだ商品が登録されていません</div>'
        '<div style="color:#64748b;font-size:0.875rem">'
        '「商品登録」ページから商品情報を登録してください</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

st.markdown(
    f'<p style="color:#475569;font-size:0.82rem;margin-bottom:16px">'
    f'<span style="color:#22c55e;font-weight:700">{len(products)}</span>'
    f' 件の商品が登録されています</p>',
    unsafe_allow_html=True,
)

for p in reversed(products):
    col_exp, col_del = st.columns([11, 1])

    with col_exp:
        with st.expander(p["product_name"], expanded=False):
            _edit_key = f"_edit_prod_{p['id']}"

            # ── 表示モード ──────────────────────────────────────────────────
            if not st.session_state.get(_edit_key, False):
                col_meta, col_btns = st.columns([8, 1])
                with col_meta:
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#64748b;margin-bottom:8px">'
                        f'<a href="{p.get("product_url","")}" target="_blank" '
                        f'style="color:#93c5fd;text-decoration:none">{p.get("product_url","")}</a>'
                        f'　{p.get("created_at","")[:10]}</div>',
                        unsafe_allow_html=True,
                    )

                col_info, col_imgs = st.columns([3, 1])
                with col_info:
                    if p.get("product_info"):
                        st.markdown(
                            '<div style="font-size:0.7rem;font-weight:700;color:#64748b;'
                            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">'
                            '商品情報</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="font-size:0.82rem;color:#94a3b8;line-height:1.6">'
                            f'{p["product_info"][:300]}{"…" if len(p["product_info"]) > 300 else ""}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    if p.get("competitor_info"):
                        st.markdown(
                            '<div style="font-size:0.7rem;font-weight:700;color:#64748b;'
                            'text-transform:uppercase;letter-spacing:0.1em;margin:10px 0 4px">'
                            '競合情報</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="font-size:0.82rem;color:#94a3b8;line-height:1.6">'
                            f'{p["competitor_info"][:200]}{"…" if len(p["competitor_info"]) > 200 else ""}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                with col_imgs:
                    if p.get("product_image_url"):
                        st.image(p["product_image_url"], caption="商品画像", width=100)
                    if p.get("product_logo_url"):
                        st.image(p["product_logo_url"], caption="商品ロゴ", width=80)
                    if p.get("logo_url"):
                        st.image(p["logo_url"], caption="企業ロゴ", width=80)

                with col_btns:
                    if st.button("✏️", key=f"edit_prod_{p['id']}", help="編集",
                                 use_container_width=True):
                        st.session_state[_edit_key] = True
                        st.rerun()

            # ── 編集モード ──────────────────────────────────────────────────
            else:
                st.markdown(
                    '<div style="font-size:0.72rem;font-weight:700;color:#f59e0b;'
                    'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px">'
                    '編集中</div>',
                    unsafe_allow_html=True,
                )
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    e_name = st.text_input(
                        "商品名 *", value=p.get("product_name", ""),
                        key=f"e_name_{p['id']}",
                    )
                with e_col2:
                    e_url = st.text_input(
                        "商品ページURL *", value=p.get("product_url", ""),
                        key=f"e_url_{p['id']}",
                    )
                e_info = st.text_area(
                    "商品情報", value=p.get("product_info", ""),
                    height=110, key=f"e_info_{p['id']}",
                )
                e_comp = st.text_area(
                    "競合商品情報", value=p.get("competitor_info", ""),
                    height=90, key=f"e_comp_{p['id']}",
                )

                def _img_field(col, label, url_key, del_sk, undo_sk, up_key, file_types):
                    with col:
                        st.markdown(
                            f'<div style="font-size:0.75rem;color:#64748b;font-weight:600;'
                            f'margin-bottom:4px">{label}</div>',
                            unsafe_allow_html=True,
                        )
                        existing_url = p.get(url_key, "")
                        is_del = st.session_state.get(del_sk, False)
                        if existing_url and not is_del:
                            _pc, _dc = st.columns([4, 1])
                            with _pc:
                                st.image(existing_url, width=90)
                            with _dc:
                                st.markdown(
                                    "<div style='height:24px'></div>", unsafe_allow_html=True
                                )
                                if st.button(
                                    "🗑", key=f"del_btn_{del_sk}", type="secondary",
                                    use_container_width=True, help="この画像を削除",
                                ):
                                    st.session_state[del_sk] = True
                                    st.rerun()
                        elif existing_url and is_del:
                            st.markdown(
                                '<div style="color:#ef4444;font-size:0.72rem;font-weight:600;'
                                'padding:4px 0 6px">✕ 保存時に削除されます</div>',
                                unsafe_allow_html=True,
                            )
                            if st.button("取り消し", key=undo_sk, type="secondary"):
                                st.session_state[del_sk] = False
                                st.rerun()
                        uploaded = st.file_uploader(
                            label, type=file_types,
                            key=up_key, label_visibility="collapsed",
                        )
                        if uploaded:
                            st.image(uploaded, width=90)
                    return uploaded

                e_img_col, e_plogo_col, e_logo_col = st.columns(3)
                e_image        = _img_field(
                    e_img_col,   "商品画像",
                    url_key="product_image_url",
                    del_sk=f"del_pimg_{p['id']}", undo_sk=f"undo_pimg_{p['id']}",
                    up_key=f"e_img_{p['id']}", file_types=["png", "jpg", "jpeg"],
                )
                e_product_logo = _img_field(
                    e_plogo_col, "商品ロゴ",
                    url_key="product_logo_url",
                    del_sk=f"del_plogo_{p['id']}", undo_sk=f"undo_plogo_{p['id']}",
                    up_key=f"e_plogo_{p['id']}", file_types=["png", "jpg", "jpeg"],
                )
                e_logo         = _img_field(
                    e_logo_col,  "企業ロゴ",
                    url_key="logo_url",
                    del_sk=f"del_logo_{p['id']}", undo_sk=f"undo_logo_{p['id']}",
                    up_key=f"e_logo_{p['id']}", file_types=["png", "jpg", "jpeg"],
                )

                btn_save, btn_cancel = st.columns(2)
                with btn_save:
                    if st.button("保存", type="primary", use_container_width=True,
                                 key=f"save_prod_{p['id']}"):
                        if not e_name.strip() or not e_url.strip():
                            st.error("商品名と商品ページURLは必須です")
                        else:
                            with st.spinner("更新中..."):
                                try:
                                    img_bytes   = e_image.read() if e_image else None
                                    img_ext     = e_image.name.rsplit(".", 1)[-1].lower() if e_image else "png"
                                    plogo_bytes = e_product_logo.read() if e_product_logo else None
                                    plogo_ext   = e_product_logo.name.rsplit(".", 1)[-1].lower() if e_product_logo else "png"
                                    logo_bytes  = e_logo.read() if e_logo else None
                                    logo_ext    = e_logo.name.rsplit(".", 1)[-1].lower() if e_logo else "png"
                                    update_product(
                                        product_id=p["id"],
                                        product_name=e_name.strip(),
                                        product_info=e_info.strip(),
                                        product_url=e_url.strip(),
                                        competitor_info=e_comp.strip(),
                                        product_image=img_bytes,
                                        product_image_ext=img_ext,
                                        product_logo=plogo_bytes,
                                        product_logo_ext=plogo_ext,
                                        logo=logo_bytes,
                                        logo_ext=logo_ext,
                                        clear_product_image=st.session_state.get(f"del_pimg_{p['id']}", False),
                                        clear_product_logo=st.session_state.get(f"del_plogo_{p['id']}", False),
                                        clear_logo=st.session_state.get(f"del_logo_{p['id']}", False),
                                    )
                                    for _k in [f"del_pimg_{p['id']}", f"del_plogo_{p['id']}", f"del_logo_{p['id']}"]:
                                        st.session_state.pop(_k, None)
                                    st.session_state[_edit_key] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"更新エラー: {e}")
                with btn_cancel:
                    if st.button("キャンセル", use_container_width=True,
                                 key=f"cancel_prod_{p['id']}"):
                        for _k in [f"del_pimg_{p['id']}", f"del_plogo_{p['id']}", f"del_logo_{p['id']}"]:
                            st.session_state.pop(_k, None)
                        st.session_state[_edit_key] = False
                        st.rerun()

    with col_del:
        if st.button("🗑", key=f"del_prod_sp_{p['id']}", help="削除",
                     type="secondary", use_container_width=True):
            delete_product(p["id"])
            st.rerun()
