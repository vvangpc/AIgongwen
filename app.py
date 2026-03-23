import streamlit as st
import openai
from openai import OpenAI
from datetime import datetime
import json
import os
import time

# ==========================================
# 页面基本配置
# ==========================================
st.set_page_config(
    page_title="公文写作智能助手 v8.0",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 云端全局接口配置 (Secrets & Hardcode)
# ==========================================
# 自动通过 st.secrets 安全读取所有核心接口配置
# 在云端只需在 Advanced Settings -> Secrets 里随意修改这三个值，代码即可无缝切换模型与供应商！
try:
    api_key = st.secrets.get("ARK_API_KEY", "")
    base_url = st.secrets.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    model_name = st.secrets.get("ARK_MODEL_NAME", "ep-20260323114516-lmqzs")
except Exception:
    # 兜底：如果没配 secrets，采用默认初始值
    api_key = ""
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model_name = "ep-20260323114516-lmqzs"


# ==========================================
# 缓存与持久化状态初始化 (Session State & Local Storage)
# ==========================================
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"历史记录保存到本地失败: {str(e)}")

# 初始化核心数据缓存
if "ai_suggestions" not in st.session_state:
    st.session_state.ai_suggestions = ""

# 初始化防刷新的最终结果缓存
if "final_fw" not in st.session_state:
    st.session_state.final_fw = ""
if "final_pl" not in st.session_state:
    st.session_state.final_pl = ""

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === 初始化全局 Agent 提示词 ===
if "sys_writer_prompt" not in st.session_state:
    st.session_state.sys_writer_prompt = "你是一名深谙中国大陆党政机关行文规范的资深‘笔杆子’（如省委办公厅综合处业务骨干）。你的任务是根据用户的需求，构建一份逻辑严密、层次清晰、政治站位高的公文提纲。要求：1. 严格使用标准公文层级序数（一、；（一）；1.；（1））。2. 提纲需具备‘起承转合’，包括背景意义、总体要求、核心举措、保障机制等（视具体文种而定）。3. 标题要对仗工整，用词规范、威严、准确。4. 禁止输出废话，直接给出提纲。"
if "sys_reviewer_prompt" not in st.session_state:
    st.session_state.sys_reviewer_prompt = "你是一位极其严苛的机关审核处长，拥有20年公文把关经验。你需要对下属提交的公文框架进行‘挑刺’。审查标准：1. 政治方向是否有偏差或遗漏？2. 逻辑树是否符合MECE原则（不重不漏）？3. 举措是否过于空泛，缺乏落地抓手？4. 标题是否不够精炼有力？请直接列出致命缺陷和具体修改指令，语气要严厉、精炼，切忌替他重写全文。"
if "sys_p_writer_prompt" not in st.session_state:
    st.session_state.sys_p_writer_prompt = "你是机关政研室的公文润色主笔。请对用户提供的公文初稿进行深度诊断。你需要精准指出以下问题：1. 存在口语化、大白话表达的地方；2. 逻辑断层或转折生硬之处；3. 缺乏理论深度和高度的地方。请严格以清单形式（1. 2. 3.）列出详细的修改建议条款，建议需具体到某一段、某一句的词汇替换方向，暂不需要重写全文。"
if "sys_p_reviewer_prompt" not in st.session_state:
    st.session_state.sys_p_reviewer_prompt = "你是负责最终签批的秘书长。你需要审阅润色主笔提交的《修改建议清单》。请以宏观视野和高标准把关：1. 严厉驳回清单中无关痛痒、流于表面的修改；2. 指出清单中不够具有‘体制内气韵’的建议；3. 补充你认为必须拔高和深挖的核心修改意见。用词要高屋建瓴，一针见血，直指要害。"
if "sys_polish_prompt" not in st.session_state:
    st.session_state.sys_polish_prompt = "你是公文排版与出稿校验大师。请严格按照用户确认的《修改最终指令》，对原始初稿进行彻底的重构与深度润色。要求：1. 坚决执行所有修改指令，极大提升词汇的公文属性（如适时使用‘压实责任’、‘统筹推进’、‘抓好落实’等体制内规范表述）。2. 确保全文行云流水，气势磅礴，逻辑严密。3. 绝对禁止输出任何解释性废话（如‘好的’、‘修改如下’），直接、且仅输出最终排版好的正文纯文本。"


