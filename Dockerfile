FROM python:3.10-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list

# 安装 procps 系统工具包以提供 pkill 等进程管理命令
RUN apt-get update && \
    apt-get install -y procps && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

# 赋予新脚本执行权限
RUN chmod +x docker.sh

# 指定容器启动时运行新的 Docker 专用脚本
CMD ["bash", "docker.sh"]
