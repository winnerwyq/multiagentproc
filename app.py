import streamlit as st
import openai
import base64
import dashscope

# ---------- 1. 读取 secrets ----------
secrets = st.secrets
DASH_KEY = secrets["DASHSCOPE_API_KEY"]   # 阿里百炼

# ---------- 2. 生成逻辑 ----------
def generate(prompt_zh: str):
    try:
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
            size="1024*1024",
            format="base64"
        )

        # 检查 API 请求状态
        if task.status_code != 200:
            raise RuntimeError(f"DashScope 图像生成失败：{task.status_code} {task.message}")

        # 打印调试信息，查看返回的数据结构
        print("DashScope Response:", task.output)

        # 检查结果是否包含 'b64' 字段
        if 'results' in task.output and len(task.output.results) > 0:
            result = task.output.results[0]
            if 'b64' in result:
                b64 = result['b64']
            else:
                raise KeyError("结果中缺少 'b64' 字段")
        else:
            raise RuntimeError("没有找到生成的图片结果")

        return f"![generated](data:image/png;base64,{b64})", en_prompt

    except KeyError as e:
        st.error(f"错误：{str(e)}")
        return None, None
    except RuntimeError as e:
        st.error(f"请求错误：{str(e)}")
        return None, None
    except Exception as e:
        st.error(f"发生了未知错误：{str(e)}")
        return None, None

# ---------- 3. UI ----------
st.set_page_config(page_title="千问作画", page_icon="🎨")
st.title("千问 · 一句话出图")
idea = st.text_area("用中文描述想要的画面", height=80)
go = st.button("生成", type="primary")

if go:
    if not idea.strip():
        st.warning("请输入描述")
        st.stop()

    with st.spinner("生成中…"):
        md, en = generate(idea)

    if md is None:
        st.error("图像生成失败，请稍后重试。")
        st.stop()

    st.markdown(md, unsafe_allow_html=True)
    
    # 提取 base64 图像并提供下载按钮
    b64 = md.split("base64,")[1].split(")")[0]
    st.download_button("📥 下载图片", data=base64.b64decode(b64),
                       file_name="generated.png", mime="image/png")

