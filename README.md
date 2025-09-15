# 🎨 千问 × 海螺 AI 作画 WebUI

一句话描述：  
输入中文画面描述 → 通义千问自动优化英文提示词 → MiniMax 海螺即时生成 1024×1024 高清图 → 浏览器一键下载。

---

## 🚀 效果速览
| 步骤 | 示例 |
|---|---|
| 输入 | `赛博朋克中国城，夜晚，霓虹龙，8K` |
| 千问输出提示词 | `cyberpunk Chinese city at night, neon dragon, 8K, ultra-detailed, cinematic lighting` |
| 海螺出图 | 实时回显 + 下载按钮 |

---

## ⚡ 快速开始（本地 3 步）

```bash
# ① 克隆
git clone https://github.com/yourname/ai-paint.git && cd ai-paint

# ② 填密钥（复制模板后填入真实 KEY）
cp .streamlit/secrets.example.toml .streamlit/secrets.toml

# ③ 安装依赖 & 启动
pip install -U streamlit openai-agents dashscope requests
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
