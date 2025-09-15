# app.py
import streamlit as st, os, base64, requests, json
import openai

# ---------- 1. 密钥 ----------
secrets = st.secrets
DASH_KEY = secrets["DASHSCOPE_API_KEY"]
MINI_KEY = secrets["MINIMAX_API_KEY"]
GROUP_ID = secrets["MINIMAX_GROUP_ID"]

# ---------- 2. 客户端 ----------
qwen = openai.OpenAI(api_key=DASH_KEY,
                     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
mini = openai.OpenAI(api_key=MINI_KEY,
                     base_url="https://api.minimax.chat/v1",
                     default_headers={"Group-Id": GROUP_ID})

# ---------- 3. 逻辑 ----------
def generate(prompt_zh: str):
    # 千问 → 英文提示词
    resp = qwen.chat.completions.create(
        model="qwen-max",
        messages=[{"role": "user", "content": (
            "你是资深平面设计师，请把中文需求精简成 1 句英文 Stable Diffusion 提示词，"
            "风格关键词用逗号分隔，不要解释，只输出提示词本身。\n\n"
            f"中文需求：{prompt_zh}")}]
    )
    en_prompt = resp.choices[0].message.content.strip()

    # 海螺 → 文生图
    r = mini.images.generate(
        model="hailuo-image",
        prompt=en_prompt,
        n=1,
        size="1024x1024",
        response_format="b64_json"
    )
    b64 = r.data[0].b64_json
    return f"![generated](data:image/png;base64,{b64})", en_prompt

# ---------- 4. UI ----------
st.set_page_config(page_title="千问×海螺作画", page_icon="🎨")
st.title("千问×海螺 · 一句话出图")
idea = st.text_area("用中文描述想要的画面", height=80)
go = st.button("生成", type="primary")

if go:
    if not idea.strip():
        st.warning("请输入描述"); st.stop()
    with st.spinner("生成中…"):
        md, en = generate(idea)
    st.markdown(md, unsafe_allow_html=True)
    b64 = md.split("base64,")[1].split(")")[0]
    st.download_button("📥 下载图片", data=base64.b64decode(b64),
                       file_name="generated.png", mime="image/png")
