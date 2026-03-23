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
    page_title="公文写作智能助手 v6.0",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 缓存与持久化状态初始化 (Session State & Local Storage)
# ==========================================
HISTORY_FILE = "history.json"

def load_history():
    """从本地 JSON 文件加载历史记录，实现刷新不丢失"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_list):
    """每次追加新的生成内容后，立刻持久化到本地 JSON 文件"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"历史记录保存到本地失败: {str(e)}")

# 初始化各模块的 session_state
if "ai_suggestions" not in st.session_state:
    st.session_state.ai_suggestions = ""

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === 初始化全局 Agent 提示词 ===
# 框架生成系
if "sys_writer_prompt" not in st.session_state:
    st.session_state.sys_writer_prompt = "你是一位资深的省内政府机关‘笔杆子’。请根据用户需求，撰写结构严谨、用词规范、符合体制内行文习惯的公文框架。"
if "sys_reviewer_prompt" not in st.session_state:
    st.session_state.sys_reviewer_prompt = "你是一位严苛的公文审核处长。请找出前文中的逻辑漏洞、口气不符、以及不符合公文排版规范的地方，并给出明确修改建议。"

# 智能润色系
if "sys_p_writer_prompt" not in st.session_state:
    st.session_state.sys_p_writer_prompt = "你是负责修改公文的润色主笔分析师。认真阅读原稿，指出你可以发现的优化方向（如词汇不够高级、语气不够得体、逻辑不连贯），详细列出建议条款清单。暂不需要直接重写全文。"
if "sys_p_reviewer_prompt" not in st.session_state:
    st.session_state.sys_p_reviewer_prompt = "你是一位极度严苛的公文润色总监。审阅手下主笔提交的修改单，必须找出里面不够高级、或不符体制气韵的建议，并给出你的严厉驳回与指导批示。"
if "sys_polish_prompt" not in st.session_state:
    st.session_state.sys_polish_prompt = "你是核心排版出稿大师。综合前文讨论、以及用户钦定确认的修改单，对用户的初稿进行一次从头到尾的彻底重排与深度润色，让全文浑然天成。只输出替换后的正文结果，不带任何废话。"

