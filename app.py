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
    page_title="公文写作智能助手 v7.0",
    page_icon="🤖",
    layout="wide"
)

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

# 【修复 2】：初始化防刷新的最终结果缓存
if "final_fw" not in st.session_state:
    st.session_state.final_fw = ""
if "final_pl" not in st.session_state:
    st.session_state.final_pl = ""

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === 初始化全局 Agent 提示词 ===
if "sys_writer_prompt" not in st.session_state:
    st.session_state.sys_writer_prompt = "你是一位资深的省内政府机关‘笔杆子’。请根据用户需求，撰写结构严谨、用词规范、符合体制内行文习惯的公文框架。"
if "sys_reviewer_prompt" not in st.session_state:
    st.session_state.sys_reviewer_prompt = "你是一位严苛的公文审核处长。请找出前文中的逻辑漏洞、口气不符、以及不符合公文排版规范的地方，并给出明确修改建议。"
if "sys_p_writer_prompt" not in st.session_state:
    st.session_state.sys_p_writer_prompt = "你是负责修改公文的润色主笔分析师。认真阅读原稿，指出可以优化的方向（如词汇不够高级、语气不够得体、逻辑不连贯），详细列出建议条款清单。暂不需要直接重写全文。"
if "sys_p_reviewer_prompt" not in st.session_state:
    st.session_state.sys_p_reviewer_prompt = "你是一位极度严苛的公文润色总监。审阅手下主笔提交的修改单，找出里面不够高级、或不符体制气韵的建议，给出严厉批示。"
if "sys_polish_prompt" not in st.session_state:
    st.session_state.sys_polish_prompt = "你是核心排版出稿大师。综合前文讨论及指令对初稿进行一次彻底重排与深度润色。只输出替换后的正文结果，不带废话。"

