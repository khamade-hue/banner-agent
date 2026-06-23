"""SNS Banner Ad Generator — entry point."""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

if hasattr(st, "secrets"):
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        if k in st.secrets and not os.getenv(k):
            os.environ[k] = st.secrets[k]

st.set_page_config(
    page_title="Banner Ad Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
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
[data-testid="stExpander"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary span { color: #94a3b8 !important; }
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
[data-testid="stMultiSelect"] > div > div {
    background: #1e293b !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
}
/* Multiselect tags */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: rgba(59,130,246,0.2) !important;
    color: #93c5fd !important;
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
</style>
""", unsafe_allow_html=True)

missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"APIキーが設定されていません: `{', '.join(missing)}`")
    st.info("`.env` ファイルを作成して API キーを設定してください（`.env.example` 参照）。")
    st.stop()

pg = st.navigation([
    st.Page("pages/analysis.py",      title="訴求軸の検討",   icon="🎯"),
    st.Page("pages/banner.py",        title="バナー生成",     icon="🖼️"),
    st.Page("pages/saved_axes.py",    title="保存済み訴求軸", icon="📋"),
    st.Page("pages/saved_banners.py", title="保存済みバナー", icon="📁"),
])
pg.run()
