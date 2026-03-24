# 🏛️ 公文写作智能助手 v8.5 (Anti-Drift 生产版)

这是一款专为公务人员打造的、具备“防偏航”机制的商用级公文写作 AI 系统。通过精心设计的 5 名 Agent 角色（主笔、审核、分析师、秘书长、出稿大师）以及核心的 **🚨 🚨 定海神针防偏航铁律**，本系统能够确保 AI 在多轮生成的过程中始终紧扣用户原始需求，杜绝“上下文深度漂移”与幻觉滋生。

---

## 🚀 核心黑科技 (Core Features)

### 1. 🚨 【定海神针】防偏航机制 (Iron Rules)
这是 V8.5 的核心升级。我们在所有 Agent 的 System Prompt 中强制注入了“🚨 铁律”：
- **框架审查**：处长 Agent 拥有“一票否决权”，首要任务是比对原始需求进行偏航检查。
- **事实核查**：在润色阶段，秘书长 Agent 会严惩任何试图“无中生有”或篡改原文事实的改动建议。
- **三明治提示词结构**：通过代码层面强制将“原始需求”包裹在 Prompt 的最末尾，确保大模型获得最强的尾部指令引导。

### 2. 👥 五位一体 Agent 协同架构 (Multi-Agent Flow)
- **✍️ 框架主笔**：遵循党政机关行文规范，起草逻辑严密的提纲。
- **🧐 审核处长**：高标准把关，对提纲进行严苛“挑刺”和政治对齐。
- **🕵️ 润色分析员**：精准识别口语化、逻辑断层，提出针对性改进条款。
- **👑 签批秘书长**：审读润色清单，毙掉无关痛痒的修改，拔高理论厚度。
- **✨ 出稿排版大师**：执行最终确认指令，产出震撼人心的公文结晶。

### 3. 🔥 极致流畅的交互体验 (Premium UX)
- **🌊 深度思考流式输出**：原生支持 DeepSeek-R1 等模型的 `<think>` 思考流展示，打字机式平滑渲染。
- **🛡️ 防丢失屏显堡垒**：利用 Session State 独家保护技术，刷新页面、切换侧边栏或 Tab，最终成稿依然稳如泰山。
- **📜 不朽档案室**：本地 `history.json` 自动记录每一份公文的“诞生全过程”，方便随时复盘。

---

## 🔧 技术底座 (Tech Stack)

- **前端/交互**：Streamlit v1.35+
- **模型核心**：豆包 (火山引擎) & DeepSeek-R1 (Ark 平台接入)
- **逻辑层**：Python 3.10+ (OpenAI SDK 兼容模式)

---

## ☁️ 云端极简部署指南 (Streamlit Secrets)

您可以直接连接此仓库到 [Streamlit Community Cloud](https://share.streamlit.io/)，并在后台点击 `Settings` -> `Secrets` 中配置以下内容即可激活：

```toml
# 必填项：您的火山引擎方舟 API 密钥
ARK_API_KEY = "Your_API_Key_Here"

# 接口地址建议 (默认已配置为火山方舟)
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 模型 ID (即您在云端创建的推理接入点 Endpoint ID)
ARK_MODEL_NAME = "ep-xxxxxx-xxxx"
```

---

## 🛠️ 本地开发运行 (Windows 环境)

1. **环境准备**：
   ```bash
   pip install -r requirements.txt
   ```
2. **本地配置**：
   在根目录新建 `.streamlit/secrets.toml` 文件，并参照上述云端配置格式填入您的密钥。
3. **启动程序**：
   ```bash
   python -m streamlit run app.py
   ```

---

## 📝 开发者备注 (Developer Notes)
本系统当前版本已锁定讨论轮次为 **1-5 轮**，以实现深度推敲与响应效率的最佳平衡点。如需更高频率的讨论，请联系管理员调整底层 Selectbox 范围。
