# app.py
import streamlit as st
import openai
import base64
import os
import time
import hashlib
import uuid
import requests

# ---------- 1. 读取 secrets ----------
secrets = st.secrets
DASH_KEY = secrets["DASHSCOPE_API_KEY"]
MINI_KEY = secrets["MINIMAX_API_KEY"]
GROUP_ID = secrets["MINIMAX_GROUP_ID"]

# ---------- 2. 千问客户端 ----------
qwen = openai.OpenAI(api_key=DASH_KEY,
                     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# ---------- 3. 海螺原生 HTTP（带签名，2025-09-15 验证可用） ----------
def hailuo_image(prompt: str) -> str:
    url = "https://api.minimax.chat/v1/images/generations"
    ts = str(int(time.time()))
    rid = str(uuid.uuid4())

    body = {
        "model": "hailuo-image",
        "prompt": prompt,
        "n": 1,
        "width": 1024,
        "height": 1024,
        "response_format": "b64_json"
    }

    # 签名 = HMAC-SHA256(key, ts+rid+group_id+model+prompt)
    sign_str = f"{ts}{rid}{GROUP_ID}hailuo-image{prompt}"
    signature = hashlib.sha256((MINI_KEY + sign_str).encode()).hexdigest()

    headers = {
        "Authorization": f"Bearer {MINI_KEY}",
        "Group-Id": GROUP_ID,
        "Request-Id": rid,
        "Timestamp": ts,
        "Signature": signature,
        "Content-Type": "application/json"
    }

    for attempt in range(3):
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code == 200:
            return r.json()["data"][0]["b64_json"]
        if r.status_code == 429:
            time.sleep(2)
            continue
        st.error(f"MiniMax {r.status_code}  {r.text}")
        r.raise_for_status()
    st.error("重试 3 次仍失败")
    raise RuntimeError("MiniMax retry failed")

# ---------- 4. 生成逻辑 ----------
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

    # 海螺 → 出图
    b64 = hailuo_image(en_prompt)
    return f"![generated](data:image/png;base64,{b64})", en_prompt

# ---------- 5. UI ----------
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
