# 1. 使用官方 Python 3.10 瘦身版镜像（推荐版本，兼容性最好）
FROM python:3.10-slim

# 2. 设置工作目录
WORKDIR /app

# 【新增这一行】：把默认的海外源替换为国内清华源，解决卡顿问题
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 3. 安装系统依赖（ChromaDB 等向量库底层依赖 C++ 编译环境，防止报错）
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 将当前目录下的所有代码复制到容器内
COPY . .

# 6. 暴露 Streamlit 的默认端口
EXPOSE 8501

# 7. 启动 Streamlit 服务
# 注意：请将 "app.py" 替换为你实际的启动文件名（比如 main.py 或 react_agent.py）
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]