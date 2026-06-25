"""Page 2: バナー画像生成エージェント"""

import io
import os
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import generate_banner_prompts, refine_banner_prompt, refine_banner_part
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
    if st.button("訴求軸生成ページへ →", type="primary"):
        st.switch_page("pages/analysis.py")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 生成設定（メインエリア）
# ═══════════════════════════════════════════════════════════════════════════════

# ── 生成モード ────────────────────────────────────────────────────────────────
_section("生成モード", margin_top="0")
mode = st.radio(
    "生成モード",
    ["新規作成", "既存のバナーから作成"],
    horizontal=True,
    key="gen_mode",
    label_visibility="collapsed",
)

st.divider()

# ════════════════════════════════════════════
# 新規作成
# ════════════════════════════════════════════
if mode == "新規作成":
    # ── 目的 & トンマナ ────────────────────────────────────────────────────────
    _section("目的 & トンマナ", margin_top="0")
    col_obj, col_ton = st.columns(2)
    with col_obj:
        objective_label = st.selectbox("目的 *", list(OBJECTIVE.keys()), label_visibility="collapsed")
    with col_ton:
        tonmana_label = st.selectbox("トンマナ *", list(TONMANA.keys()), label_visibility="collapsed")

    # ── 訴求軸 ────────────────────────────────────────────────────────────────
    _section("訴求軸")
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

    # ── コピー ────────────────────────────────────────────────────────────────
    _section("バナーに入れるコピー")

    copy_s         = selected_axis.get("copy_suggestions", {})
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

    # ── プラットフォーム ──────────────────────────────────────────────────────
    _section("プラットフォーム")
    selected_platform_name = st.selectbox(
        "バナーの用途（プラットフォーム）*",
        [p.name for p in PLATFORMS],
        index=0,
        label_visibility="collapsed",
    )

    # ── バリエーション数 ──────────────────────────────────────────────────────
    _section("バリエーション数")
    num_variations = st.selectbox("バリエーション数", [1, 2, 3, 4, 5], index=2,
                                  label_visibility="collapsed")

    # ── リファレンス画像 ──────────────────────────────────────────────────────
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

# ════════════════════════════════════════════
# 既存のバナーから作成
# ════════════════════════════════════════════
else:
    all_saved = load_banners()
    banners_with_img = [
        b for b in sorted(all_saved, key=lambda x: x["created_at"], reverse=True)
        if b.get("platforms")
    ]
    if not banners_with_img:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.03);border:1px dashed #334155;'
            'border-radius:12px;padding:32px;text-align:center;color:#64748b">'
            '保存済みバナーがありません。まず「新規作成」でバナーを生成してください。</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    # 選択インデックスを初期化・クランプ
    if ("ex_selected_idx" not in st.session_state
            or st.session_state["ex_selected_idx"] >= len(banners_with_img)):
        st.session_state["ex_selected_idx"] = 0
    sel_idx = st.session_state["ex_selected_idx"]

    # ── バナーギャラリー ──────────────────────────────────────────────────────
    _section("ベースにするバナーを選択", margin_top="0")

    st.markdown(
        "<style>"
        "[data-testid='stColumn']:has(.ex-sel-marker){"
        "outline:3px solid #8b5cf6;border-radius:12px;padding:4px !important}"
        "</style>",
        unsafe_allow_html=True,
    )

    n_cols = 3
    for row_start in range(0, len(banners_with_img), n_cols):
        row  = banners_with_img[row_start:row_start + n_cols]
        cols = st.columns(n_cols)
        for c_idx, (col, b) in enumerate(zip(cols, row)):
            idx    = row_start + c_idx
            is_sel = sel_idx == idx
            with col:
                if is_sel:
                    st.markdown('<div class="ex-sel-marker" style="display:none"></div>',
                                unsafe_allow_html=True)
                img_url = b["platforms"][0].get("public_url", "")
                if img_url:
                    st.image(img_url, use_container_width=True)
                short_lbl = f"[{b.get('variation','')}] {b.get('label','')}"
                st.caption(short_lbl[:32] + ("…" if len(short_lbl) > 32 else ""))
                if is_sel:
                    st.markdown(
                        '<div style="text-align:center;color:#8b5cf6;font-size:0.72rem;'
                        'font-weight:700;margin-bottom:4px">✓ 選択中</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button("選択", key=f"ex_sel_{idx}",
                                 use_container_width=True, type="secondary"):
                        st.session_state["ex_selected_idx"] = idx
                        st.rerun()

    sel_banner = banners_with_img[sel_idx]

    # ── バリエーション数 ──────────────────────────────────────────────────────
    _section("バリエーション数")
    num_variations_ex = st.selectbox(
        "バリエーション数", [1, 2, 3], index=0,
        label_visibility="collapsed", key="ex_num_var",
    )

    # ── パーツ別修正指示 ──────────────────────────────────────────────────────
    _section("修正指示（任意）")
    st.markdown(
        '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:6px">'
        '① 修正するパーツ</div>',
        unsafe_allow_html=True,
    )
    EX_REVISION_PARTS = ["なし（そのまま再生成）", "ビジュアル", "メインキャッチ", "オファー・CTA", "特徴・アイコン"]
    sel_part_ex = st.radio(
        "修正するパーツ",
        EX_REVISION_PARTS,
        horizontal=True,
        key="ex_rev_part",
        label_visibility="collapsed",
    )

    target_elem_ex    = None
    rev_instructions_ex = ""

    if sel_part_ex != "なし（そのまま再生成）":
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:14px 0 6px">'
            '② 修正する要素（任意）</div>',
            unsafe_allow_html=True,
        )
        if sel_part_ex == "ビジュアル":
            st.markdown(
                '<div style="color:#475569;font-size:0.78rem;padding:6px 0">'
                'ビジュアル全体が対象です — ③に修正指示を入力してください</div>',
                unsafe_allow_html=True,
            )
        else:
            raw_elem = st.text_input(
                "修正する要素",
                placeholder="例: 「5万円」→ 変更先の金額、または現在のコピーテキスト（空欄可）",
                key="ex_target_elem",
                label_visibility="collapsed",
            )
            target_elem_ex = raw_elem.strip() or None

        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:14px 0 6px">'
            '③ 修正指示</div>',
            unsafe_allow_html=True,
        )
        rev_instructions_ex = st.text_area(
            "修正指示",
            placeholder="例: もっとインパクトのある写真に / シアンの光を強調して / 「期間限定」の訴求に変更",
            key="ex_rev_inst",
            label_visibility="collapsed",
            height=80,
        )

