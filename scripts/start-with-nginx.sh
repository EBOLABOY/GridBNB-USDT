#!/bin/bash

# GridBNB Trading Bot - Ubuntu/Linux 部署脚本
# 专为 Ubuntu 服务器优化
# 优化记录:
# - 使用 docker compose 替代 docker-compose
# - 添加 sudo 检测和提示
# - 优化 Docker 安装流程

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 sudo 是否可用
check_sudo() {
    log_info "检查 sudo 命令..."

    if ! command -v sudo &> /dev/null; then
        log_error "sudo 命令未安装"
        echo ""
        echo "在 Debian 系统上,sudo 默认未安装。请以 root 用户运行以下命令安装:"
        echo ""
        echo "  su -"
        echo "  apt-get update"
        echo "  apt-get install -y sudo"
        echo "  usermod -aG sudo $USER"
        echo "  exit"
        echo ""
        echo "然后重新登录并再次运行此脚本。"
        exit 1
    fi

    # 检查当前用户是否在 sudo 组中
    if ! groups | grep -q '\bsudo\b'; then
        log_warning "当前用户不在 sudo 组中"
        echo ""
        echo "请以 root 用户运行以下命令将当前用户添加到 sudo 组:"
        echo ""
        echo "  su -"
        echo "  usermod -aG sudo $USER"
        echo "  exit"
        echo ""
        echo "然后重新登录并再次运行此脚本。"
        exit 1
    fi

    log_success "sudo 检查通过"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到root用户，建议使用普通用户运行"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 检查系统要求
check_system() {
    log_info "检查系统环境..."

    # 检查操作系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
            log_warning "检测到非Ubuntu/Debian系统: $PRETTY_NAME"
            log_warning "脚本主要针对Ubuntu优化,其他系统可能需要手动调整"
        else
            log_success "系统检测: $PRETTY_NAME"
        fi
    fi

    # 检查内存
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$MEMORY_GB" -lt 1 ]; then
        log_warning "内存不足1GB，建议至少512MB可用内存"
    else
        log_success "内存检查通过: ${MEMORY_GB}GB"
    fi

    # 检查磁盘空间
    DISK_AVAIL=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$DISK_AVAIL" -lt 1 ]; then
        log_error "磁盘空间不足，至少需要1GB可用空间"
        exit 1
    else
        log_success "磁盘空间检查通过: ${DISK_AVAIL}GB可用"
    fi
}

# 检测 Docker Compose 命令
# 项目标准: 使用 docker compose (Docker 20.10+)
# 向后兼容: 支持旧版 docker-compose (仅用于旧环境过渡)
detect_docker_compose_cmd() {
    # 优先使用 docker compose (项目标准)
    if docker compose version &> /dev/null; then
        echo "docker compose"
    # 回退到 docker-compose (旧环境降级支持)
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo ""
    fi
}

# 安装Docker (使用官方便捷脚本)
install_docker() {
    if ! command -v docker &> /dev/null; then
        log_info "Docker未安装，开始安装..."

        log_info "使用Docker官方便捷安装脚本..."

        # 下载并运行Docker官方安装脚本
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh

        # 将当前用户添加到docker组
        sudo usermod -aG docker $USER

        log_success "Docker安装完成"
        log_warning "请重新登录以使docker组权限生效，或运行: newgrp docker"

        # 启动并启用Docker服务
        sudo systemctl enable docker
        sudo systemctl start docker
    else
        log_success "Docker已安装: $(docker --version)"
    fi
}

# 检查 Docker Compose 插件
check_docker_compose() {
    log_info "检查 Docker Compose..."

    DOCKER_COMPOSE_CMD=$(detect_docker_compose_cmd)

    if [ -z "$DOCKER_COMPOSE_CMD" ]; then
        log_warning "Docker Compose 未安装"
        log_info "现代Docker版本已内置 Compose 插件"
        log_info "尝试安装 Docker Compose 插件..."

        # 安装 Docker Compose 插件
        sudo apt-get update
        sudo apt-get install -y docker-compose-plugin

        # 再次检测
        DOCKER_COMPOSE_CMD=$(detect_docker_compose_cmd)

        if [ -z "$DOCKER_COMPOSE_CMD" ]; then
            log_error "Docker Compose 安装失败"
            exit 1
        fi
    fi

    log_success "使用命令: $DOCKER_COMPOSE_CMD"
    log_success "版本: $($DOCKER_COMPOSE_CMD version)"

    # 导出全局变量供后续使用
    export DOCKER_COMPOSE_CMD
}

# 主函数
main() {
    echo "🚀 GridBNB Trading Bot - Ubuntu/Linux 部署脚本"
    echo "=================================================="

    check_sudo
    check_root
    check_system
    install_docker
    check_docker_compose

    # 检查必要文件
    log_info "检查项目文件..."
    if [ ! -f "config/.env" ]; then
        log_error "配置文件不存在: config/.env"
        log_info "请先复制 config/.env.example 为 config/.env 并配置"
        exit 1
    fi
    if [ ! -f "docker/docker-compose.yml" ]; then
        log_error "Docker配置文件不存在: docker/docker-compose.yml"
        exit 1
    fi
    if [ ! -f "docker/nginx/nginx.conf" ]; then
        log_error "Nginx配置文件不存在: docker/nginx/nginx.conf"
        exit 1
    fi
    log_success "项目文件检查完成"

    # 创建必要的目录
    log_info "创建必要的目录..."
    mkdir -p data docker/nginx/logs

    # 设置权限
    chmod 755 data docker/nginx/logs

    # 切换到docker目录
    cd docker

    # 停止现有容器
    log_info "停止现有容器..."
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true

    # 构建并启动服务
    log_info "构建并启动服务..."
    $DOCKER_COMPOSE_CMD up -d --build

    # 返回项目根目录
    cd ..

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 15

    # 检查服务状态
    log_info "检查服务状态..."
    cd docker && $DOCKER_COMPOSE_CMD ps && cd ..

    # 验证安全配置
    log_info "验证安全配置..."
    if cd docker && $DOCKER_COMPOSE_CMD port gridbnb-bot 8080 2>/dev/null; then
        cd ..
        log_warning "8080端口仍然开放，建议检查docker-compose.yml配置"
    else
        cd ..
        log_success "安全配置正确: 8080端口已关闭"
    fi

    # 显示访问信息
    echo ""
    log_success "🎉 GridBNB交易机器人部署完成！"
    echo "=================================================="
    echo "🌐 访问地址:"
    echo "   - Web界面: http://$(hostname -I | awk '{print $1}')"
    echo "   - 本地访问: http://localhost"
    echo "   - 安全配置: 仅通过Nginx访问，8080端口已关闭"
    echo ""
    echo "📊 管理命令:"
    echo "   - 查看状态: cd docker && $DOCKER_COMPOSE_CMD ps"
    echo "   - 查看日志: cd docker && $DOCKER_COMPOSE_CMD logs -f"
    echo "   - 重启服务: cd docker && $DOCKER_COMPOSE_CMD restart"
    echo "   - 停止服务: cd docker && $DOCKER_COMPOSE_CMD down"
    echo "   - 更新代码: git pull && cd docker && $DOCKER_COMPOSE_CMD up -d --build"
    echo ""
    echo "📝 日志位置:"
    echo "   - 应用日志: ./trading_system.log"
    echo "   - Nginx日志: ./docker/nginx/logs/"
    echo "   - Docker日志: cd docker && $DOCKER_COMPOSE_CMD logs"
    echo ""
    echo "🔧 故障排除:"
    echo "   - 检查端口: sudo netstat -tlnp | grep :80"
    echo "   - 检查防火墙: sudo ufw status"
    echo "   - 重启Docker: sudo systemctl restart docker"
    echo "=================================================="
}

# 运行主函数
main "$@"