# ==========================================
# 侧边栏配置区 (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("### 欢迎使用公文助手")
    
    st.markdown("#### 🔄 Agent 讨论轮数设置")
    discuss_rounds = st.selectbox("框架生成轮数：", options=list(range(1, 11)), index=0)
    polish_rounds = st.selectbox("智能润色轮数：", options=list(range(1, 11)), index=1)
    
    st.markdown("---")
    
    # 彻底移除了极客向的 ⚙️ 接口常规设置 菜单，实现“小白打开即用”的清爽感
    
    st.markdown("#### 📝 框架生成：提示词配置")
    with st.popover("✍️ 设置：框架主笔 Agent", use_container_width=True):
        st.markdown("**为起草主笔定制灵魂与行文规范：**")
        temp_fw_writer = st.text_area("提示词编辑区", value=st.session_state.sys_writer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_fw_writer"):
            st.session_state.sys_writer_prompt = temp_fw_writer
            st.success("✅ 修改成功！")
            
    with st.popover("🧐 设置：框架审核处长 Agent", use_container_width=True):
        st.markdown("**为挑刺的审核处长定制审核标准：**")
        temp_fw_reviewer = st.text_area("提示词编辑区", value=st.session_state.sys_reviewer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_fw_reviewer"):
            st.session_state.sys_reviewer_prompt = temp_fw_reviewer
            st.success("✅ 修改成功！")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("#### 📝 智能润色：提示词配置")
    with st.popover("✍️ 设置：政研室润色主笔 ", use_container_width=True):
        st.markdown("**指导分析师如何针对原文挑错找茬：**")
        temp_pl_writer = st.text_area("提示词编辑区", value=st.session_state.sys_p_writer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_pl_writer"):
            st.session_state.sys_p_writer_prompt = temp_pl_writer
            st.success("✅ 修改成功！")

    with st.popover("🧐 设置：润色把关秘书长 ", use_container_width=True):
        st.markdown("**为挑剔的秘书长设定高级审稿门槛：**")
        temp_pl_reviewer = st.text_area("提示词编辑区", value=st.session_state.sys_p_reviewer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_pl_reviewer"):
            st.session_state.sys_p_reviewer_prompt = temp_pl_reviewer
            st.success("✅ 修改成功！")

    with st.popover("✨ 设置：润色排版出稿大师", use_container_width=True):
        st.markdown("**为最终负责重新合并全图的出稿大师定义排版风格：**")
        temp_pl_final = st.text_area("提示词编辑区", value=st.session_state.sys_polish_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_pl_final"):
            st.session_state.sys_polish_prompt = temp_pl_final
            st.success("✅ 修改成功！")


# ==========================================
# 核心公共函数
# ==========================================
def call_openai_api(sys_prompt, user_prompt):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ 后台请求出现异常：\n\n```python\n{str(e)}\n```")
        st.stop()

def stream_openai_api(sys_prompt, user_prompt):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n\n❌ 流式请求被中断或发生异常：{str(e)}"

def append_to_history(new_record):
    st.session_state.history.append(new_record)
    save_history(st.session_state.history)


# ==========================================
# 主界面布局
# ==========================================
st.title("公文写作智能助手 v8.0 🏛️")

tab_framework, tab_polish, tab_history = st.tabs([
    "📍 需求一：框架生成", 
    "✨ 需求二：智能润色",
    "📜 生成档案室"
])

# ===============================================================
# 需求一：框架生成
# ===============================================================
with tab_framework:
    st.header("👥 多Agent框架推敲系统")
    draft_req = st.text_area(
        "📝 您的公文撰写需求：", height=150, 
        placeholder="例如：请帮我构思一份年度党风廉政建设的结构框架..."
    )
    
    if st.button("🚀 开始生成框架", type="primary"):
        st.session_state.final_fw = "" 
        
        if not api_key:
            # 根据要求：友好的零基础管理员警告
            st.warning("⚠️ 系统管理员尚未在云端配置 API Key，请联系开发者。")
        elif not draft_req.strip():
            st.warning("⚠️ 请先输入您的撰写需求！")
        else:
            discussion_log = []
            
            with st.expander("👀 展开查看 AI 内部讨论细节...", expanded=True):
                current_context = ""
                
                for i in range(discuss_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮讨论")
                    
                    with st.spinner("✍️ 框架主笔 Agent 起草 / 修改..."):
                        if i == 0:
                            user_writer_prompt = f"【用户的最初撰写需求（绝对基准）】：\n{draft_req}\n\n请直接基于该需求撰写公文框架。"
                        else:
                            user_writer_prompt = f"【用户的最初撰写需求（绝对基准不能偏听偏信）】：\n{draft_req}\n\n【前序讨论与处长批评意见】：\n{current_context}\n\n请吸取处长意见继续修改出新框架，但内容绝不可偏离原始需求主题。"
                        
                        writer_output = call_openai_api(st.session_state.sys_writer_prompt, user_writer_prompt)
                        st.markdown("**✍️ 框架主笔 Agent 产出：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 框架主笔】\n{writer_output}")
                    
                    with st.spinner("🧐 框架审核处长 检查修正..."):
                        user_reviewer_prompt = f"【用户最初提的需求】：\n{draft_req}\n\n【手下主笔交上来的框架】：\n{writer_output}\n\n请比对原需求进行严苛痛批，提出改进指令。"
                        
                        reviewer_output = call_openai_api(st.session_state.sys_reviewer_prompt, user_reviewer_prompt)
                        st.markdown("**🧐 框架审核处长批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 处长】\n{reviewer_output}")
                    
                    current_context = f"【上一版你写的主笔原稿】\n{writer_output}\n\n【刚才处长的批评建议】\n{reviewer_output}"
                    
            with st.spinner("✨ 讨论完毕，已开启无闪烁流式打字输出..."):
                sys_final = st.session_state.sys_writer_prompt + " 你现在需要进行最终定稿输出，直接出纯净的文本结果，没有前缀也没有后缀。"
                user_final = f"【回归用户定海神针需求】：\n{draft_req}\n\n【后台磨合素材】：\n{current_context}\n\n整理出一份大圆满框架定稿："
                
                st.markdown("### 📄 最终定稿流注中...")
                
                final_framework_raw = st.write_stream(stream_openai_api(sys_final, user_final))
                st.session_state.final_fw = final_framework_raw
                
                summary = draft_req[:15] + "..." if len(draft_req) > 15 else draft_req
                
                append_to_history({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": f"💡 框架：{summary}",
                    "user_input": draft_req,
                    "process_log": "\n\n---\n\n".join(discussion_log),
                    "final_output": final_framework_raw
                })

    elif st.session_state.final_fw:
        st.markdown("### 📄 最终定稿的公文范文框架")
        st.success(st.session_state.final_fw)


# ===============================================================
# 需求二：智能润色
# ===============================================================
with tab_polish:
    st.header("✨ 人机协同智能润色")
    
    original_text = st.text_area(
        "📝 步骤一：请输入需要润色的【公文原始内容】", height=150, 
        placeholder="把不满意的初稿文本粘贴在这里..."
    )
    
    if st.button("💡 1. 生成修改方案", type="primary"):
        if not api_key: st.warning("⚠️ 系统管理员尚未在云端配置 API Key，请联系开发者。")
        elif not original_text.strip(): st.warning("⚠️ 原始公文内容不能为空！")
        else:
            discussion_log = []
            
            with st.expander("👀 查看 AI 政研室内部润色博弈过程", expanded=True):
                current_context = ""
                
                for i in range(polish_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮探讨")
                    
                    with st.spinner("✍️ 润色分析员 正在指出可以优化的方向..."):
                        if i == 0:
                            user_p_writer = f"【需要润色的原文绝对锚点】：\n{original_text}\n\n请指出具体需要优化的漏洞与改善点。"
                        else:
                            user_p_writer = f"【需要润色的原文绝对锚点】：\n{original_text}\n\n【你上次输出的方案与总监批语】：\n{current_context}\n\n请死死盯住原稿语义，结合总监批示重新改进修改清单。"
                        
                        writer_output = call_openai_api(st.session_state.sys_p_writer_prompt, user_p_writer)
                        st.markdown("**✍️ 润色分析员意见：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 分析师】\n{writer_output}")
                    
                    with st.spinner("🧐 润色秘书长 正在把关方案有效性..."):
                        user_p_reviewer = f"【被润色的原文】：\n{original_text}\n\n【手下上的修改呈报表】：\n{writer_output}\n\n请进行高标准的审问与打回要求。"
                        
                        reviewer_output = call_openai_api(st.session_state.sys_p_reviewer_prompt, user_p_reviewer)
                        st.markdown("**🧐 润色秘书长批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 秘书长】\n{reviewer_output}")
                    
                    current_context = f"【你当时的呈上清单】\n{writer_output}\n\n【秘书长痛批的意见】\n{reviewer_output}"
            
            with st.spinner("✨ 整合汇总最终意见方案..."):
                sys_final_suggest = "综合底下刚才讨论，输出一份最清晰有条理的【最终公文修改条款清单】。绝不废话。"
                user_final_suggest = f"【必须紧扣原稿】：\n{original_text}\n\n【底下人的争吵记录】：\n{current_context}\n\n出具一锤定音的汇总修改清单："
                
                st.session_state.ai_suggestions = call_openai_api(sys_final_suggest, user_final_suggest)
                st.success("✅ 多轮探讨结束自动填入下方人工审核区，供您检阅删减！")

    if st.session_state.ai_suggestions:
        st.markdown("---")
        st.markdown("### 🧑‍💻 步骤二：人工审查与编辑 (您可以直接在此框内强行介入修改)")
        
        edited_suggestions = st.text_area(
            "对润色方案的最终把关集：", 
            value=st.session_state.ai_suggestions, 
            height=200
        )
        
        if st.button("✨ 2. 执行最终彻头彻尾的流式润色洗稿！", type="primary"):
            st.session_state.final_pl = "" 
            if not api_key:
                st.warning("⚠️ 系统管理员尚未在云端配置 API Key，请联系开发者。")
            else:
                with st.spinner("🤖 出稿大师接入中...") :
                    sys_final_polish = st.session_state.sys_polish_prompt
                    user_final_polish = f"【绝对原始稿件区】：\n{original_text}\n\n【皇帝圣旨级别的修改强制命令区域】：\n{edited_suggestions}\n\n开始不掺杂废话的全文重构排版润色："
                    
                    st.markdown("### 📜 倾注精力的最终结晶打字生成中...")
                    
                    final_pl_raw = st.write_stream(stream_openai_api(sys_final_polish, user_final_polish))
                    st.session_state.final_pl = final_pl_raw
                    
                    summary = original_text[:15] + "..." if len(original_text) > 15 else original_text
                    
                    append_to_history({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "task_type": f"✒️ 润色：{summary}",
                        "user_input": original_text,
                        "process_log": edited_suggestions,
                        "final_output": final_pl_raw
                    })

        elif st.session_state.final_pl:
            st.markdown("### 📜 最终润色结晶纯净稿")
            st.success(st.session_state.final_pl)


# ===============================================================
# 历史记录展示页 
# ===============================================================
with tab_history:
    st.header("📜 不朽档案室 (完全无缝保存版)")
    
    if not st.session_state.history:
        st.info("🕒 目前暂无记录。去主线任务随便写点什么试试吧！")
    else:
        for idx, record in enumerate(reversed(st.session_state.history)):
            with st.expander(f"🕰️ {record['timestamp']} - {record['task_type']}", expanded=(idx == 0)):
                st.markdown("#### 🔹 最初的需求与原稿")
                st.info(record["user_input"])
                st.markdown("#### 💬 定稿前的切磋磨合细节日志")
                st.text(record.get("process_log", "无流转细节日志"))
                st.markdown("#### ⭐ 岁月留香的成品")
                st.success(record["final_output"])