# ── 生成ボタン ────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
generate_btn = st.button("バナーを生成", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 生成処理
# ═══════════════════════════════════════════════════════════════════════════════
if generate_btn:
    if mode == "新規作成":
        selected_platforms = [p for p in PLATFORMS if p.name == selected_platform_name]
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
            n = len(variations)
            st.write(f"**Step 2 / 3** — gpt-image-2 で {n} 枚を並列生成中 {ref_note}")

            results = [None] * n
            preview_cols = st.columns(n)
            col_slots = [col.empty() for col in preview_cols]

            def _gen(item):
                idx, v = item
                img = generate_image(v["prompt"], reference_image=reference_image)
                return idx, v, resize_for_selected_platforms(img, selected_platforms)

            gen_errors = []
            with ThreadPoolExecutor(max_workers=n) as pool:
                futures = {pool.submit(_gen, (i, v)): i for i, v in enumerate(variations)}
                done = 0
                for fut in as_completed(futures):
                    try:
                        idx, v_res, pimgs = fut.result()
                    except RuntimeError as e:
                        gen_errors.append(str(e))
                        continue
                    done += 1
                    results[idx] = (v_res, pimgs)
                    col_slots[idx].image(
                        _img_to_bytes(pimgs[0][1]),
                        caption=f"[{v_res['variation']}] {v_res['label']}",
                        use_container_width=True,
                    )
                    st.write(f"  ✓ [{v_res['variation']}] {v_res['label']} 完了 ({done}/{n})")

            if gen_errors:
                st.error(f"画像生成エラー:\n\n```\n{gen_errors[0]}\n```")
                st.stop()

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
        st.session_state["gen_headline"]  = headline_copy.strip()
        st.session_state["gen_offer"]     = offer_copy.strip()
        st.session_state["gen_features"]  = features

    else:  # 既存のバナーから作成
        ex_platform_name = (
            sel_banner["platforms"][0].get("platform_name", PLATFORMS[0].name)
            if sel_banner.get("platforms") else PLATFORMS[0].name
        )
        ex_platforms = [p for p in PLATFORMS if p.name == ex_platform_name] or [PLATFORMS[0]]
        base_prompt  = sel_banner.get("prompt", "")

        # 元バナーをリファレンス画像として読み込み
        ex_ref_image: Image.Image | None = None
        first_url = sel_banner["platforms"][0].get("public_url", "") if sel_banner.get("platforms") else ""
        if first_url:
            try:
                ex_img_bytes = requests.get(first_url, timeout=10).content
                ex_ref_image = Image.open(io.BytesIO(ex_img_bytes)).convert("RGB")
            except Exception:
                pass

        has_revision = sel_part_ex != "なし（そのまま再生成）" and rev_instructions_ex.strip()

        with st.status("バナーを生成中...", expanded=True) as status:
            if has_revision:
                st.write(f"**Step 1 / 3** — Claude が「{sel_part_ex}」を修正中")
                try:
                    base_prompt = refine_banner_part(
                        base_prompt, sel_part_ex, target_elem_ex, rev_instructions_ex
                    )
                    st.write("✓ プロンプト修正完了")
                except Exception as e:
                    st.error(f"プロンプト修正エラー: {e}")
                    st.stop()
            else:
                st.write("**Step 1 / 3** — 元のプロンプトを使用")

            ref_note = "（元バナーをリファレンスに使用）" if ex_ref_image is not None else ""
            suffix     = f"（{sel_part_ex}修正）" if has_revision else "（再生成）"
            base_label = sel_banner.get("label", "").split("（")[0]
            n_ex = num_variations_ex
            st.write(f"**Step 2 / 3** — gpt-image-2 で {n_ex} 枚を並列生成中 {ref_note}")

            results = [None] * n_ex
            preview_cols_ex = st.columns(n_ex)
            col_slots_ex = [col.empty() for col in preview_cols_ex]

            def _gen_ex(i):
                img = generate_image(base_prompt, reference_image=ex_ref_image)
                pimgs = resize_for_selected_platforms(img, ex_platforms)
                v_dict = {
                    "variation": chr(65 + i),
                    "label": base_label + suffix,
                    "prompt": base_prompt,
                    "rationale": sel_banner.get("rationale", ""),
                }
                return i, v_dict, pimgs

            gen_errors_ex = []
            with ThreadPoolExecutor(max_workers=n_ex) as pool:
                futures_ex = {pool.submit(_gen_ex, i): i for i in range(n_ex)}
                done_ex = 0
                for fut in as_completed(futures_ex):
                    try:
                        idx, v_dict_res, pimgs = fut.result()
                    except RuntimeError as e:
                        gen_errors_ex.append(str(e))
                        continue
                    done_ex += 1
                    results[idx] = (v_dict_res, pimgs)
                    col_slots_ex[idx].image(
                        _img_to_bytes(pimgs[0][1]),
                        caption=f"[{v_dict_res['variation']}] {v_dict_res['label']}",
                        use_container_width=True,
                    )
                    st.write(f"  ✓ バリエーション {idx + 1} 完了 ({done_ex}/{n_ex})")

            if gen_errors_ex:
                st.error(f"画像生成エラー:\n\n```\n{gen_errors_ex[0]}\n```")
                st.stop()

            st.write("**Step 3 / 3** — バナーを保存中")
            for v, platform_images in results:
                save_banner_entry(
                    product_name=sel_banner.get("product_name", ""),
                    axis_label=sel_banner.get("axis", ""),
                    variation=v,
                    platform_images=platform_images,
                    tonmana=sel_banner.get("tonmana", ""),
                    objective=sel_banner.get("objective", ""),
                )
            st.write(f"✓ {len(results)} バリエーションを保存しました")
            status.update(label="生成完了！", state="complete", expanded=False)

        st.session_state["gen_results"]   = results
        st.session_state["gen_axis"]      = {
            "product_name": sel_banner.get("product_name", ""),
            "axis": sel_banner.get("axis", ""),
        }
        st.session_state["gen_platforms"] = ex_platforms
        st.session_state["gen_tonmana"]   = sel_banner.get("tonmana", "")
        st.session_state["gen_objective"] = sel_banner.get("objective", "")
        st.session_state["gen_headline"]  = ""
        st.session_state["gen_offer"]     = ""
        st.session_state["gen_features"]  = []


# ═══════════════════════════════════════════════════════════════════════════════
# 生成結果
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.get("gen_results"):
    st.stop()

results          = st.session_state["gen_results"]
current_axis     = st.session_state.get("gen_axis", {})
current_platforms = st.session_state.get("gen_platforms", [])

st.divider()

# 生成完了バナー
st.markdown(
    f'<div style="background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(16,185,129,0.04));'
    f'border:1px solid rgba(16,185,129,0.35);border-radius:12px;'
    f'padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
    f'<div style="color:#10b981;font-size:1.1rem">✓</div>'
    f'<div>'
    f'<div style="color:#10b981;font-weight:700;font-size:0.9rem">'
    f'{len(results)} バリエーション × {len(current_platforms)} プラットフォーム を生成・保存しました</div>'
    f'<div style="color:#6ee7b7;font-size:0.78rem;margin-top:2px">'
    f'「保存済みバナー」ページからいつでも確認・ダウンロードできます</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

col_title, col_saved, col_dl = st.columns([3, 1, 1])
with col_title:
    if current_axis:
        st.caption(
            f"訴求軸: {current_axis['axis']} ｜ "
            f"トンマナ: {st.session_state.get('gen_tonmana', '—')} ｜ "
            f"目的: {st.session_state.get('gen_objective', '—')}"
        )
with col_saved:
    if st.button("保存済みバナー →", type="secondary", use_container_width=True, key="goto_saved"):
        st.switch_page("pages/saved_banners.py")
with col_dl:
    st.download_button(
        "ZIP でダウンロード",
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
        st.markdown(
            '<div style="font-size:0.72rem;font-weight:700;color:#8b5cf6;'
            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:14px">'
            'パーツ別修正</div>',
            unsafe_allow_html=True,
        )

        # ① 修正するパーツ
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin-bottom:6px">'
            '① 修正するパーツ</div>',
            unsafe_allow_html=True,
        )
        REVISION_PARTS = ["ビジュアル", "メインキャッチ", "オファー・CTA", "特徴・アイコン"]
        sel_part = st.radio(
            "修正するパーツ",
            REVISION_PARTS,
            horizontal=True,
            key=f"rev_part_{tab_idx}",
            label_visibility="collapsed",
        )

        # ② 修正する要素
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:14px 0 6px">'
            '② 修正する要素</div>',
            unsafe_allow_html=True,
        )
        gen_headline = st.session_state.get("gen_headline", "")
        gen_offer    = st.session_state.get("gen_offer", "")
        gen_features = st.session_state.get("gen_features", [])
        target_elem  = None

        if sel_part == "ビジュアル":
            st.markdown(
                '<div style="color:#475569;font-size:0.78rem;padding:6px 0">'
                'ビジュアル全体が対象です — ③に修正指示を入力してください</div>',
                unsafe_allow_html=True,
            )
        elif sel_part == "メインキャッチ":
            if gen_headline:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.04);border:1px solid #334155;'
                    f'border-radius:8px;padding:8px 12px;font-size:0.82rem;color:#cbd5e1">'
                    f'現在: {gen_headline}</div>',
                    unsafe_allow_html=True,
                )
                target_elem = gen_headline
            else:
                st.caption("メインキャッチが設定されていません")
        elif sel_part == "オファー・CTA":
            if gen_offer:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.04);border:1px solid #334155;'
                    f'border-radius:8px;padding:8px 12px;font-size:0.82rem;color:#cbd5e1">'
                    f'現在: {gen_offer}</div>',
                    unsafe_allow_html=True,
                )
                target_elem = gen_offer
            else:
                st.caption("オファー・CTAが設定されていません — ③に追加したい内容を指示してください")
        elif sel_part == "特徴・アイコン":
            if gen_features:
                target_elem = st.selectbox(
                    "修正する特徴を選択",
                    gen_features,
                    key=f"rev_feat_{tab_idx}",
                    label_visibility="collapsed",
                )
            else:
                st.caption("特徴・アイコンが設定されていません")

        # ③ 修正指示
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#94a3b8;margin:14px 0 6px">'
            '③ 修正指示</div>',
            unsafe_allow_html=True,
        )
        rev_instructions = st.text_area(
            "修正指示",
            placeholder="例: もっとインパクトのある写真に / シアンの光を強調して / 「期間限定」の訴求に変更",
            key=f"rev_inst_{tab_idx}",
            label_visibility="collapsed",
            height=80,
        )

        if st.button(
            f"「{sel_part}」を修正して再生成",
            key=f"rev_part_btn_{tab_idx}",
            type="primary",
            use_container_width=True,
        ):
            if not rev_instructions.strip():
                st.warning("③ に修正指示を入力してください")
            else:
                with st.spinner(f"「{sel_part}」を修正して再生成中..."):
                    try:
                        new_prompt = refine_banner_part(
                            v["prompt"], sel_part, target_elem, rev_instructions
                        )
                        new_base_img = generate_image(new_prompt, reference_image=reference_image)
                        new_platform_images = resize_for_selected_platforms(
                            new_base_img, current_platforms
                        )
                        part_suffix = f" [{sel_part}修正]"
                        base_label  = v["label"].split(" [")[0]  # strip previous suffixes
                        updated_v   = {**v, "prompt": new_prompt, "label": base_label + part_suffix}
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
