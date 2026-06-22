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

missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"APIキーが設定されていません: `{', '.join(missing)}`")
    st.info("`.env` ファイルを作成して API キーを設定してください（`.env.example` 参照）。")
    st.stop()

pg = st.navigation([
    st.Page("pages/analysis.py", title="訴求軸の検討", icon="🎯"),
    st.Page("pages/banner.py", title="バナー生成", icon="🖼️"),
])
pg.run()
