"""Page 0: 商品登録"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import delete_product, load_products, save_product, update_product

st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#134e2e 60%,#166534 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:24px;'
    'border:1px solid rgba(34,197,94,0.25);'
    'box-shadow:0 8px 32px rgba(22,101,52,0.25),inset 0 1px 0 rgba(255,255,255,0.06)">'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">商品登録</h1>'
    '<p style="color:#86efac;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    '訴求軸生成で使用する商品情報を登録・管理します'
    '</p></div>',
    unsafe_allow_html=True,
)

# ── 登録フォーム ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:0.72rem;font-weight:700;color:#22c55e;text-transform:uppercase;'
    'letter-spacing:0.1em;margin-bottom:12px">新しい商品を登録</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("商品名 *", placeholder="例: Craftin for Company")
with col2:
    product_url = st.text_input("商品ページURL *", placeholder="https://example.com/product")

product_info = st.text_area(
    "商品情報（任意）",
    placeholder="商品の特徴・強み・ターゲット・価格帯・訴求ポイントなど。ここに書いた内容が3C分析のインプットになります。",
    height=110,
)

col_img, col_plogo, col_logo = st.columns(3)
with col_img:
    st.markdown(
        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
        '商品画像（任意）</div>',
        unsafe_allow_html=True,
    )
    uploaded_image = st.file_uploader(
        "商品画像", type=["png", "jpg", "jpeg"],
        key="prod_image", label_visibility="collapsed",
    )
    if uploaded_image:
        st.image(uploaded_image, width=140)

with col_plogo:
    st.markdown(
        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
        '商品ロゴ（任意）</div>',
        unsafe_allow_html=True,
    )
    uploaded_product_logo = st.file_uploader(
        "商品ロゴ", type=["png", "jpg", "jpeg"],
        key="prod_product_logo", label_visibility="collapsed",
    )
    if uploaded_product_logo:
        st.image(uploaded_product_logo, width=120)

with col_logo:
    st.markdown(
        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
        '企業ロゴ（任意）</div>',
        unsafe_allow_html=True,
    )
    uploaded_logo = st.file_uploader(
        "企業ロゴ", type=["png", "jpg", "jpeg"],
        key="prod_logo", label_visibility="collapsed",
    )
    if uploaded_logo:
        st.image(uploaded_logo, width=120)

competitor_info = st.text_area(
    "競合商品情報（任意）",
    placeholder="競合他社名・製品名・強み・差別化ポイントなど。ここに書いた内容が競合分析のインプットになります。",
    height=90,
)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
if st.button("商品を登録する", type="primary", use_container_width=True, key="reg_btn"):
    if not product_name.strip() or not product_url.strip():
        st.error("商品名と商品ページURLは必須です")
    else:
        with st.spinner("登録中..."):
            try:
                image_bytes        = uploaded_image.read() if uploaded_image else None
                image_ext          = uploaded_image.name.rsplit(".", 1)[-1].lower() if uploaded_image else "png"
                plogo_bytes        = uploaded_product_logo.read() if uploaded_product_logo else None
                plogo_ext          = uploaded_product_logo.name.rsplit(".", 1)[-1].lower() if uploaded_product_logo else "png"
                logo_bytes         = uploaded_logo.read() if uploaded_logo else None
                logo_ext           = uploaded_logo.name.rsplit(".", 1)[-1].lower() if uploaded_logo else "png"

                save_product(
                    product_name=product_name.strip(),
                    product_info=product_info.strip(),
                    product_url=product_url.strip(),
                    product_image=image_bytes,
                    product_image_ext=image_ext,
                    product_logo=plogo_bytes,
                    product_logo_ext=plogo_ext,
                    logo=logo_bytes,
                    logo_ext=logo_ext,
                    competitor_info=competitor_info.strip(),
                )
                st.success(f"「{product_name.strip()}」を登録しました！")
                st.rerun()
            except Exception as e:
                st.error(f"登録エラー: {e}")

# ── 登録済み商品一覧 ──────────────────────────────────────────────────────────
products = load_products()

st.divider()
st.markdown(
    f'<div style="font-size:0.72rem;font-weight:700;color:#22c55e;text-transform:uppercase;'
    f'letter-spacing:0.1em;margin-bottom:12px">'
    f'登録済み商品 <span style="color:#64748b;font-weight:400;font-size:0.78rem;'
    f'text-transform:none;letter-spacing:0">（{len(products)} 件）</span></div>',
    unsafe_allow_html=True,
)

if not products:
    st.markdown(
        '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
        'border-radius:12px;padding:40px;text-align:center;color:#64748b">'
        '登録済みの商品がありません。上のフォームから登録してください。</div>',
        unsafe_allow_html=True,
    )
else:
    for p in reversed(products):
        with st.expander(p["product_name"], expanded=False):
            _edit_key = f"_edit_prod_{p['id']}"

            # ── 表示モード ──────────────────────────────────────────────────────
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
                    if st.button("🗑", key=f"del_prod_{p['id']}", help="削除",
                                 use_container_width=True):
                        delete_product(p["id"])
                        st.rerun()

            # ── 編集モード ──────────────────────────────────────────────────────
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

                e_img_col, e_plogo_col, e_logo_col = st.columns(3)
                with e_img_col:
                    st.markdown(
                        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
                        '商品画像（変更する場合のみ）</div>',
                        unsafe_allow_html=True,
                    )
                    e_image = st.file_uploader(
                        "商品画像", type=["png", "jpg", "jpeg"],
                        key=f"e_img_{p['id']}", label_visibility="collapsed",
                    )
                    if e_image:
                        st.image(e_image, width=110)
                    elif p.get("product_image_url"):
                        st.image(p["product_image_url"], width=110)

                with e_plogo_col:
                    st.markdown(
                        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
                        '商品ロゴ（変更する場合のみ）</div>',
                        unsafe_allow_html=True,
                    )
                    e_product_logo = st.file_uploader(
                        "商品ロゴ", type=["png", "jpg", "jpeg"],
                        key=f"e_plogo_{p['id']}", label_visibility="collapsed",
                    )
                    if e_product_logo:
                        st.image(e_product_logo, width=100)
                    elif p.get("product_logo_url"):
                        st.image(p["product_logo_url"], width=100)

                with e_logo_col:
                    st.markdown(
                        '<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">'
                        '企業ロゴ（変更する場合のみ）</div>',
                        unsafe_allow_html=True,
                    )
                    e_logo = st.file_uploader(
                        "企業ロゴ", type=["png", "jpg", "jpeg"],
                        key=f"e_logo_{p['id']}", label_visibility="collapsed",
                    )
                    if e_logo:
                        st.image(e_logo, width=100)
                    elif p.get("logo_url"):
                        st.image(p["logo_url"], width=100)

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
                                    )
                                    st.session_state[_edit_key] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"更新エラー: {e}")
                with btn_cancel:
                    if st.button("キャンセル", use_container_width=True,
                                 key=f"cancel_prod_{p['id']}"):
                        st.session_state[_edit_key] = False
                        st.rerun()
