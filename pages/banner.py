"""Page 2: バナー画像生成エージェント"""

import io
import os
import sys
import zipfile
from datetime import datetime

import requests
import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import generate_banner_prompts, refine_banner_prompt
from image_gen import generate_image
from platforms import PLATFORMS, resize_for_selected_platforms
from state import load_axes, load_banners, save_banner_entry

# ── トンマナ / 目的 定義 ──────────────────────────────────────────────────────
TONMANA = {
    "モダン・ミニマル": "modern minimalist: clean geometric composition, ample white space, muted neutral palette (white/light gray/black), simple elegant forms, understated sophistication",
    "プロフェッショナル・信頼感": "professional and trustworthy: structured balanced composition, authoritative navy-gray-white palette, polished corporate aesthetic, conveys stability and credibility",
    "ポップ・カジュアル": "playful and casual: vibrant saturated colors, energetic dynamic layout, bold graphic shapes, youthful approachable feel",
    "ラグジュアリー・高級感": "luxury premium: deep rich tones (black/gold/deep burgundy), dramatic chiaroscuro lighting, exclusive sophisticated atmosphere, opulent textures",
    "エネルギッシュ・ダイナミック": "energetic and dynamic: bold diagonal lines, high-contrast vivid colors, sense of speed and momentum, powerful impactful composition",
    "ナチュラル・オーガニック": "natural and organic: earthy warm tones (sage green/warm beige/terracotta), soft natural textures, wholesome honest aesthetic, nature-inspired elements",
    "テック・イノベーティブ": "tech-forward and innovative: dark background, electric neon accent colors (blue/cyan/purple), futuristic geometric elements, cutting-edge digital aesthetic",
    "ウォーム・フレンドリー": "warm and friendly: soft warm colors (peach/warm yellow/coral), inviting comfortable composition, heartfelt approachable mood, human-centered",
}

OBJECTIVE = {
    "認知拡大（ブランディング）": "brand awareness — striking and memorable, strong brand world-building, aspirational and inspiring, makes the viewer want to know more",
    "クリック促進（CTR向上）": "CTR optimization — visually arresting with a clear focal point, creates curiosity and desire, irresistible visual pull",
    "コンバージョン（購入・申込）": "direct conversion — clearly conveys the core product benefit and value, builds immediate trust, creates desire to act now",
    "リターゲティング（再訪問促進）": "retargeting — reinforces familiarity with the product, warm and inviting re-engagement tone, reminds the viewer of the value they saw before",
    "シーズン・キャンペーン": "seasonal campaign — timely and festive elements, limited-time energy, celebratory and urgent mood",
}


