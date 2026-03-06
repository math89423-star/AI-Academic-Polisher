FROM python:3.10-slim

WORKDIR /app

# 安装 procps 系统工具包以提供 pkill 等进程管理命令
RUN apt-get update && \
    apt-get install -y procps && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 赋予新脚本执行权限
RUN chmod +x start_docker.bash

# 指定容器启动时运行新的 Docker 专用脚本
CMD ["bash", "start_docker.bash"]