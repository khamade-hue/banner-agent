"""Web UI for SNS Banner Ad Generator — Claude + gpt-image-1."""

import io
import os
import zipfile
from datetime import datetime

import streamlit as st
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Streamlit Community Cloud: inject secrets as env vars
if hasattr(st, "secrets"):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        if k in st.secrets and not os.getenv(k):
            os.environ[k] = st.secrets[k]

st.set_page_config(
    page_title="Banner Ad Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Banner Ad Generator")
st.caption("Claude がクリエイティブ戦略を立案 → gpt-image-1 で全プラットフォーム向け画像を生成")


# ── API key check ────────────────────────────────────────────────────────────
missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"APIキーが設定されていません: `{', '.join(missing)}`")
    st.info("Streamlit Cloud の場合: Settings → Secrets に追加してください。")
    st.stop()


# ── Sidebar: input form ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("キャンペーン設定")

    with st.form("banner_form"):
        brand_name = st.text_input("ブランド名 *", placeholder="例: ACME Corp")
        product    = st.text_input("商品・サービス *", placeholder="例: クラウド会計ソフト")
        message    = st.text_input("キャッチコピー *", placeholder="例: 経理の時間を半分に")
        target     = st.text_input("ターゲット層", value="20〜40代のビジネスパーソン")
        style      = st.text_input("ビジュアルスタイル", value="モダン・プロフェッショナル")

        st.divider()
        num_var = st.slider("A/B バリエーション数", 1, 5, 3)
        quality = st.select_slider("画像品質", ["low", "medium", "high"], value="high")

        submitted = st.form_submit_button(
            "バナーを生成する", type="primary", use_container_width=True
        )


# ── Helpers ──────────────────────────────────────────────────────────────────
def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _build_zip(results: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for v, platform_images in results:
            for platform, img in platform_images:
                fname = f"{v['variation']}_{v['label']}/{platform.filename}_{platform.width}x{platform.height}.png"
                zf.writestr(fname, _pil_to_bytes(img))
    return buf.getvalue()


# ── Generation ───────────────────────────────────────────────────────────────
if submitted:
    if not all([brand_name, product, message]):
        st.sidebar.error("ブランド名・商品・キャッチコピーは必須です")
        st.stop()

    from agent import generate_banner_prompts
    from image_gen import generate_image
    from platforms import resize_for_all_platforms

    results = []

    with st.status("生成中...", expanded=True) as status:

        st.write("**Step 1 / 3** — Claude がクリエイティブプロンプトを生成中")
        variations = generate_banner_prompts(
            brand_name=brand_name,
            product=product,
            message=message,
            style=style,
            target_audience=target,
            num_variations=num_var,
        )
        st.write(f"✓ {len(variations)} バリエーション確定")

        st.write("**Step 2 / 3** — gpt-image-1 で画像を生成中")
        for i, v in enumerate(variations):
            st.write(f"  [{v['variation']}] {v['label']} ({i + 1}/{len(variations)})")
            base_img       = generate_image(v["prompt"], quality=quality)
            platform_images = resize_for_all_platforms(base_img)
            results.append((v, platform_images))

        total = sum(len(pi) for _, pi in results)
        st.write(f"**Step 3 / 3** — 完了  ({total} ファイル)")
        status.update(label="生成完了！", state="complete", expanded=False)

    st.session_state["results"] = results


# ── Results ──────────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.info("左サイドバーでキャンペーン情報を入力して「バナーを生成する」を押してください。")
    st.stop()

results = st.session_state["results"]

col_title, col_dl = st.columns([3, 1])
with col_title:
    total = sum(len(pi) for _, pi in results)
    st.subheader(f"生成結果  —  {len(results)} バリエーション × {total // len(results)} サイズ")
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

for tab, (v, platform_images) in zip(tabs, results):
    with tab:
        st.markdown(f"**戦略:** {v['rationale']}")
        with st.expander("生成プロンプトを見る"):
            st.code(v["prompt"], language=None)

        st.markdown("**プラットフォーム別プレビュー**")

        chunk = 4
        for row_start in range(0, len(platform_images), chunk):
            row = platform_images[row_start : row_start + chunk]
            cols = st.columns(len(row))
            for col, (platform, img) in zip(cols, row):
                with col:
                    st.image(img, caption=f"{platform.name}\n{platform.width}×{platform.height}", use_container_width=True)
                    st.download_button(
                        f"↓ {platform.filename}_{platform.width}x{platform.height}.png",
                        data=_pil_to_bytes(img),
                        file_name=f"{platform.filename}_{platform.width}x{platform.height}.png",
                        mime="image/png",
                        key=f"dl_{v['variation']}_{platform.filename}",
                        use_container_width=True,
                    )
