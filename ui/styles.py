"""
简约优雅的 Apple 风格 CSS
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Noto Sans SC", sans-serif !important;
}

.stApp {
    background: #f5f5f7 !important;
    color: #1d1d1f !important;
}

#MainMenu, footer, header {
    visibility: hidden !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    border-right: 1px solid rgba(0, 0, 0, 0.06) !important;
}

/* 按钮 */
.stButton > button {
    background: linear-gradient(135deg, #0071e3, #409cff) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(0, 113, 227, 0.2) !important;
}

.stButton > button:hover {
    box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="secondary"] {
    background: rgba(0, 0, 0, 0.05) !important;
    color: #1d1d1f !important;
    box-shadow: none !important;
}

/* 聊天气泡 */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, #0071e3, #409cff) !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 8px rgba(0, 113, 227, 0.15) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] p {
    color: white !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: white !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 12px 16px !important;
    box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06) !important;
    border: 1px solid rgba(0, 0, 0, 0.04) !important;
}

/* 输入框 */
[data-testid="stChatInput"] {
    border-radius: 22px !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04) !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #0071e3 !important;
    box-shadow: 0 2px 16px rgba(0, 113, 227, 0.12) !important;
}

/* 表单 */
[data-testid="stForm"] {
    border: none !important;
    background: transparent !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input {
    border-radius: 12px !important;
    padding: 12px 16px !important;
    border: 1px solid rgba(0, 0, 0, 0.1) !important;
    background: white !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input:focus {
    border-color: #0071e3 !important;
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1) !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] label {
    display: none !important;
}

.stFormSubmitButton > button {
    background: linear-gradient(135deg, #0071e3, #409cff) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

/* 标题 */
.hero-title {
    font-size: 44px;
    font-weight: 700;
    background: linear-gradient(135deg, #1d1d1f, #0071e3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 8px;
}

.hero-subtitle {
    font-size: 17px;
    color: #86868b;
    text-align: center;
}

/* 欢迎卡片 */
.welcome-card {
    background: white;
    border-radius: 20px;
    padding: 48px 40px;
    box-shadow: 0 2px 20px rgba(0, 0, 0, 0.05);
    text-align: center;
    margin: 60px auto;
    max-width: 520px;
}

/* 技能标签 */
.skill-tag {
    display: inline-block;
    padding: 5px 12px;
    background: rgba(0, 113, 227, 0.07);
    color: #0071e3;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 4px;
}

/* 花朵 */
.flower-box {
    text-align: center;
    padding: 20px 0 10px;
}

.flower-container {
    display: inline-block;
    position: relative;
    width: 50px;
    height: 50px;
    cursor: pointer;
}

.flower-stem {
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 3px;
    height: 18px;
    background: #c7c7cc;
    border-radius: 2px;
    transition: all 0.5s ease;
}

.flower-center {
    position: absolute;
    top: 14px;
    left: 50%;
    transform: translateX(-50%);
    width: 10px;
    height: 10px;
    background: #c7c7cc;
    border-radius: 50%;
    transition: all 0.5s ease;
    z-index: 2;
}

.petal {
    position: absolute;
    top: 10px;
    left: 50%;
    width: 12px;
    height: 12px;
    background: #c7c7cc;
    border-radius: 50% 50% 50% 0;
    transform-origin: bottom left;
    transition: all 0.5s ease;
    opacity: 0.25;
    margin-left: -6px;
}

.petal:nth-child(1) { transform: rotate(0deg); }
.petal:nth-child(2) { transform: rotate(90deg); }
.petal:nth-child(3) { transform: rotate(180deg); }
.petal:nth-child(4) { transform: rotate(270deg); }

.flower-container:hover .flower-stem {
    height: 30px;
    background: #0071e3;
}

.flower-container:hover .flower-center {
    top: 4px;
    background: #0071e3;
    box-shadow: 0 0 8px rgba(0, 113, 227, 0.4);
}

.flower-container:hover .petal {
    opacity: 1;
    background: linear-gradient(135deg, #0071e3, #409cff);
}

.flower-container:hover .petal:nth-child(1) { transform: rotate(45deg) translateY(-10px) scale(1.15); }
.flower-container:hover .petal:nth-child(2) { transform: rotate(135deg) translateY(-10px) scale(1.15); }
.flower-container:hover .petal:nth-child(3) { transform: rotate(-135deg) translateY(-10px) scale(1.15); }
.flower-container:hover .petal:nth-child(4) { transform: rotate(-45deg) translateY(-10px) scale(1.15); }

/* 滚动条 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }

/* 底部间距 */
.main .block-container { padding-bottom: 60px !important; }
</style>
"""


def render_flower_html():
    return """
    <div class="flower-box">
        <div class="flower-container">
            <div class="petal"></div>
            <div class="petal"></div>
            <div class="petal"></div>
            <div class="petal"></div>
            <div class="flower-center"></div>
            <div class="flower-stem"></div>
        </div>
    </div>
    """