# ==========================================
# 侧边栏配置区 (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("### 欢迎使用公文助手")
    
    # 讨论轮数统一管控区
    st.markdown("#### 🔄 Agent 讨论轮数设置")
    discuss_rounds = st.selectbox(
        "框架生成轮数：", 
        options=list(range(1, 11)), 
        index=0, 
        help="【需求一】中两名 Agent 内部论战次数。"
    )
    polish_rounds = st.selectbox(
        "智能润色轮数：", 
        options=list(range(1, 11)), 
        index=1, 
        help="【需求二】中润色分析师与总监博弈的次数。"
    )
    
    st.markdown("---")
    
    # 接口设置
    with st.expander("⚙️ 接口常规设置", expanded=False):
        api_key = st.text_input("API Key 🔑", type="password", placeholder="请输入您的 API Key")
        base_url = st.text_input("Base URL 🌐", value="https://api.deepseek.com")
        model_name = st.text_input("Model Name 🤖", value="deepseek-chat")

    st.markdown("---")
    
    # 【改动点：全面重构为弹窗 (Popover) 式单独设置机制】
    st.markdown("#### 📝 框架生成：提示词配置")
    
    # 【1】框架主笔 Agent
    with st.popover("✍️ 设置：框架主笔 Agent", use_container_width=True):
        st.markdown("**为起草主笔定制灵魂与行文规范：**")
        temp_fw_writer = st.text_area(
            "提示词编辑区",
            value=st.session_state.sys_writer_prompt,
            label_visibility="collapsed",
            height=200
        )
        if st.button("💾 确认覆盖并保存", key="btn_fw_writer"):
            st.session_state.sys_writer_prompt = temp_fw_writer
            st.success("✅ 修改成功！新灵魂已注入后台。请点击屏幕空白处关闭此弹窗。")
            
    # 【2】框架审核 Agent
    with st.popover("🧐 设置：框架审核处长 Agent", use_container_width=True):
        st.markdown("**为挑刺的审核处长定制审核标准：**")
        temp_fw_reviewer = st.text_area(
            "提示词编辑区",
            value=st.session_state.sys_reviewer_prompt,
            label_visibility="collapsed",
            height=200
        )
        if st.button("💾 确认覆盖并保存", key="btn_fw_reviewer"):
            st.session_state.sys_reviewer_prompt = temp_fw_reviewer
            st.success("✅ 修改成功！已保存。请点击屏幕空白处关闭此弹窗。")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==========================
    st.markdown("#### 📝 智能润色：提示词配置")
    
    # 【3】润色分析师 Agent
    with st.popover("✍️ 设置：润色分析师 Agent", use_container_width=True):
        st.markdown("**指导分析师如何针对原文挑错找茬：**")
        temp_pl_writer = st.text_area(
            "提示词编辑区",
            value=st.session_state.sys_p_writer_prompt,
            label_visibility="collapsed",
            height=200
        )
        if st.button("💾 确认覆盖并保存", key="btn_pl_writer"):
            st.session_state.sys_p_writer_prompt = temp_pl_writer
            st.success("✅ 润色分析师性格已保存！请点击屏幕空白处关闭此弹窗。")

    # 【4】润色总监 Agent
    with st.popover("🧐 设置：润色把关总监 Agent", use_container_width=True):
        st.markdown("**为挑剔的总监设定高级审稿门槛与批示要求：**")
        temp_pl_reviewer = st.text_area(
            "提示词编辑区",
            value=st.session_state.sys_p_reviewer_prompt,
            label_visibility="collapsed",
            height=200
        )
        if st.button("💾 确认覆盖并保存", key="btn_pl_reviewer"):
            st.session_state.sys_p_reviewer_prompt = temp_pl_reviewer
            st.success("✅ 润色把关总监已上线！请点击屏幕空白处关闭此弹窗。")

    # 【5】润色排版出稿大师
    with st.popover("✨ 设置：润色排版出稿大师", use_container_width=True):
        st.markdown("**为最终负责重新合并全图的出稿大师定义最终排版风格：**")
        temp_pl_final = st.text_area(
            "提示词编辑区",
            value=st.session_state.sys_polish_prompt,
            label_visibility="collapsed",
            height=200
        )
        if st.button("💾 确认覆盖并保存", key="btn_pl_final"):
            st.session_state.sys_polish_prompt = temp_pl_final
            st.success("✅ 出稿大师调教完毕！请点击屏幕空白处关闭此弹窗。")


# ==========================================
# 核心公共函数：封装 API 调用并处理报错
# ==========================================
def call_openai_api(sys_prompt, user_prompt):
    """封装调用 OpenAI 接口的基础函数，处理一切异常情况"""
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
    
    except openai.AuthenticationError as e:
        st.error("❌ 认证失败：您的 API Key 不正确或已欠费，请在侧边栏【⚙️ 接口设置】中检查。")
        st.stop()
    except openai.APIConnectionError as e:
        st.error("❌ 网络连接失败：无法连接到目标服务器。")
        st.stop()
    except Exception as e:
        st.error(f"❌ 请求出现未知异常：\n\n```python\n{str(e)}\n```")
        st.stop()

def append_to_history(new_record):
    """辅助函数：将新记录加入缓存并立刻落盘保存"""
    st.session_state.history.append(new_record)
    save_history(st.session_state.history)


# ==========================================
# 主界面布局
# ==========================================
st.title("公文写作智能助手 v6.0 🏛️")
st.markdown("本次升级为您解锁了极客级操作体验：点击对应角色的名字即可呼出面板为其深度注入灵魂，即走即停！")

# 三个核心标签页
tab_framework, tab_polish, tab_history = st.tabs([
    "📍 需求一：框架生成 (多Agent)", 
    "✨ 需求二：智能润色 (深度推敲)",
    "📜 永久生成档案室"
])