# ==========================================
# 侧边栏配置区 (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("### 欢迎使用公文助手")
    
    st.markdown("#### 🔄 Agent 讨论轮数设置")
    discuss_rounds = st.selectbox("框架生成轮数：", options=list(range(1, 11)), index=0)
    polish_rounds = st.selectbox("智能润色轮数：", options=list(range(1, 11)), index=1)
    
    st.markdown("---")
    
    with st.expander("⚙️ 接口常规设置", expanded=False):
        api_key = st.text_input("API Key 🔑", type="password", placeholder="请输入您的火山引擎 API Key")
        
        # 1. 修改为火山方舟（豆包）的 Base URL
        base_url = st.text_input("Base URL 🌐", value="https://ark.cn-beijing.volces.com/api/v3")
        
        # 2. 将 text_input 改为 selectbox (下拉框)，并预置深度思考精选模型
        model_options = [
            "doubao-seed-2-0-lite-260215",  # 文档推荐的最新支持思考的豆包模型
            "doubao-1-5-thinking-pro",      # 豆包 1.5 Pro 深度思考版
            "deepseek-r1-250120",           # 火山方舟托管的满血深度思考 DeepSeek-R1
            "自定义接入点(请在下方输入 ep- 开头的ID)" 
        ]
        
        selected_model = st.selectbox("Model Name 🤖 (深度思考精选模型)", options=model_options, index=0)
        
        # 如果用户选择自定义接入点，弹出一个新的文本框让用户输入具体的 ep-xxxxx
        if selected_model == "自定义接入点(请在下方输入 ep- 开头的ID)":
            model_name = st.text_input("请输入火山引擎推理接入点 (Endpoint ID) 或 模型名：", placeholder="ep-...")
        else:
            model_name = selected_model

    st.markdown("---")
    
    st.markdown("#### 📝 框架生成：提示词配置")
    with st.popover("✍️ 设置：框架主笔 Agent", use_container_width=True):
        st.markdown("**为起草主笔定制灵魂与行文规范：**")
        temp_fw_writer = st.text_area("提示词编辑区", value=st.session_state.sys_writer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_fw_writer"):
            st.session_state.sys_writer_prompt = temp_fw_writer
            st.success("✅ 修改成功！新灵魂已注入后台。")
            
    with st.popover("🧐 设置：框架审核处长 Agent", use_container_width=True):
        st.markdown("**为挑刺的审核处长定制审核标准：**")
        temp_fw_reviewer = st.text_area("提示词编辑区", value=st.session_state.sys_reviewer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_fw_reviewer"):
            st.session_state.sys_reviewer_prompt = temp_fw_reviewer
            st.success("✅ 修改成功！")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("#### 📝 智能润色：提示词配置")
    with st.popover("✍️ 设置：润色分析师 Agent", use_container_width=True):
        st.markdown("**指导分析师如何针对原文挑错找茬：**")
        temp_pl_writer = st.text_area("提示词编辑区", value=st.session_state.sys_p_writer_prompt, label_visibility="collapsed", height=200)
        if st.button("💾 确认覆盖并保存", key="btn_pl_writer"):
            st.session_state.sys_p_writer_prompt = temp_pl_writer
            st.success("✅ 修改成功！")

    with st.popover("🧐 设置：润色把关总监 Agent", use_container_width=True):
        st.markdown("**为挑剔的总监设定高级审稿门槛：**")
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
# 核心公共函数：带打字机流式输出和阻塞请求
# ==========================================
def call_openai_api(sys_prompt, user_prompt):
    """阻塞式调用：用于 Agent 在后台“互相吵架并产生中间件”的场合"""
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
    """【体验升级 3】：流式生成器，提供打字机效果。用于最终成稿阶段交付给用户"""
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
st.title("公文写作智能助手 v7.0 🏛️")
st.markdown("突破性架构：引入**无上下文漂移双向记忆体**、防刷新持久化常驻技术，并支持**流式长文本打字机出稿**体验。")

tab_framework, tab_polish, tab_history = st.tabs([
    "📍 需求一：框架生成", 
    "✨ 需求二：智能润色",
    "📜 生成档案室"
])

# ===============================================================
# 需求一：框架生成 (修复Context Drift + 防刷新 + 流式)
# ===============================================================
with tab_framework:
    st.header("👥 多Agent框架推敲系统")
    draft_req = st.text_area(
        "📝 您的公文撰写需求：", height=150, 
        placeholder="例如：请帮我构思一份年度党风廉政建设的结构框架..."
    )
    
    if st.button("🚀 开始生成框架", type="primary"):
        if not api_key:
            st.warning("⚠️ 请先填写 API Key！")
        elif not draft_req.strip():
            st.warning("⚠️ 请先输入您的撰写需求！")
        else:
            discussion_log = []
            
            with st.expander("👀 展开查看 AI 内部讨论细节...", expanded=True):
                current_context = ""
                
                for i in range(discuss_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮讨论")
                    
                    with st.spinner("✍️ 框架主笔 Agent 起草 / 修改..."):
                        # 【核心修复 1】：上下文无论循环多少次，永远以“原始需求”这四个字做绝对锚定基点，防止 Drift 偏题！
                        if i == 0:
                            user_writer_prompt = f"【用户的最初撰写需求（绝对基准）】：\n{draft_req}\n\n请直接基于该需求撰写公文框架。"
                        else:
                            user_writer_prompt = f"【用户的最初撰写需求（绝对基准不能偏听偏信）】：\n{draft_req}\n\n【前序讨论与处长批评意见】：\n{current_context}\n\n请吸取处长意见继续修改出新框架，但内容绝不可偏离原始需求主题。"
                        
                        writer_output = call_openai_api(st.session_state.sys_writer_prompt, user_writer_prompt)
                        st.markdown("**✍️ 框架主笔 Agent 产出：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 框架主笔】\n{writer_output}")
                    
                    with st.spinner("🧐 框架审核 Agent 检查修正..."):
                        user_reviewer_prompt = f"【用户最初提的需求】：\n{draft_req}\n\n【手下主笔交上来的框架】：\n{writer_output}\n\n请比对原需求进行严苛痛批，提出改进指令。"
                        
                        reviewer_output = call_openai_api(st.session_state.sys_reviewer_prompt, user_reviewer_prompt)
                        st.markdown("**🧐 框架审核处长批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 框架审核】\n{reviewer_output}")
                    
                    # 传承给下一轮主笔的信息包容留
                    current_context = f"【上一版你写的主笔原稿】\n{writer_output}\n\n【刚才处长的批评建议】\n{reviewer_output}"
                    
            with st.spinner("✨ 讨论完毕，连接大模型拉取流式最终数据..."):
                sys_final = st.session_state.sys_writer_prompt + " 你现在需要进行最终定稿输出，直接出纯净的文本结果，没有前缀也没有后缀。"
                user_final = f"【回归用户定海神针需求】：\n{draft_req}\n\n【后台磨合素材】：\n{current_context}\n\n整理出一份大圆满框架定稿："
                
                st.markdown("### 📄 正在流式打字定稿中...")
                # 【体验升级 3】：使用流式 st.write_stream 展现令人愉悦的生成过程
                final_framework = st.write_stream(stream_openai_api(sys_final, user_final))
                
                # 【核心修复 2】：赋值完毕后立刻塞入 session_state ，然后 Rerun。这样不管怎么切网页，它都焊死在页面上！
                st.session_state.final_fw = final_framework
                
                append_to_history({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": "💡 框架生成多轮流式推敲",
                    "user_input": draft_req,
                    "process_log": "\n\n---\n\n".join(discussion_log),
                    "final_output": final_framework
                })
                # 触发页面重绘，此时 st.button 区域走完，底部独立渲染块会展现
                st.rerun()

    # 【常驻防刷新的渲染块】
    if st.session_state.final_fw:
        st.markdown("### 📄 最终定稿的公文范文框架")
        st.success(st.session_state.final_fw)


# ===============================================================
# 需求二：智能润色 (修复Context Drift + 防刷新 + 流式)
# ===============================================================
with tab_polish:
    st.header("✨ 人机协同智能润色")
    
    original_text = st.text_area(
        "📝 步骤一：请输入需要润色的【公文原始内容】", height=150, 
        placeholder="把不满意的初稿文本粘贴在这里..."
    )
    
    # 步骤一：AI 博弈出修改意见
    if st.button("💡 1. 生成修改方案", type="primary"):
        if not api_key: st.warning("⚠️ 填写 API Key！")
        elif not original_text.strip(): st.warning("⚠️ 原始公文内容不能为空！")
        else:
            discussion_log = []
            
            with st.expander("👀 查看 AI 润色博弈过程", expanded=True):
                current_context = ""
                
                for i in range(polish_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮探讨")
                    
                    with st.spinner("✍️ 润色分析员 正在指出可以优化的方向..."):
                        # 【核心修复 1】：强锚定被润色的原稿
                        if i == 0:
                            user_p_writer = f"【需要润色的原文绝对锚点】：\n{original_text}\n\n请指出具体需要优化的漏洞与改善点。"
                        else:
                            user_p_writer = f"【需要润色的原文绝对锚点】：\n{original_text}\n\n【你上次输出的方案与总监批语】：\n{current_context}\n\n请死死盯住原稿语义，结合总监批示重新改进修改清单。"
                        
                        writer_output = call_openai_api(st.session_state.sys_p_writer_prompt, user_p_writer)
                        st.markdown("**✍️ 润色分析员意见：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 分析师】\n{writer_output}")
                    
                    with st.spinner("🧐 润色总监 正在把关方案有效性..."):
                        user_p_reviewer = f"【被润色的原文】：\n{original_text}\n\n【手下上的修改呈报表】：\n{writer_output}\n\n请进行高标准的审问与打回要求。"
                        
                        reviewer_output = call_openai_api(st.session_state.sys_p_reviewer_prompt, user_p_reviewer)
                        st.markdown("**🧐 润色总监批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 总监】\n{reviewer_output}")
                    
                    current_context = f"【你当时的呈上清单】\n{writer_output}\n\n【总监痛批的意见】\n{reviewer_output}"
            
            with st.spinner("✨ 整合汇总最终意见方案..."):
                sys_final_suggest = "你是办公室秘书长。综合底下刚才讨论，输出一份最清晰有条理的【最终公文修改条款清单】。绝不废话。"
                user_final_suggest = f"【必须紧扣原稿】：\n{original_text}\n\n【底下人的争吵记录】：\n{current_context}\n\n出具一锤定音的汇总修改清单："
                
                st.session_state.ai_suggestions = call_openai_api(sys_final_suggest, user_final_suggest)
                st.success("✅ 多轮探讨结束自动填入下方人工审核区，供您检阅删减！")

    # 步骤二与三：人工修改与流式洗稿
    if st.session_state.ai_suggestions:
        st.markdown("---")
        st.markdown("### 🧑‍💻 步骤二：人工审查与编辑 (您可以直接在此框内强行介入修改)")
        
        edited_suggestions = st.text_area(
            "对润色方案的最终把关集：", 
            value=st.session_state.ai_suggestions, 
            height=200
        )
        
        if st.button("✨ 2. 执行最终彻头彻尾的流式润色洗稿！", type="primary"):
            with st.spinner("🤖 出稿大师接入中...") :
                sys_final_polish = st.session_state.sys_polish_prompt
                user_final_polish = f"【绝对原始稿件区】：\n{original_text}\n\n【皇帝圣旨级别的修改强制命令区域】：\n{edited_suggestions}\n\n开始不掺杂废话的全文重构排版润色："
                
                st.markdown("### 📜 正在流式打字出稿中...")
                # 【体验升级 3】采用高级打字机特效完成渲染
                final_pl = st.write_stream(stream_openai_api(sys_final_polish, user_final_polish))
                
                # 【核心修复 2】缓存持久，防止页面刷新蒸发心血
                st.session_state.final_pl = final_pl
                
                append_to_history({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": "✒️ 两级流式深度修文",
                    "user_input": original_text,
                    "process_log": edited_suggestions,
                    "final_output": final_pl
                })
                # 重刷页面
                st.rerun()

    # 【常驻防刷新的渲染块】
    if st.session_state.final_pl:
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
                st.text(record.get("process_log", "无流转日志"))
                st.markdown("#### ⭐ 岁月留香的成品")
                st.success(record["final_output"])
