#!/bin/bash

# GridBNB Trading Bot - 简单更新脚本
# 用于安全更新GitHub代码并重启服务
# 项目标准: 使用 docker compose (Docker 20.10+)
# 优化记录:
# - 使用 docker compose 作为标准命令
# - 添加 sudo 检测

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo -e "${GREEN}🔄 GridBNB Trading Bot 更新脚本${NC}"
echo "=================================="

# 检查 sudo
check_sudo

# 检测 Docker Compose 命令
DOCKER_COMPOSE_CMD=$(detect_docker_compose_cmd)

if [ -z "$DOCKER_COMPOSE_CMD" ]; then
    log_error "Docker Compose 未安装或不可用"
    echo ""
    echo "请先安装 Docker 和 Docker Compose:"
    echo "  - 使用官方脚本: curl -fsSL https://get.docker.com | sudo sh"
    echo "  - 或安装插件: sudo apt-get install docker-compose-plugin"
    exit 1
fi

log_success "使用命令: $DOCKER_COMPOSE_CMD"

# 1. 检查当前目录是否为项目目录
if [ ! -f "docker-compose.yml" ] || [ ! -f ".env" ]; then
    log_error "请在GridBNB项目目录中运行此脚本"
    exit 1
fi

log_info "当前目录: $(pwd)"

# 2. 检查配置文件
log_info "检查配置文件..."
if [ ! -f ".env" ]; then
    log_error ".env文件不存在，请先配置"
    exit 1
fi
log_success ".env配置文件存在"

# 3. 检查Git状态
log_info "检查Git状态..."
if [ -n "$(git status --porcelain)" ]; then
    log_warning "检测到本地修改，将暂存这些更改"
    git stash push -m "Auto stash before update $(date)"
    STASHED=true
else
    STASHED=false
fi

# 4. 拉取最新代码
log_info "拉取最新代码..."
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log_success "代码已是最新版本"
    UPDATE_NEEDED=false
else
    log_info "发现新版本，开始更新..."
    git pull origin main
    UPDATE_NEEDED=true
    log_success "代码更新完成"

    # 自动恢复update.sh的执行权限
    log_info "恢复update.sh执行权限..."
    chmod +x update.sh
    log_success "update.sh执行权限已恢复"
fi

# 5. 恢复本地修改 (如果有暂存)
if [ "$STASHED" = true ]; then
    log_info "恢复本地个性化修改..."
    if git stash pop; then
        log_success "本地修改已恢复"
    else
        log_warning "恢复本地修改时出现冲突，请手动解决"
        echo "💡 查看冲突: git status"
        echo "💡 解决后继续: git add . && git stash drop"
    fi
fi

# 6. 验证配置文件
log_info "验证配置文件..."
if [ -f ".env" ]; then
    log_success ".env配置文件完好无损"
else
    log_error ".env文件丢失"
    exit 1
fi

# 7. 重新构建并启动服务
log_info "重新构建并启动Docker服务..."
$DOCKER_COMPOSE_CMD down
log_success "服务已停止"

$DOCKER_COMPOSE_CMD up -d --build
log_success "服务重新构建并启动"

# 8. 等待服务启动
log_info "等待服务启动..."
sleep 15

# 9. 检查服务状态
log_info "检查服务状态..."
if $DOCKER_COMPOSE_CMD ps | grep -q "Up"; then
    log_success "服务运行正常"

    # 验证安全配置
    log_info "验证安全配置..."
    if $DOCKER_COMPOSE_CMD port gridbnb-bot 8080 2>/dev/null; then
        log_warning "8080端口仍然开放，建议检查docker-compose.yml配置"
    else
        log_success "安全配置正确: 8080端口已关闭"
    fi

    # 显示服务状态
    echo ""
    echo "📊 服务状态:"
    $DOCKER_COMPOSE_CMD ps

    # 显示最新日志
    echo ""
    echo "📝 最新日志 (最近5行):"
    $DOCKER_COMPOSE_CMD logs --tail=5 gridbnb-bot

else
    log_error "服务启动异常，请检查日志"
    echo "查看日志命令: $DOCKER_COMPOSE_CMD logs"
    exit 1
fi

# 10. 显示更新结果
echo ""
log_success "🎉 更新完成！"
echo "=================================="

if [ "$UPDATE_NEEDED" = true ]; then
    log_success "代码已更新到最新版本"
else
    log_info "代码已是最新版本，仅重启了服务"
fi

log_success ".env配置文件未受影响"
log_success "Docker服务已重启"
log_success "服务运行正常"



echo ""
echo "🌐 访问地址:"
echo "   - Web界面: http://$(hostname -I | awk '{print $1}')"
echo "   - 本地访问: http://localhost"
echo "   - 安全配置: 仅通过Nginx访问，8080端口已关闭"

echo ""
echo "📊 常用命令:"
echo "   - 查看状态: $DOCKER_COMPOSE_CMD ps"
echo "   - 查看日志: $DOCKER_COMPOSE_CMD logs -f"
echo "   - 重启服务: $DOCKER_COMPOSE_CMD restart"

echo ""
log_success "更新脚本执行完成！"
