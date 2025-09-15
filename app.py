# app.py
import streamlit as st
import openai
import base64
import dashscope

# ---------- 1. 读取 secrets ----------
secrets = st.secrets
DASH_KEY = secrets["DASHSCOPE_API_KEY"]   # 阿里百炼

# ---------- 2. 生成逻辑 ----------
def generate(prompt_zh: str):
    # ① 千问把中文需求翻译成英文提示词
    qwen = openai.OpenAI(
        api_key=DASH_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    resp = qwen.chat.completions.create(
        model="qwen-max",
        messages=[{"role": "user", "content": (
            "你是资深平面设计师，请把中文需求精简成 1 句英文 Stable Diffusion 提示词，"
            "风格关键词用逗号分隔，不要解释，只输出提示词本身。\n\n"
            f"中文需求：{prompt_zh}")}]
    )
    en_prompt = resp.choices[0].message.content.strip()

    # ② 千问文生图（DashScope 原生接口）
    task = dashscope.ImageSynthesis.call(
        model="wanx-v1",
        prompt=en_prompt,
        n=1,
        size="1024*1024",   # 星号
        format="base64"
    )
    if task.status_code != 200:
        raise RuntimeError(f"DashScope 图像生成失败：{task.status_code} {task.message}")
    b64 = task.output.results[0].base64_data
    return f"![generated](data:image/png;base64,{b64})", en_prompt

# ---------- 3. UI ----------
st.set_page_config(page_title="千问作画", page_icon="🎨")
st.title("千问 · 一句话出图")
idea = st.text_area("用中文描述想要的画面", height=80)
go = st.button("生成", type="primary")

if go:
    if not
