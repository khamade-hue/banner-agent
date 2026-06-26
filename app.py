"""SNS Banner Ad Generator — entry point."""

import base64
import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

if hasattr(st, "secrets"):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        if k in st.secrets and not os.getenv(k):
            os.environ[k] = st.secrets[k]

_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 50">'
    '<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">'
    '<stop offset="30%" stop-color="#f1f5f9"/>'
    '<stop offset="100%" stop-color="#93c5fd"/>'
    '</linearGradient></defs>'
    '<text x="2" y="30" '
    'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',system-ui,sans-serif" '
    'font-weight="800" font-size="20" fill="url(#g)" letter-spacing="0">'
    'Raku Raku Banner</text>'
    '<rect x="2" y="41" width="32" height="3" rx="1.5" fill="#3b82f6"/>'
    '<rect x="36" y="41" width="11" height="3" rx="1.5" fill="#3b82f6" fill-opacity="0.45"/>'
    '<rect x="49" y="41" width="6" height="3" rx="1.5" fill="#3b82f6" fill-opacity="0.2"/>'
    '</svg>'
)
_LOGO_URL = "data:image/svg+xml;base64," + base64.b64encode(_LOGO_SVG.encode()).decode()

st.set_page_config(
    page_title="Banner Ad Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700;800&display=swap');

/* ═══════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════ */
html { font-size: 14px; }
.stApp { background: #0f172a; }
.main .block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1040px;
}

/* Top toolbar */
[data-testid="stHeader"] {
    background: #0f172a !important;
    border-bottom: 1px solid #1e293b !important;
}
[data-testid="stDecoration"] { display: none !important; }

/* Header buttons: use <header> tag selector for specificity */
header button {
    color: #94a3b8 !important;
    background: transparent !important;
    border-radius: 6px !important;
}
header button:hover {
    color: #e2e8f0 !important;
    background: rgba(255,255,255,0.08) !important;
}
header button span,
header button p {
    color: inherit !important;
}
header svg {
    fill: #94a3b8 !important;
}
header button:hover svg {
    fill: #e2e8f0 !important;
}

/* App running spinner */
[data-testid="stAppRunningIcon"] { opacity: 0.55 !important; }

/* ═══════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════ */

/* ── 固定幅 ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {
    width: 224px !important;
    min-width: 224px !important;
}

/* ── 折りたたみボタン & ヘッダーハンバーガーを非表示 ── */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarNavToggle"],
button[aria-label="Close sidebar"],
button[aria-label="Open sidebar"] {
    display: none !important;
}

/* ── ロゴエリア（st.logo が注入する要素）── */
[data-testid="stLogoSidebar"] {
    padding: 18px 16px 14px !important;
    background: #1e293b !important;
    overflow: visible !important;
}
[data-testid="stLogoSidebar"] a {
    display: block !important;
    overflow: visible !important;
}
[data-testid="stLogoSidebar"] img,
[data-testid="stLogoSidebar"] a img {
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    width: auto !important;
    max-width: none !important;
    object-fit: contain !important;
}

[data-testid="stSidebar"] {
    background: #1e293b !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not(button span),
[data-testid="stSidebar"] li {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #334155 !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div {
    background: #0f172a !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: #0f172a !important;
    border-color: #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] p,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] span,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] li {
    color: #94a3b8 !important;
}

/* ═══════════════════════════════════════════════
   MARKDOWN (main content text)
═══════════════════════════════════════════════ */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em {
    color: #cbd5e1 !important;
}
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    color: #e2e8f0 !important;
}
[data-testid="stCaptionContainer"] p {
    color: #475569 !important;
    font-size: 0.8rem !important;
}

/* ═══════════════════════════════════════════════
   STATUS WIDGET (st.status / st.spinner)
═══════════════════════════════════════════════ */
[data-testid="stStatusWidget"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
}
[data-testid="stStatusWidget"] p,
[data-testid="stStatusWidget"] summary,
[data-testid="stStatusWidget"] div:not([class*="spinner"]) {
    color: #cbd5e1 !important;
}
/* Spinner label */
[data-testid="stSpinner"] p { color: #94a3b8 !important; }

/* ═══════════════════════════════════════════════
   CONTAINERS
═══════════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 14px !important;
}
[data-testid="stVerticalBlockBorderWrapper"] p,
[data-testid="stVerticalBlockBorderWrapper"] li {
    color: #cbd5e1 !important;
}

/* ═══════════════════════════════════════════════
   EXPANDER
═══════════════════════════════════════════════ */
[data-testid="stExpander"],
[data-testid="stExpander"]:hover,
[data-testid="stExpander"]:focus-within {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] details,
[data-testid="stExpander"] details[open],
[data-testid="stExpander"] details > div {
    background: #1e293b !important;
    border-radius: 0 0 10px 10px !important;
}
[data-testid="stExpanderDetails"],
[data-testid="stExpanderDetails"] > div,
[data-testid="stExpanderDetails"] > div > div {
    background: #1e293b !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus {
    padding: 10px 14px !important;
    background: #1e293b !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] details[open] > summary {
    border-radius: 10px 10px 0 0 !important;
}
[data-testid="stExpander"] summary span {
    color: #cbd5e1 !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
}
[data-testid="stExpander"] summary:hover span { color: #f1f5f9 !important; }
[data-testid="stExpander"] p,
[data-testid="stExpander"] li { color: #cbd5e1 !important; }

/* ═══════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════ */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    caret-color: #e2e8f0 !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.18) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: #475569 !important;
}

/* ═══════════════════════════════════════════════
   SELECTBOX / MULTISELECT
═══════════════════════════════════════════════ */
[data-testid="stSelectbox"] > div > div {
    background: #1e293b !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stMultiSelect"] > div > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="input"],
[data-testid="stMultiSelect"] [data-baseweb="base-input"],
[data-testid="stMultiSelect"] [data-baseweb="base-input"] > div,
[data-testid="stMultiSelect"] [data-baseweb="base-input"] > div > div {
    background: #1e293b !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stMultiSelect"] input[type="text"] {
    background: transparent !important;
    color: #e2e8f0 !important;
}
/* Multiselect: selected tag chips */
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: #1e3a5f !important;
    border: 1px solid #3b82f6 !important;
    border-radius: 6px !important;
    padding: 2px 4px 2px 8px !important;
    margin: 2px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] *,
[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: #e2e8f0 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}
/* Dropdown chevron arrows (selectbox + multiselect toggle) */
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stSelectbox"] [data-baseweb="select"] svg path,
[data-testid="stMultiSelect"] [data-baseweb="select"] svg,
[data-testid="stMultiSelect"] [data-baseweb="select"] svg path {
    fill: #94a3b8 !important;
}
/* × close button inside tag — keep blue */
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg,
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg path,
[data-testid="stMultiSelect"] [data-baseweb="tag"] [role="presentation"],
[data-testid="stMultiSelect"] [data-baseweb="tag"] button {
    fill: #93c5fd !important;
    color: #93c5fd !important;
    opacity: 1 !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] [role="presentation"]:hover,
[data-testid="stMultiSelect"] [data-baseweb="tag"] button:hover {
    fill: #ffffff !important;
    color: #ffffff !important;
    background: rgba(255,255,255,0.15) !important;
    border-radius: 4px !important;
}
/* Dropdown option text */
[data-testid="stMultiSelect"] li {
    color: #cbd5e1 !important;
    background: #1e293b !important;
}
[data-testid="stMultiSelect"] li:hover,
[data-testid="stMultiSelect"] li[aria-selected="true"] {
    background: rgba(59,130,246,0.2) !important;
    color: #e2e8f0 !important;
}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */
button[kind="primary"] {
    background: linear-gradient(135deg,#3b82f6 0%,#2563eb 50%,#1d4ed8 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 15px rgba(59,130,246,0.35) !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(59,130,246,0.5) !important;
}
button[kind="primary"] p { color: #ffffff !important; }

button[kind="secondary"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #64748b !important;
}
button[kind="secondary"]:hover {
    border-color: #ef4444 !important;
    color: #ef4444 !important;
}
button[kind="secondary"] p { color: inherit !important; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 0.78rem !important;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
}
[data-testid="stDownloadButton"] button p { color: inherit !important; }

/* Form submit button */
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg,#3b82f6,#1d4ed8) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(59,130,246,0.35) !important;
}
[data-testid="stFormSubmitButton"] button p { color: #ffffff !important; }

/* ═══════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════ */
[data-testid="stTabs"] button {
    color: #475569 !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom-color: #3b82f6 !important;
}
[data-testid="stTabsContent"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 0 10px 10px 10px !important;
    padding: 1rem !important;
}

/* ═══════════════════════════════════════════════
   ALERTS (keep default colors, just round corners)
═══════════════════════════════════════════════ */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ═══════════════════════════════════════════════
   DIVIDERS
═══════════════════════════════════════════════ */
hr {
    border: none !important;
    border-top: 1px solid #1e293b !important;
    margin: 1.5rem 0 !important;
}

/* ═══════════════════════════════════════════════
   CODE
═══════════════════════════════════════════════ */
[data-testid="stCode"] {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
[data-testid="stCode"] code { color: #94a3b8 !important; }

/* ═══════════════════════════════════════════════
   FILE UPLOADER
═══════════════════════════════════════════════ */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzone"]:hover,
[data-testid="stFileUploaderDropzone"]:hover > div {
    border-color: #475569 !important;
    background: #243447 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {
    color: #64748b !important;
}
</style>
""", unsafe_allow_html=True)

st.logo(_LOGO_URL)

# CSS では Streamlit 内部の emotion クラスに勝てないため JS でインラインスタイルを強制
components.html(
    '<script>'
    '!function f(){'
    'try{'
    'var imgs=parent.document.querySelectorAll(\'[data-testid="stLogoSidebar"] img\');'
    'if(!imgs.length){setTimeout(f,150);return;}'
    'imgs.forEach(function(el){'
    'el.style.setProperty("height","44px","important");'
    'el.style.setProperty("max-height","44px","important");'
    'el.style.setProperty("min-height","44px","important");'
    'el.style.setProperty("width","auto","important");'
    'el.style.setProperty("max-width","none","important");'
    '});'
    '}catch(e){}'
    '}'
    'f();setTimeout(f,500);setTimeout(f,1500);'
    '</script>',
    height=0,
    scrolling=False,
)

missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY") if not os.getenv(k)]
if missing:
    st.error(f"APIキーが設定されていません: `{', '.join(missing)}`")
    st.info("`.env` ファイルを作成して API キーを設定してください（`.env.example` 参照）。")
    st.stop()

with st.sidebar:
    st.markdown(
        '<div style="background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.18);'
        'border-radius:10px;padding:12px 14px;margin-bottom:4px">'
        '<div style="font-size:0.68rem;font-weight:700;color:#3b82f6;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:10px">使い方フロー</div>'
        '<div style="font-size:0.8rem;color:#94a3b8;line-height:1.9">'
        '<span style="color:#3b82f6;font-weight:700">①</span>'
        ' <span style="color:#cbd5e1">商品登録</span><br>'
        '<span style="color:#475569;font-size:0.73rem;margin-left:14px">'
        '商品情報を登録</span><br>'
        '<span style="color:#3b82f6;font-weight:700">②</span>'
        ' <span style="color:#cbd5e1">訴求軸生成</span><br>'
        '<span style="color:#475569;font-size:0.73rem;margin-left:14px">'
        '商品を選択して3C分析</span><br>'
        '<span style="color:#3b82f6;font-weight:700">③</span>'
        ' <span style="color:#cbd5e1">バナー生成</span><br>'
        '<span style="color:#475569;font-size:0.73rem;margin-left:14px">'
        '訴求軸を選んで画像生成</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

pg = st.navigation([
    st.Page("pages/product.py",       title="商品登録",       icon="📦"),
    st.Page("pages/analysis.py",      title="訴求軸生成",     icon="🎯"),
    st.Page("pages/banner.py",        title="バナー生成",     icon="🖼️"),
    st.Page("pages/saved_axes.py",    title="保存済み訴求軸", icon="📋"),
    st.Page("pages/saved_banners.py", title="保存済みバナー", icon="📁"),
])
pg.run()