# ===============================================================
# 需求一：框架生成 (多Agent讨论)
# ===============================================================
with tab_framework:
    st.header("👥 多Agent框架推敲系统")
    draft_req = st.text_area(
        "📝 您的公文撰写需求：", 
        height=150, 
        placeholder="例如：请帮我构思一份年度党风廉政建设与反腐败工作总结的结构框架..."
    )
    
    if st.button("🚀 开始生成框架", type="primary"):
        if not api_key:
            st.warning("⚠️ 提示：请先在左侧边栏【⚙️ 接口常规设置】中填写 API Key！")
        elif not draft_req.strip():
            st.warning("⚠️ 提示：请先输入您的撰写需求！")
        else:
            discussion_log = []
            
            with st.expander("👀 展开查看 AI 内部讨论细节...", expanded=True):
                current_context = draft_req
                
                # 采用侧边栏的主笔/审核动态提示词
                for i in range(discuss_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮讨论")
                    
                    # 1. 框架主笔 Agent
                    with st.spinner("✍️ 框架主笔 Agent 正在起草 / 修改..."):
                        if i == 0:
                            user_writer_prompt = f"用户的撰写需求如下：\n{current_context}"
                        else:
                            user_writer_prompt = f"结合当前的上下文和审核意见：\n{current_context}\n\n请修改出更完美的新版公文框架。"
                        
                        writer_output = call_openai_api(st.session_state.sys_writer_prompt, user_writer_prompt)
                        st.markdown("**✍️ 框架主笔 Agent 产出：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 框架主笔】\n{writer_output}")
                    
                    # 2. 框架审核 Agent
                    with st.spinner("🧐 框架审核 Agent 正在检查修正..."):
                        user_reviewer_prompt = f"请审核以下由主笔起草的公文框架，并给出你的修改批示意见：\n{writer_output}"
                        
                        reviewer_output = call_openai_api(st.session_state.sys_reviewer_prompt, user_reviewer_prompt)
                        st.markdown("**🧐 框架审核 Agent 批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 框架审核】\n{reviewer_output}")
                    
                    current_context = f"【上一版主笔原稿】\n{writer_output}\n\n【审核处长的意见】\n{reviewer_output}"
                    
            with st.spinner("✨ 讨论完毕，主笔 Agent 正在执行最高权限生成最终定稿版本..."):
                sys_final = st.session_state.sys_writer_prompt + " 你现在需要进行最终定稿，直接输出规范提纲，坚决不要任何客套前言后语。"
                user_final = f"参考以下材料定稿：\n{current_context}"
                final_framework = call_openai_api(sys_final, user_final)
                
            st.success("✅ 多轮打磨完毕，请看定稿！")
            st.markdown("### 📄 最终定稿的公文范文框架")
            st.success(final_framework)
            
            # 【持久化历史存档】
            append_to_history({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "task_type": "💡 框架生成多轮推敲",
                "user_input": draft_req,
                "process_log": "\n\n---\n\n".join(discussion_log),
                "final_output": final_framework
            })


# ===============================================================
# 需求二：智能润色 (多 Agent 讨论 + 人工审查 / Human-in-loop)
# ===============================================================
with tab_polish:
    st.header("✨ 人机协同智能润色")
    
    original_text = st.text_area(
        "📝 步骤一：请输入需要润色的【公文原始内容】", 
        height=150, 
        placeholder="请把您写好的、或者不够满意的初稿文本粘贴在这里..."
    )
    
    if st.button("💡 1. 生成修改方案", type="primary"):
        if not api_key: st.warning("⚠️ 提示：请先填写 API Key！")
        elif not original_text.strip(): st.warning("⚠️ 提示：原始公文内容不能为空！")
        else:
            discussion_log = []
            
            with st.expander("👀 查看 AI 润色分析员与总监的争议博弈过程", expanded=True):
                current_context = original_text
                
                for i in range(polish_rounds):
                    st.markdown(f"### 🔄 第 {i+1} 轮润色探讨")
                    
                    # 1. 润色分析员 Agent
                    with st.spinner("✍️ 润色分析员 正在指出可以优化的方向..."):
                        if i == 0:
                            sys_p_writer = st.session_state.sys_p_writer_prompt
                            user_p_writer = f"原稿如下：\n{current_context}"
                        else:
                            sys_p_writer = st.session_state.sys_p_writer_prompt + " 你现在需要根据总监的严格要求，改进你的上一版润色清单结论。"
                            user_p_writer = f"之前的上下文本与总监的批语：\n{current_context}\n\n请虚心接受批评，重新输出一份更加完美高级的【润色方案建议条款】。"
                        
                        writer_output = call_openai_api(sys_p_writer, user_p_writer)
                        st.markdown("**✍️ 润色分析员意见：**")
                        st.info(writer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 润色主笔分析师】\n{writer_output}")
                    
                    # 2. 润色总监 Agent
                    with st.spinner("🧐 润色总监 正在把关方案有效性..."):
                        sys_p_reviewer = st.session_state.sys_p_reviewer_prompt
                        user_p_reviewer = f"这是底下员工呈交来的公文润色建议表，请给予严肃批示修改与纠错意见（不用直接重排全文，只需批示他的建议表）：\n{writer_output}"
                        
                        reviewer_output = call_openai_api(sys_p_reviewer, user_p_reviewer)
                        st.markdown("**🧐 润色总监批示：**")
                        st.warning(reviewer_output)
                        discussion_log.append(f"【第 {i+1} 轮 - 润色严格总监】\n{reviewer_output}")
                    
                    current_context = f"【主笔上报方案】\n{writer_output}\n\n【总监打回意见】\n{reviewer_output}"
            
            # 【提取精华给人类审查】
            with st.spinner("✨ 系统正在为您将战果整合融汇成最终意见方案..."):
                sys_final_suggest = "你是办公室秘书长。综合底下刚才那一堆互相撕咬的讨论记录，立刻输出一份最清晰有条理、最集大成的【最终公文修改条款方案】供书记过目。绝对不要长篇大论的废话。"
                user_final_suggest = f"吵架和讨论记录全在这了：\n{current_context}"
                
                st.session_state.ai_suggestions = call_openai_api(sys_final_suggest, user_final_suggest)
                st.success("✅ 多轮探讨结束，这份完美方案已自动填入下方人工审核区，供您检阅删减！")

    # 【步骤二与步骤三】利用 session_state 进行中断保留
    if st.session_state.ai_suggestions:
        st.markdown("---")
        st.markdown("### 🧑‍💻 步骤二：人工审查与编辑 (您可以直接在此框内强行介入修改)")
        st.info("👇 这份修改方案是刚才两人通过多轮斗争得出的精华。如您仍觉不痛快，大可直接在此处手动删减、甚至随意添写指令（比如加上‘所有字句换成排比句’）。")
        
        edited_suggestions = st.text_area(
            "对润色方案的最终把关与人工介入：", 
            value=st.session_state.ai_suggestions, 
            height=250
        )
        
        if st.button("✨ 2. 人工把关完毕！确认依据此方案并执行最终润色洗稿！", type="primary"):
            with st.spinner("🤖 出稿大师已经就位！正在排兵布阵，重塑原稿字句..."):
                
                # 调用在左侧设置菜单独家配备的 润色排版专家 提示词！
                sys_final_polish = st.session_state.sys_polish_prompt
                user_final_polish = f"【原始稿内容】\n{original_text}\n\n【我钦定的全部修改指令与打磨精华方案】\n{edited_suggestions}\n\n开始执行全盘彻彻底底的洗稿式重构排版润色工作："
                
                final_polished_text = call_openai_api(sys_final_polish, user_final_polish)
                
                st.success("✅ 终局大胜！一切润色出稿指令均被完美执行！")
                st.markdown("### 📜 全文结晶成稿")
                st.success(final_polished_text)
                
                # 【落盘防丢失保存】
                append_to_history({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": "✒️ 智能协同两级讨论润色深加工",
                    "user_input": original_text,
                    "process_log": edited_suggestions,
                    "final_output": final_polished_text
                })


# ===============================================================
# 历史记录展示页 (本地防丢失版)
# ===============================================================
with tab_history:
    st.header("📜 不朽档案室 (全本云端固化版)")
    st.markdown("不用再担心浏览器突然崩溃或者手滑刷新了，因为您的每一次修改都已经实时保存在项目大营的 `history.json` 绝密资料库里了！")
    
    if not st.session_state.history:
        st.info("🕒 目前暂无记录。去主线任务随便写点什么试试吧！")
    else:
        # 降序显示
        for idx, record in enumerate(reversed(st.session_state.history)):
            with st.expander(f"🕰️ {record['timestamp']} - {record['task_type']}", expanded=(idx == 0)):
                
                st.markdown("#### 🔹 最初的需求与原稿重现")
                st.info(record["user_input"])
                
                st.markdown("#### 💬 当时落锤打磨确认的加工建议细节")
                st.text(record.get("process_log", "无流转细节日志"))
                
                st.markdown("#### ⭐ 最终为您呈现的完美果实")
                st.success(record["final_output"])
