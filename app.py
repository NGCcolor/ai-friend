import time
import json
import os
import hashlib
import streamlit as st
from agent.react_agent import ReactAgent

# ==========================================
# 1. 页面全局配置 (必须放在第一行)
# ==========================================
st.set_page_config(
    page_title="智能旅游 AI 管家",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 隐藏官方 UI 元素
custom_css = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInputContainer {
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 2. 轻量级用户认证模块 (模拟数据库)
# ==========================================
USER_DB_DIR = "data"
USER_DB_FILE = os.path.join(USER_DB_DIR, "users_db.json")

# 确保数据目录存在
if not os.path.exists(USER_DB_DIR):
    os.makedirs(USER_DB_DIR)


def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users_data):
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=4)


def hash_password(password):
    """简单的密码 MD5 加密（体现工程素养）"""
    return hashlib.md5(password.encode()).hexdigest()


# ==========================================
# 3. 初始化会话状态 (Session State)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""

# ==========================================
# 4. 路由分发：未登录显示登录页，已登录显示主界面
# ==========================================
if not st.session_state["logged_in"]:
    # ---------------- 登录/注册页面 ----------------
    st.markdown("<h1 style='text-align: center;'>✈️ 智能旅游 AI 管家</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>请先登录以同步您的专属私有旅行画像</p>",
                unsafe_allow_html=True)

    # 使用居中列布局
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])

        # 登录 Tab
        with tab1:
            with st.form("login_form"):
                login_user = st.text_input("用户名")
                login_pwd = st.text_input("密码", type="password")
                submit_login = st.form_submit_button("登 录", use_container_width=True)

                if submit_login:
                    users = load_users()
                    if login_user in users and users[login_user]["password"] == hash_password(login_pwd):
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = login_user
                        st.session_state["user_id"] = users[login_user]["user_id"]
                        st.success("登录成功！正在进入系统...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("用户名或密码错误！")

        # 注册 Tab
        with tab2:
            with st.form("register_form"):
                reg_user = st.text_input("设置用户名")
                reg_pwd = st.text_input("设置密码", type="password")
                reg_pwd_confirm = st.text_input("确认密码", type="password")
                submit_register = st.form_submit_button("注 册", use_container_width=True)

                if submit_register:
                    users = load_users()
                    if reg_user in users:
                        st.error("该用户名已存在，请换一个！")
                    elif reg_pwd != reg_pwd_confirm:
                        st.error("两次输入的密码不一致！")
                    elif len(reg_user) < 2 or len(reg_pwd) < 4:
                        st.error("用户名至少2位，密码至少4位！")
                    else:
                        # 生成简单的唯一 user_id
                        new_user_id = f"uid_{int(time.time())}"
                        users[reg_user] = {
                            "user_id": new_user_id,
                            "password": hash_password(reg_pwd)
                        }
                        save_users(users)
                        st.success("注册成功！请切换到【登录】标签页进行登录。")

else:
    # ---------------- 核心 AI 管家页面 (用户已登录) ----------------

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2060/2060284.png", width=100)
        st.title(f"👋 欢迎, {st.session_state['username']}")
        st.caption(f"🆔 ID: {st.session_state['user_id']}")

        st.divider()
        st.subheader("🛠️ 已装载核心技能")
        st.markdown("""
        - 🌤️ **实时天气时空感知**
        - 🗺️ **高德地图智能规划**
        - 📕 **小红书实况排雷**
        - 📚 **私有高分口碑检索**
        - 👤 **用户私有画像构建** *(已激活)*
        """)
        st.divider()

        if st.button("🗑️ 清空历史对话", use_container_width=True):
            st.session_state["message"] = []
            st.rerun()

        if st.button("🚪 退出登录", type="primary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["message"] = []  # 退出时清空当前屏幕对话
            st.rerun()

    # 主内容区
    st.title("✈️ 旅游方案智能推荐引擎")

    if "agent" not in st.session_state:
        st.session_state["agent"] = ReactAgent()

    # 初始化欢迎语（带上用户名）
    if "message" not in st.session_state or len(st.session_state["message"]) == 0:
        st.session_state["message"] = [
            {"role": "assistant",
             "content": f"你好，**{st.session_state['username']}**！我是你的专属智能旅游管家。系统已挂载你的私有偏好画像，请问你想去哪里玩？"}
        ]

    avatar_dict = {"user": "🧑‍💻", "assistant": "✈️"}

    # 渲染历史记录
    for message in st.session_state["message"]:
        with st.chat_message(message["role"], avatar=avatar_dict[message["role"]]):
            st.write(message["content"])

    # 处理输入
    prompt = st.chat_input("例如：帮我规划一份哈尔滨3天2夜的避坑攻略，我不爱吃辣，怕冷。")

    if prompt:
        with st.chat_message("user", avatar=avatar_dict["user"]):
            st.write(prompt)

        # 1. 先把用户最新输入追加进 session state
        st.session_state["message"].append({"role": "user", "content": prompt})

        # ==========================================
        # 核心新增区：组装短期记忆 (治好大模型的金鱼脑)
        # ==========================================
        # 提取最近的对话记录作为上下文 (排除最后一条，因为最后一条是刚刚用户输入的 query)
        recent_msgs = st.session_state["message"][:-1][-6:]  # 取最近 3 轮 (6条) 对话

        history_str = ""
        for msg in recent_msgs:
            role_name = "用户" if msg["role"] == "user" else "AI管家"
            history_str += f"{role_name}：{msg['content']}\n"

        with st.chat_message("assistant", avatar=avatar_dict["assistant"]):
            response_messages = []

            with st.spinner("🧠 正在调度底层工具链，结合您的画像深度规划中..."):

                # ==========================================
                # 核心修改区：透传完整的 3 个参数给 LangGraph
                # ==========================================
                res_stream = st.session_state["agent"].execute_stream(
                    query=prompt,
                    user_id=st.session_state["user_id"],  # 打通画像物理隔离墙！
                    short_term_history=history_str  # 传给网关做指代消解！
                )


                def capture(generator, cache_list):
                    for chunk in generator:
                        cache_list.append(chunk)
                        for char in chunk:
                            # 模拟打字机效果，提升流式体验
                            time.sleep(0.01)
                            yield char


                st.write_stream(capture(res_stream, response_messages))

            full_response = "".join(response_messages)
            st.session_state["message"].append({"role": "assistant", "content": full_response})
