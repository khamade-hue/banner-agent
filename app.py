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
/* ── Base ── */
.stApp { background: #0f172a; }
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1040px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1e293b !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size:0.78rem !important; font-weight:600 !important; text-transform:uppercase; letter-spacing:0.07em; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div {
    background: #0f172a !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] hr { border-color: #334155 !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #334155 !important;
    background: #0f172a !important;
    border-radius: 10px !important;
}

/* ── Inputs (main area) ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.18) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label { color: #94a3b8 !important; font-size:0.8rem !important; font-weight:600 !important; }

/* ── Selectbox (main area) ── */
[data-testid="stSelectbox"] > div > div {
    background: #1e293b !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
}
[data-testid="stSelectbox"] label { color: #94a3b8 !important; font-size:0.8rem !important; font-weight:600 !important; }
[data-testid="stMultiSelect"] > div > div {
    background: #1e293b !important;
    border-color: #334155 !important;
    border-radius: 8px !important;
}
[data-testid="stMultiSelect"] label { color: #94a3b8 !important; font-size:0.8rem !important; font-weight:600 !important; }

/* ── Buttons ── */
button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #1d4ed8 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 15px rgba(59,130,246,0.4) !important;
    transition: all 0.2s !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(59,130,246,0.55) !important;
    transform: translateY(-1px) !important;
}
button[kind="secondary"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
}
button[kind="secondary"]:hover { border-color: #ef4444 !important; color: #ef4444 !important; }

/* ── Containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 14px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
[data-testid="stAlert"][data-baseweb="notification"] { background: #1e293b !important; border-color: #334155 !important; }

/* ── Dividers ── */
hr { border: none !important; border-top: 1px solid #1e293b !important; margin: 1.5rem 0 !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { color: #94a3b8 !important; }

/* ── Tabs ── */
[data-testid="stTabs"] button {
    color: #64748b !important;
    font-weight: 600 !important;
    border-radius: 8px 8px 0 0 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] { color: #3b82f6 !important; }
[data-testid="stTabsContent"] { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 0 10px 10px 10px !important; padding: 1rem !important; }

/* ── Typography ── */
h1,h2,h3,h4,h5,h6,p,span,div,li { color: #f1f5f9; }
[data-testid="stCaptionContainer"] p { color: #64748b !important; font-size: 0.8rem !important; }

/* ── Status ── */
[data-testid="stStatusWidget"] { background: #1e293b !important; border-color: #334155 !important; border-radius: 10px !important; }

/* ── Code block ── */
[data-testid="stCode"] { background: #0f172a !important; border: 1px solid #334155 !important; border-radius: 8px !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] button { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 8px !important; color: #94a3b8 !important; font-size: 0.78rem !important; }
[data-testid="stDownloadButton"] button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)

missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"APIキーが設定されていません: `{', '.join(missing)}`")
    st.info("`.env` ファイルを作成して API キーを設定してください（`.env.example` 参照）。")
    st.stop()

pg = st.navigation([
    st.Page("pages/analysis.py", title="訴求軸の検討", icon="🎯"),
    st.Page("pages/banner.py", title="バナー生成", icon="🖼️"),
    st.Page("pages/saved_banners.py", title="保存済みバナー", icon="📁"),
])
pg.run()
