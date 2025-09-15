import streamlit as st
import openai
import base64
import dashscope
import json

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
        st.info(f"生成的英文提示词：\n`{en_prompt}`")

        # ② 千问文生图（DashScope 原生接口）
        task = dashscope.ImageSynthesis.call(
            model="wanx-v1",
            prompt=en_prompt,
            n=1,
            size="1024*1024",
            format="base64"
        )

        # --- 关键修复：全面检查 API 响应 ---
        # 1. 检查 HTTP 状态码
        if task.status_code != 200:
            raise RuntimeError(f"HTTP 请求失败：{task.status_code} {task.message}")
        
        # 2. 检查业务状态码（关键！）
        if hasattr(task, 'code') and task.code != '200':
            raise RuntimeError(f"业务错误：{task.code} {task.message}")
        
        # 3. 调试：打印完整响应结构
        response_data = {
            "status_code": task.status_code,
            "code": getattr(task, 'code', 'N/A'),
            "message": task.message,
            "output": str(task.output) if task.output else "None"
        }
        st.debug(f"API 响应结构: {json.dumps(response_data, indent=2)}")
        
        # 4. 智能解析结果（兼容新旧 SDK 版本）
        if not hasattr(task, 'output') or not task.output:
            raise RuntimeError("API 响应中缺少 'output' 字段")
        
        # 尝试多种可能的响应结构
        b64_data = None
        
        # 方案1: 新版 SDK (v1.14.0+)
        if hasattr(task.output, 'results') and task.output.results:
            for result in task.output.results:
                # 检查新字段名 b64
                if hasattr(result, 'b64') and result.b64:
                    b64_data = result.b64
                    st.success("✅ 检测到新版 SDK 字段: b64")
                    break
                # 检查旧字段名 b64_json
                elif hasattr(result, 'b64_json') and result.b64_json:
                    b64_data = result.b64_json
                    st.success("✅ 检测到旧版 SDK 字段: b64_json")
                    break
        
        # 方案2: 直接解析 output
        if not b64_data and isinstance(task.output, dict):
            # 尝试直接获取 b64
            if 'b64' in task.output:
                b64_data = task.output['b64']
                st.success("✅ 检测到字典格式响应: b64")
            elif 'b64_json' in task.output:
                b64_data = task.output['b64_json']
                st.success("✅ 检测到字典格式响应: b64_json")
        
        # 方案3: 检查 results 数组
        if not b64_data and hasattr(task.output, 'results') and isinstance(task.output.results, list):
            for item in task.output.results:
                if isinstance(item, dict):
                    if 'b64' in item:
                        b64_data = item['b64']
                        st.success("✅ 检测到 results 字典项: b64")
                        break
                    elif 'b64_json' in item:
                        b64_data = item['b64_json']
                        st.success("✅ 检测到 results 字典项: b64_json")
                        break
        
        # 5. 验证结果
        if not b64_data:
            # 详细报告可用字段
            available_fields = []
            if hasattr(task.output, 'results'):
                available_fields.append(f"results ({type(task.output.results)})")
            if isinstance(task.output, dict):
                available_fields.append(f"dict keys: {list(task.output.keys())}")
            raise KeyError(f"未找到图片数据！可用字段: {', '.join(available_fields) if available_fields else '无'}")
        
        # 6. 返回结果
        return f"![generated](data:image/png;base64,{b64_data})", en_prompt

    except KeyError as e:
        st.error(f"❌ 数据解析错误：{str(e)}")
        st.warning("API 响应结构可能已变更，请检查 DashScope 文档或升级 SDK")
        return None, None
    except RuntimeError as e:
        st.error(f"❌ 请求错误：{str(e)}")
        st.warning("请检查：1. API 密钥是否有效 2. 账户余额是否充足 3. 模型是否可用")
        return None, None
    except Exception as e:
        st.error(f"❌ 发生未知错误：{str(e)}")
        st.exception(e)  # 显示详细错误堆栈
        return None, None

# ---------- 3. UI ----------
st.set_page_config(page_title="千问作画", page_icon="🎨")
st.title("千问 · 一句话出图")
st.caption("使用 DashScope WanX 模型生成图像 | 模型: wanx-v1")

idea = st.text_area("用中文描述想要的画面", height=80, placeholder="例如：一只可爱的柯基犬在草地上奔跑，阳光明媚，高清摄影风格")
go = st.button("生成", type="primary")

if go:
    if not idea.strip():
        st.warning("⚠️ 请输入描述内容")
        st.stop()

    with st.spinner("🎨 正在生成图像..."):
        md, en = generate(idea)

    if md is None:
        st.error("❌ 图像生成失败，请检查错误信息")
        st.stop()

    st.success("✅ 图像生成成功！")
    st.markdown(md, unsafe_allow_html=True)
    
    # 提取 base64 图像并提供下载按钮
    if "base64," in md:
        try:
            b64 = md.split("base64,")[1].split(")")[0]
            st.download_button(
                "📥 下载图片", 
                data=base64.b64decode(b64),
                file_name="qwen_art.png", 
                mime="image/png",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"下载失败: {str(e)}")
    
    # 显示英文提示词
    with st.expander("查看生成的英文提示词"):
        st.code(en, language="text")




