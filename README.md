# 公文写作智能助手 v8.0 (纯净生产版)

这是一款基于 Python Streamlit 构建的轻量化但却拥有**商用级架构**的公文写作智能辅助 Web 平台。系统利用兼容 OpenAI 格式的大型语言模型 API 接口，通过多名个性化设定的 Agent 在后台的互相推敲博弈，打破单纯的“一问一答”模式，为您提供极度缜密、贴合体制内行文规范的公文框架与大纲定稿。

---

## 🌟 核心独家特性

1. **双轨 Agent 推敲系统 (Context Injection)**
   - 后台兵分两路：“主笔起草 Agent” 与 “审核挑刺 Agent”。核心防偏科逻辑（Context Drift Protection）确保了无论 AI 后台如何循环讨论，“用户的最初需求”始终被强制灌输为第一顺位指令。
2. **热拔插定制提示词 (Popover UI)**
   - 点击侧边栏对应 Agent 名称，即刻弹出精美的轻量级小气泡 (Popover) 无缝更改人物设定。所有修改后直接实时生效。
3. **人机协同洗稿 (Human-in-the-loop 人在回路)**
   - AI 吵架得到的润色方案将被拉出呈现到一个可编辑区。用户可强行在这组方案上划掉不想要的、补充想要加的，确认后再由排版大师忠实执行。
4. **打字机流式出稿 & 防丢失屏显堡垒**
   - 采用大模型 Streaming 迭代器技术，无等待极速打字渲染！兼容 DeepSeek-R1 等带有 `<think>` 标签特性的深度思考模型。
   - `history.json` 本地固化机制搭配 Session State，断电、刷新浏览器、切网页绝不丢失已生成的精美排版成果。

---

## ☁️ 云端极简部署指南 (Streamlit Secrets)

底层代码已经与接口凭据 **彻底解耦**。零基础用户或领导打开页面即用，完全隐藏底层的极客接口配置框！

如果您要将本仓库直接通过 [Streamlit Community Cloud](https://share.streamlit.io/) 部署上线，**无需修改任何代码**。您只需要在云端项目部署成功后的后台面板中，点击 `Settings` -> `Secrets`，贴入以下您的专属接口设置即可激活大模型：

```toml
# 必填项：您的火山引擎方舟 (或任何兼容 OpenAI 的大模型) API 密钥
ARK_API_KEY = "您自己的API-KEY"

# 选填项：默认内置了火山豆包的地址和推理接入点。
# 如果将来您要对接其他模型平台(如通义千问、DeepSeek官方)，直接按此格式覆盖这两个变量即可，实现零代码换脑！
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ARK_MODEL_NAME = "ep-您的专属接入点ID"
```

## 🛠️ 本地运行

**1. 安装核心依赖库：**
```bash
pip install -r requirements.txt
```

**2. 本地环境变量配置：**
在项目根目录新建 `.streamlit/secrets.toml` 文件（注意前面的点），并贴上和刚才上文完全相同的 TOML 配置代码以提供您的 API Key。

**3. 一键启动服务：**
```bash
python -m streamlit run app.py
```
启动成功后，会自动在您的本地浏览器打开交互引擎页面。
