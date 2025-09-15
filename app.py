import streamlit as st, os, base64, requests, json
from agents import load_config, Runner

# ---------- 1. 读取 secrets ----------
secrets = st.secrets            # 本地或 Streamlit Cloud 通用
DASH_KEY  = secrets["DASHSCOPE_API_KEY"]
MINI_KEY  = secrets["MINIMAX_API_KEY"]
GROUP_ID  = secrets["MINIMAX_GROUP_ID"]

# ---------- 2. 注入环境变量（供 YAML 占位符使用） ----------
os.environ.update({
    "DASHSCOPE_API_KEY": DASH_KEY,
    "MINIMAX_API_KEY":   MINI_KEY,
    "MINIMAX_GROUP_ID":  GROUP_ID,
})

# ---------- 3. Streamlit UI ----------
st.set_page_config(page_title="千问×海螺作画", page_icon="🎨")
st.title("千问×海螺 · 一句话出图")
idea = st.text_area("用中文描述想要的画面", height=80)
go = st.button("生成", type="primary")

# ---------- 4. 生成 & 下载 ----------
if go:
    if not idea.strip():
        st.warning("请输入描述"); st.stop()
    cfg = load_config("agents.yaml")
    with st.spinner("Agent 工作流运行中…"):
        result = Runner.run_flow(cfg, initial_input=idea)
    md = result.final_output
    st.markdown(md, unsafe_allow_html=True)          # 展示图片
    # 下载按钮
    b64 = md.split("base64,")[1].split(")")[0]
    st.download_button("📥 下载图片", data=base64.b64decode(b64),
                       file_name="generated.png", mime="image/png")
