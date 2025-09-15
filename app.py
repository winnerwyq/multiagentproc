import streamlit as st
import openai
import base64
import dashscope
import json
import re

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
        st.info(f"📝 生成的英文提示词：\n`{en_prompt}`")

        # ② 千问文生图（DashScope 原生接口） - 关键修复参数
        # 修正1: 使用正确的尺寸格式 (1024x1024 而不是 1024*1024)
        # 修正2: 使用更稳定的 wanx1.3 模型
        task = dashscope.ImageSynthesis.call(
            model="wanx1.3-text2image-v1",  # 替换为当前可用模型
            prompt=en_prompt,
            n=1,
            size="1024x1024",  # 使用 x 分隔尺寸
            format="base64"
        )

        # --- 深度调试：完整解析 API 响应 ---
        st.subheader("🔍 API 响应分析")
        
        # 打印原始响应结构
        debug_info = {
            "HTTP状态码": task.status_code,
            "响应对象类型": str(type(task)),
            "对象属性": list(task.__dict__.keys()),
            "消息内容": task.message,
            "输出内容": str(task.output) if task.output else "None"
        }
        
        # 显示调试信息
        with st.expander("查看完整API响应结构"):
            st.json(debug_info)
        
        # 检查HTTP状态
        if task.status_code != 200:
            st.error(f"❌ HTTP请求失败: {task.status_code} - {task.message}")
            st.warning("请检查网络连接或API端点是否可用")
            return None, None
        
        # 检查业务错误（关键修复点）
        # 方案1: 检查task对象中的code属性
        if hasattr(task, 'code') and task.code != '200':
            error_msg = f"业务错误: {task.code} - {task.message}"
            st.error(f"❌ {error_msg}")
            st.warning("常见原因：1. 模型未开通 2. 账户无权限 3. 参数错误")
            return None, None
        
        # 方案2: 检查output中的错误信息
        if hasattr(task, 'output') and task.output:
            # 检查output中是否包含错误信息
            if isinstance(task.output, dict):
                if 'code' in task.output and task.output['code'] != '200':
                    error_msg = f"业务错误: {task.output['code']} - {task.output.get('message', '未知错误')}"
                    st.error(f"❌ {error_msg}")
                    return None, None
                elif 'error' in task.output:
                    st.error(f"❌ 模型错误: {task.output['error']}")
                    return None, None
            
            # 检查results是否为空
            if hasattr(task.output, 'results') and not task.output.results:
                st.error("❌ 图像生成失败：返回结果为空")
                st.warning("可能原因：1. 提示词包含敏感内容 2. 模型服务异常")
                return None, None
        
        # 智能解析图片数据（兼容所有SDK版本）
        b64_data = None
        
        # 尝试1: 新版SDK (v1.14.0+)
        if hasattr(task, 'output') and hasattr(task.output, 'results') and task.output.results:
            for result in task.output.results:
                if hasattr(result, 'b64') and result.b64:
                    b64_data = result.b64
                    st.success("✅ 检测到图片数据 (b64)")
                    break
        
        # 尝试2: 旧版SDK
        if not b64_data and hasattr(task, 'output') and isinstance(task.output, dict):
            if 'results' in task.output and task.output['results']:
                for item in task.output['results']:
                    if isinstance(item, dict) and 'b64' in item:
                        b64_data = item['b64']
                        st.success("✅ 检测到图片数据 (results.b64)")
                        break
        
        # 尝试3: 直接解析output
        if not b64_data and hasattr(task, 'output') and hasattr(task.output, 'b64'):
            b64_data = task.output.b64
            st.success("✅ 检测到图片数据 (output.b64)")
        
        # 验证base64数据
        if not b64_data:
            st.error("❌ 未找到图片数据")
            st.warning("请检查：1. 模型是否支持base64输出 2. 账户是否有调用权限")
            
            # 显示可用字段帮助诊断
            available_fields = []
            if hasattr(task, 'output') and task.output:
                if hasattr(task.output, 'results'):
                    available_fields.append("output.results")
                if isinstance(task.output, dict):
                    available_fields.append(f"output字典: {list(task.output.keys())}")
            st.info(f"可用字段: {', '.join(available_fields) if available_fields else '无'}")
            
            return None, None
        
        # 验证base64格式
        if not re.match(r'^[A-Za-z0-9+/]+={0,2}$', b64_data):
            st.error("❌ base64数据格式无效")
            st.warning("可能原因：1. 模型返回了错误信息 2. 响应被截断")
            return None, None
        
        # 返回结果
        return f"![generated](data:image/png;base64,{b64_data})", en_prompt

    except Exception as e:
        st.error(f"❌ 发生未知错误：{str(e)}")
        st.exception(e)  # 显示详细错误堆栈
        return None, None

# ---------- 3. UI ----------
st.set_page_config(page_title="千问作画", page_icon="🎨")
st.title("千问 · 一句话出图")
st.caption("使用 DashScope WanX 1.3 模型 | 支持中文描述转英文提示词")

# 添加模型说明
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    **常见问题解决方案：**
    1. **模型未开通**：访问 [DashScope模型广场](https://dashscope.console.aliyun.com/model) 开通 WanX 1.3
    2. **参数错误**：确保尺寸格式为 `1024x1024` (不是 `1024*1024`)
    3. **账户问题**：检查 [账户余额](https://dashscope.console.aliyun.com/credit)
    4. **敏感内容**：避免包含暴力、成人内容
    
    **推荐提示词：**
    - "一只可爱的柯基犬在草地上奔跑，阳光明媚，高清摄影风格"
    - "中国风山水画，水墨风格，云雾缭绕的山峰"
    """)

idea = st.text_area(
    "用中文描述想要的画面", 
    height=80, 
    placeholder="例如：未来城市夜景，霓虹灯光，赛博朋克风格，4K高清"
)
go = st.button("生成", type="primary", use_container_width=True)

if go:
    if not idea.strip():
        st.warning("⚠️ 请输入描述内容")
        st.stop()

    with st.spinner("🎨 正在生成图像... (可能需要30-60秒)"):
        md, en = generate(idea)

    if md is None:
        st.error("❌ 图像生成失败，请参考错误信息排查")
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
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            st.error(f"❌ 下载失败: {str(e)}")
    
    # 显示英文提示词
    with st.expander("🔤 查看生成的英文提示词"):
        st.code(en, language="text")





