import streamlit as st
import openai
import base64
import dashscope

# ---------- 1. 读取 secrets ----------
dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]

# ---------- 2. 生成逻辑 ----------
def generate(prompt_zh: str):
    try:
        # ① 千问把中文需求翻译成英文提示词
        qwen = openai.OpenAI(
            api_key=dashscope.api_key,
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
            format="base64"  # 确保使用 base64 格式
        )

        # 检查 API 请求状态
        if task.status_code != 200:
            raise RuntimeError(f"DashScope 图像生成失败：{task.status_code} {task.message}")

        # 正确处理响应结果（关键修复）
        if hasattr(task.output, 'results') and len(task.output.results) > 0:
            result = task.output.results[0]
            
            # 修复1: 使用 b64_json 而不是 b64
            if hasattr(result, 'b64_json') and result.b64_json:
                b64 = result.b64_json
                return f"![generated](data:image/png;base64,{b64})", en_prompt
            
            # 修复2: 使用 url 而不是 image_url
            elif hasattr(result, 'url') and result.url:
                image_url = result.url
                return f"![generated]({image_url})", en_prompt
            else:
                raise KeyError("结果中缺少 'b64_json' 或 'url' 字段")
        else:
            raise RuntimeError("没有找到生成的图片结果")

    except KeyError as e:
        st.error(f"数据解析错误：{str(e)}")
        st.warning("API 响应结构可能已变更，请联系开发者")
        return None, None
    except RuntimeError as e:
        st.error(f"请求错误：{str(e)}")
        st.warning("请检查输入的描述是否适合生成图像，或稍后重试。")
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
    if "base64," in md:
        b64 = md.split("base64,")[1].split(")")[0]
        st.download_button("📥 下载图片", data=base64.b64decode(b64),
                           file_name="generated.png", mime="image/png")



