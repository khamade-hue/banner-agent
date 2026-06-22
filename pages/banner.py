"""Page 2: バナー画像生成エージェント"""

import io
import os
import sys
import zipfile
from datetime import datetime

import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import generate_banner_prompts, refine_banner_prompt
from image_gen import generate_image, add_text_overlay
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


# ── Load saved axes ───────────────────────────────────────────────────────────
axes = load_axes()

st.title("バナー画像生成")
st.caption("Claude がクリエイティブ戦略を立案 → gpt-image-2 で各プラットフォーム向け画像を生成")

if not axes:
    st.warning("訴求軸がまだ保存されていません。")
    st.info("先に「訴求軸の検討」ページで訴求軸を生成・保存してください。")
    if st.button("訴求軸の検討ページへ", type="primary"):
        st.switch_page("pages/analysis.py")
    st.stop()


# ── Sidebar: generation settings ─────────────────────────────────────────────
with st.sidebar:
    st.header("生成設定")

    axis_labels = [f"{a['axis']} — {a['product_name']}" for a in axes]
    selected_idx = st.selectbox(
        "訴求軸を選択 *",
        range(len(axes)),
        format_func=lambda i: axis_labels[i],
    )
    selected_axis = axes[selected_idx]

    with st.expander("選択中の訴求軸の詳細"):
        st.markdown(f"**{selected_axis['axis']}**")
        st.markdown(selected_axis.get("description", ""))
        st.caption(f"ターゲット: {selected_axis.get('target_segment', '—')}")
        ctx = selected_axis.get("product_context", {})
        if ctx.get("value_proposition"):
            st.caption(f"提供価値: {ctx['value_proposition']}")

    st.divider()

    objective_label = st.selectbox("目的 *", list(OBJECTIVE.keys()))
    tonmana_label = st.selectbox("トンマナ *", list(TONMANA.keys()))

    st.divider()

    platform_names = [p.name for p in PLATFORMS]
    selected_platform_names = st.multiselect(
        "バナーの用途（プラットフォーム）*",
        platform_names,
        default=["Instagram Square", "X (Twitter)", "Facebook"],
    )

    num_variations = st.selectbox(
        "出力枚数（バリエーション数）", [1, 2, 3, 4, 5], index=2
    )

    # ── Reference image ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("**リファレンス画像（任意）**")
    ref_option = st.radio(
        "リファレンスの種類",
        ["なし", "画像をアップロード", "保存済みバナーから選択"],
        key="ref_option",
    )

    reference_image: Image.Image | None = None

    if ref_option == "画像をアップロード":
        uploaded = st.file_uploader(
            "画像を選択", type=["png", "jpg", "jpeg"], key="ref_upload"
        )
        if uploaded:
            reference_image = Image.open(uploaded).convert("RGB")
            st.image(reference_image, caption="リファレンス", use_container_width=True)

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
                    banner_opts[label] = b["platforms"][0]["path"]

            if banner_opts:
                sel_label = st.selectbox("バナーを選択", list(banner_opts.keys()))
                sel_path = banner_opts[sel_label]
                if os.path.exists(sel_path):
                    reference_image = Image.open(sel_path).convert("RGB")
                    st.image(reference_image, caption="リファレンス", use_container_width=True)
                else:
                    st.warning("画像ファイルが見つかりません")

    st.divider()
    generate_btn = st.button("画像生成", type="primary", use_container_width=True)


# ── Generation ───────────────────────────────────────────────────────────────
if generate_btn:
    if not selected_platform_names:
        st.sidebar.error("プラットフォームを1つ以上選択してください")
        st.stop()

    selected_platforms = [p for p in PLATFORMS if p.name in selected_platform_names]
    tonmana_desc = TONMANA[tonmana_label]
    objective_desc = OBJECTIVE[objective_label]

    with st.status("バナーを生成中...", expanded=True) as status:
        st.write("**Step 1 / 3** — Claude がクリエイティブプロンプトを生成中")
        try:
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
            )
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
                base_img = generate_image(
                    v["prompt"],
                    reference_image=reference_image,
                )
            except RuntimeError as e:
                st.error(f"画像生成エラー:\n\n```\n{e}\n```")
                st.stop()
            platform_images = [
                (platform, add_text_overlay(img, v.get("headline", ""), v.get("subtext", "")))
                for platform, img in resize_for_selected_platforms(base_img, selected_platforms)
            ]
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

    st.session_state["gen_results"] = results
    st.session_state["gen_axis"] = selected_axis
    st.session_state["gen_platforms"] = selected_platforms
    st.session_state["gen_tonmana"] = tonmana_label
    st.session_state["gen_objective"] = objective_label


# ── Results display ───────────────────────────────────────────────────────────
if "gen_results" not in st.session_state:
    st.info("左サイドバーで設定を入力し「画像生成」を押してください。")
    st.stop()

results = st.session_state["gen_results"]
current_axis = st.session_state.get("gen_axis", {})
current_platforms = st.session_state.get("gen_platforms", [])

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
        if v.get("headline"):
            st.markdown(f"**コピー:** {v['headline']}")
            if v.get("subtext"):
                st.caption(v["subtext"])
        st.markdown(f"**戦略:** {v['rationale']}")
        with st.expander("生成プロンプトを見る"):
            st.code(v["prompt"], language=None)

        st.markdown("**プラットフォーム別プレビュー**")
        chunk = 4
        for row_start in range(0, len(platform_images), chunk):
            row = platform_images[row_start: row_start + chunk]
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

        # ── Revision section ──────────────────────────────────────────────────
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
                        new_prompt = refine_banner_prompt(v["prompt"], revision_text)
                        new_base_img = generate_image(
                            new_prompt, reference_image=reference_image
                        )
                        new_platform_images = [
                            (platform, add_text_overlay(img, v.get("headline", ""), v.get("subtext", "")))
                            for platform, img in resize_for_selected_platforms(new_base_img, current_platforms)
                        ]
                        updated_v = {
                            **v,
                            "prompt": new_prompt,
                            "label": v["label"] + "（修正済）",
                        }
                        # Save revised banner
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