def _img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _build_zip(results: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for v, platform_images in results:
            for platform, img in platform_images:
                fname = (
                    f"{v['variation']}_{v['label']}/"
                    f"{platform.filename}_{platform.width}x{platform.height}.png"
                )
                zf.writestr(fname, _img_to_bytes(img))
    return buf.getvalue()


def _section(label: str, margin_top: str = "24px") -> None:
    st.markdown(
        f'<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin:{margin_top} 0 10px">{label}</div>',
        unsafe_allow_html=True,
    )


# ── Load saved axes ───────────────────────────────────────────────────────────
axes = load_axes()

st.markdown(
    '<div style="background:linear-gradient(135deg,#0f2744 0%,#1e1b4b 60%,#312e81 100%);'
    'padding:32px 36px;border-radius:20px;margin-bottom:28px;'
    'border:1px solid rgba(139,92,246,0.3);'
    'box-shadow:0 8px 32px rgba(99,102,241,0.2),inset 0 1px 0 rgba(255,255,255,0.07)">'
    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
    '<div style="background:rgba(139,92,246,0.25);border:1px solid rgba(139,92,246,0.4);'
    'border-radius:8px;padding:3px 10px;font-size:0.72rem;font-weight:700;'
    'color:#c4b5fd;letter-spacing:0.1em;text-transform:uppercase">Step 2 / 2</div>'
    '</div>'
    '<h1 style="color:#e2e8f0;margin:0 0 10px;font-size:2rem;font-weight:800;'
    'line-height:1.15;letter-spacing:-0.02em">バナー画像生成</h1>'
    '<p style="color:#a5b4fc;margin:0;font-size:0.9rem;line-height:1.6;max-width:560px">'
    'Claude がデザインブリーフを作成し、gpt-image-2 が各プラットフォーム向けのバナーを生成します'
    '</p></div>',
    unsafe_allow_html=True,
)

if not axes:
    st.markdown(
        '<div style="background:linear-gradient(145deg,#1e293b,#162032);border:1px dashed #334155;'
        'border-radius:14px;padding:48px;text-align:center">'
        '<div style="font-size:3rem;margin-bottom:16px">🎯</div>'
        '<div style="color:#f1f5f9;font-size:1.1rem;font-weight:700;margin-bottom:8px">'
        '訴求軸がまだ保存されていません</div>'
        '<div style="color:#64748b;font-size:0.875rem;margin-bottom:24px">'
        '先に「訴求軸の検討」ページで3C分析を実施して訴求軸を保存してください</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("訴求軸の検討ページへ →", type="primary"):
        st.switch_page("pages/analysis.py")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 生成設定（メインエリア）
# ═══════════════════════════════════════════════════════════════════════════════

# ── 訴求軸 ────────────────────────────────────────────────────────────────────
_section("訴求軸", margin_top="0")
axis_labels  = [f"{a['axis']} — {a['product_name']}" for a in axes]
selected_idx = st.selectbox(
    "訴求軸を選択 *",
    range(len(axes)),
    format_func=lambda i: axis_labels[i],
    label_visibility="collapsed",
)
selected_axis = axes[selected_idx]

with st.expander("選択中の訴求軸の詳細"):
    st.markdown(f"**{selected_axis['axis']}**")
    st.markdown(selected_axis.get("description", ""))
    st.caption(f"ターゲット: {selected_axis.get('target_segment', '—')}")
    ctx = selected_axis.get("product_context", {})
    if ctx.get("value_proposition"):
        st.caption(f"提供価値: {ctx['value_proposition']}")

# ── 目的 & トンマナ ────────────────────────────────────────────────────────────
_section("目的 & トンマナ")
col_obj, col_ton = st.columns(2)
with col_obj:
    objective_label = st.selectbox("目的 *", list(OBJECTIVE.keys()), label_visibility="collapsed")
with col_ton:
    tonmana_label = st.selectbox("トンマナ *", list(TONMANA.keys()), label_visibility="collapsed")

# ── コピー ─────────────────────────────────────────────────────────────────────
_section("バナーに入れるコピー")

copy_s        = selected_axis.get("copy_suggestions", {})
headlines_opts = copy_s.get("headlines", [])
offers_opts    = copy_s.get("offers", [])
features_opts  = copy_s.get("features", [])

col_hl, col_of = st.columns(2)
with col_hl:
    st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">メインキャッチ</div>', unsafe_allow_html=True)
    if headlines_opts:
        hl_sel = st.selectbox("メインキャッチ", headlines_opts + ["カスタム入力..."],
                              key="hl_sel", label_visibility="collapsed")
        headline_copy = st.text_input("キャッチを入力", key="hl_custom",
                                      label_visibility="collapsed") if hl_sel == "カスタム入力..." else hl_sel
    else:
        headline_copy = st.text_input("メインキャッチ（任意）",
                                      placeholder="例: 制作費、10分の1でいい。",
                                      label_visibility="collapsed")

with col_of:
    st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">オファー / CTA</div>', unsafe_allow_html=True)
    if offers_opts:
        of_sel = st.selectbox("オファー / CTA", ["なし"] + offers_opts + ["カスタム入力..."],
                              key="of_sel", label_visibility="collapsed")
        if of_sel == "カスタム入力...":
            offer_copy = st.text_input("オファーを入力", key="of_custom", label_visibility="collapsed")
        elif of_sel == "なし":
            offer_copy = ""
        else:
            offer_copy = of_sel
    else:
        offer_copy = st.text_input("オファー / CTA（任意）",
                                   placeholder="例: 今なら1件まるごと無料",
                                   label_visibility="collapsed")

st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin:10px 0 4px">特徴・アイコン</div>', unsafe_allow_html=True)
if features_opts:
    selected_features = st.multiselect("特徴・アイコン", features_opts,
                                       default=features_opts, key="feat_sel",
                                       label_visibility="collapsed")
    features_text = ""
else:
    selected_features = []
    features_text = st.text_area(
        "特徴・アイコン（1行1項目、任意）",
        placeholder="最短3営業日で納品\n修正回数無制限\nプロのディレクター監修\n著作権譲渡・商用利用OK",
        height=90,
        label_visibility="collapsed",
    )

# ── プラットフォーム & バリエーション ──────────────────────────────────────────
_section("プラットフォーム & バリエーション")
col_pf, col_var = st.columns([3, 1])
with col_pf:
    selected_platform_names = st.multiselect(
        "バナーの用途（プラットフォーム）*",
        [p.name for p in PLATFORMS],
        default=["Instagram Square", "X (Twitter)", "Facebook"],
        label_visibility="collapsed",
    )
with col_var:
    st.markdown('<div style="font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:4px">バリエーション数</div>', unsafe_allow_html=True)
    num_variations = st.selectbox("バリエーション数", [1, 2, 3, 4, 5], index=2,
                                  label_visibility="collapsed")

# ── リファレンス画像 ──────────────────────────────────────────────────────────
_section("リファレンス画像（任意）")
ref_option = st.radio(
    "リファレンスの種類",
    ["なし", "画像をアップロード", "保存済みバナーから選択"],
    horizontal=True,
    key="ref_option",
    label_visibility="collapsed",
)

reference_image: Image.Image | None = None

if ref_option == "画像をアップロード":
    uploaded = st.file_uploader("画像を選択", type=["png", "jpg", "jpeg"],
                                key="ref_upload", label_visibility="collapsed")
    if uploaded:
        reference_image = Image.open(uploaded).convert("RGB")
        st.image(reference_image, caption="リファレンス", width=200)

elif ref_option == "保存済みバナーから選択":
    saved_banners = load_banners()
    if not saved_banners:
        st.info("保存済みバナーがありません")
    else:
        banner_opts: dict[str, str] = {}
        for b in sorted(saved_banners, key=lambda x: x["created_at"], reverse=True):
            if b.get("platforms"):
                label = (
                    f"[{b['variation']}] {b['label']} — "
                    f"{b['product_name']} ({b['created_at'][:10]})"
                )
                banner_opts[label] = b["platforms"][0].get("public_url", "")
        if banner_opts:
            sel_label = st.selectbox("バナーを選択", list(banner_opts.keys()),
                                     label_visibility="collapsed")
            sel_url = banner_opts[sel_label]
            if sel_url:
                try:
                    img_bytes = requests.get(sel_url, timeout=10).content
                    reference_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    st.image(reference_image, caption="リファレンス", width=200)
                except Exception:
                    st.warning("画像の読み込みに失敗しました")

# ── 生成ボタン ────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
generate_btn = st.button("バナーを生成", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 生成処理
# ═══════════════════════════════════════════════════════════════════════════════
if generate_btn:
    if not selected_platform_names:
        st.error("プラットフォームを1つ以上選択してください")
        st.stop()

    selected_platforms = [p for p in PLATFORMS if p.name in selected_platform_names]
    tonmana_desc   = TONMANA[tonmana_label]
    objective_desc = OBJECTIVE[objective_label]

    with st.status("バナーを生成中...", expanded=True) as status:
        st.write("**Step 1 / 3** — Claude がクリエイティブプロンプトを生成中")
        try:
            features = (
                selected_features if features_opts
                else [f.strip() for f in features_text.splitlines() if f.strip()]
            )
            variations = generate_banner_prompts(
                brand_name=selected_axis["product_name"],
                product=selected_axis["product_name"],
                message=selected_axis["description"],
                tonmana=tonmana_desc,
                target_audience=selected_axis.get("target_segment", ""),
                num_variations=num_variations,
                appeal_axis=selected_axis,
                product_context=selected_axis.get("product_context"),
                objective=objective_desc,
                headline_copy=headline_copy.strip(),
                offer_copy=offer_copy.strip(),
                features=features,
            )
            if not variations:
                st.error("バリエーションが生成されませんでした。再度「バナーを生成」を押してください。")
                st.stop()
            st.write(f"✓ {len(variations)} バリエーション確定")
        except Exception as e:
            st.error(f"プロンプト生成エラー: {e}")
            st.stop()

        ref_note = "（リファレンスあり）" if reference_image is not None else ""
        st.write(f"**Step 2 / 3** — gpt-image-2 で画像を生成中 {ref_note}")
        results = []
        for i, v in enumerate(variations):
            st.write(f"  [{v['variation']}] {v['label']} ({i + 1}/{len(variations)})")
            try:
                base_img = generate_image(v["prompt"], reference_image=reference_image)
            except RuntimeError as e:
                st.error(f"画像生成エラー:\n\n```\n{e}\n```")
                st.stop()
            platform_images = resize_for_selected_platforms(base_img, selected_platforms)
            results.append((v, platform_images))

        st.write("**Step 3 / 3** — バナーを保存中")
        for v, platform_images in results:
            save_banner_entry(
                product_name=selected_axis["product_name"],
                axis_label=selected_axis["axis"],
                variation=v,
                platform_images=platform_images,
                tonmana=tonmana_label,
                objective=objective_label,
            )
        st.write(f"✓ {len(results)} バリエーションを保存しました")
        status.update(label="生成完了！", state="complete", expanded=False)

    st.session_state["gen_results"]   = results
    st.session_state["gen_axis"]      = selected_axis
    st.session_state["gen_platforms"] = selected_platforms
    st.session_state["gen_tonmana"]   = tonmana_label
    st.session_state["gen_objective"] = objective_label


# ═══════════════════════════════════════════════════════════════════════════════
# 生成結果
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.get("gen_results"):
    st.stop()

results          = st.session_state["gen_results"]
current_axis     = st.session_state.get("gen_axis", {})
current_platforms = st.session_state.get("gen_platforms", [])

st.divider()

col_title, col_dl = st.columns([3, 1])
with col_title:
    st.subheader(
        f"生成結果 — {len(results)} バリエーション × {len(current_platforms)} プラットフォーム"
    )
    if current_axis:
        st.caption(
            f"訴求軸: {current_axis['axis']} ｜ "
            f"トンマナ: {st.session_state.get('gen_tonmana', '—')} ｜ "
            f"目的: {st.session_state.get('gen_objective', '—')}"
        )
with col_dl:
    st.download_button(
        "全ファイルを ZIP でダウンロード",
        data=_build_zip(results),
        file_name=f"banners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        use_container_width=True,
    )

st.divider()

tabs = st.tabs([f"[{v['variation']}] {v['label']}" for v, _ in results])

for tab_idx, (tab, (v, platform_images)) in enumerate(zip(tabs, results)):
    with tab:
        st.markdown(f"**戦略:** {v['rationale']}")
        with st.expander("生成プロンプトを見る"):
            st.code(v["prompt"], language=None)

        st.markdown("**プラットフォーム別プレビュー**")
        chunk = 4
        for row_start in range(0, len(platform_images), chunk):
            row  = platform_images[row_start: row_start + chunk]
            cols = st.columns(len(row))
            for col, (platform, img) in zip(cols, row):
                with col:
                    st.image(
                        img,
                        caption=f"{platform.name}\n{platform.width}×{platform.height}",
                        use_container_width=True,
                    )
                    st.download_button(
                        f"↓ {platform.filename}_{platform.width}x{platform.height}.png",
                        data=_img_to_bytes(img),
                        file_name=f"{platform.filename}_{platform.width}x{platform.height}.png",
                        mime="image/png",
                        key=f"dl_{tab_idx}_{platform.filename}",
                        use_container_width=True,
                    )

        st.divider()
        st.markdown("**修正指示**")
        revision_text = st.text_area(
            "修正指示",
            placeholder="例: 背景をもっと明るい色に変更して、より爽やかな印象にしてください",
            key=f"revision_text_{tab_idx}",
            label_visibility="collapsed",
        )
        if st.button("修正する", key=f"revise_btn_{tab_idx}", type="secondary"):
            if not revision_text.strip():
                st.warning("修正指示を入力してください")
            else:
                with st.spinner("プロンプトを修正し、画像を再生成中..."):
                    try:
                        new_prompt    = refine_banner_prompt(v["prompt"], revision_text)
                        new_base_img  = generate_image(new_prompt, reference_image=reference_image)
                        new_platform_images = resize_for_selected_platforms(new_base_img, current_platforms)
                        updated_v = {**v, "prompt": new_prompt, "label": v["label"] + "（修正済）"}
                        save_banner_entry(
                            product_name=current_axis.get("product_name", ""),
                            axis_label=current_axis.get("axis", ""),
                            variation=updated_v,
                            platform_images=new_platform_images,
                            tonmana=st.session_state.get("gen_tonmana", ""),
                            objective=st.session_state.get("gen_objective", ""),
                        )
                        updated = list(st.session_state["gen_results"])
                        updated[tab_idx] = (updated_v, new_platform_images)
                        st.session_state["gen_results"] = updated
                        st.rerun()
                    except Exception as e:
                        st.error(f"修正エラー: {e}")
