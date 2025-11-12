# GridBNB-USDT 项目技术标准

> **创建时间**: 2025-10-20
> **状态**: 正式生效
> **适用范围**: 所有开发、部署和文档

---

## 📋 容器化标准

### Docker Compose 命令规范

**项目标准**: 统一使用 `docker compose` (无连字符)

#### 标准命令示例

```bash
# ✅ 正确 - 使用项目标准
docker compose up -d
docker compose down
docker compose ps
docker compose logs -f
docker compose restart

# ❌ 错误 - 不再推荐
docker-compose up -d
docker-compose down
docker-compose ps
```

#### 技术背景

Docker Compose V2 已作为 Docker CLI 插件集成到 Docker 20.10+ 版本中：

- **发布时间**: 2020年12月 (Docker 20.10)
- **官方状态**: Compose V2 是官方推荐方案
- **独立版本**: `docker-compose` (Python实现) 已进入维护模式
- **性能优势**: Compose V2 使用 Go 语言重写，性能更优

#### 环境要求

**最低版本**:
- Docker Engine: 20.10+
- Docker Desktop: 3.4.0+

**验证命令**:
```bash
docker --version
# 应显示 20.10 或更高版本

docker compose version
# 应显示 Docker Compose version v2.x.x
```

#### 向后兼容说明

本项目脚本中保留了 `docker-compose` 的检测逻辑，但这**仅用于旧环境的过渡支持**：

```bash
# scripts/start-with-nginx.sh 中的检测逻辑
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
```

**重要声明**:
- 新部署环境**必须**使用 Docker 20.10+ 版本
- 不推荐依赖降级逻辑
- 旧环境应尽快升级到标准版本

---

## 📝 文档规范

### Docker 命令文档化

在所有文档中（README、教程、脚本注释）：

✅ **使用**:
```bash
docker compose up -d
```

❌ **避免**:
```bash
docker-compose up -d
# 或
docker compose / docker-compose
```

### 示例引用

**正确示例**:
```markdown
## 部署步骤

1. 启动服务：
   ```bash
   docker compose up -d
   ```

2. 查看状态：
   ```bash
   docker compose ps
   ```
```

**错误示例**:
```markdown
## 部署步骤

1. 启动服务（使用 docker compose 或 docker-compose）：
   ```bash
   docker compose up -d
   # 或
   docker-compose up -d
   ```
```

---

## 🔄 迁移指南

### 从 docker-compose 迁移

如果您的环境目前使用 `docker-compose`，请按以下步骤迁移：

#### 1. 检查 Docker 版本

```bash
docker --version
```

- 如果版本 < 20.10，需要升级 Docker
- 如果版本 >= 20.10，已内置 Compose V2

#### 2. 验证 Compose V2

```bash
docker compose version
```

如果命令成功，说明 Compose V2 已可用。

#### 3. 更新命令

全局替换所有脚本和文档中的命令：

```bash
# 使用 sed 批量替换（Linux/Mac）
find . -type f -name "*.sh" -exec sed -i 's/docker-compose/docker compose/g' {} +

# 手动检查并更新文档
# - README.md
# - 教程文件
# - CI/CD 配置
```

#### 4. 测试验证

```bash
# 测试基本命令
docker compose ps
docker compose config

# 测试完整部署
./scripts/start-with-nginx.sh
```

#### 5. 移除旧版本（可选）

```bash
# 卸载独立的 docker-compose
sudo rm /usr/local/bin/docker-compose

# 或通过包管理器卸载
sudo apt-get remove docker-compose  # Debian/Ubuntu
```

---

## 📚 参考资料

### 官方文档
- [Docker Compose V2 发布公告](https://docs.docker.com/compose/compose-v2/)
- [Compose V2 迁移指南](https://docs.docker.com/compose/migrate/)
- [Docker Compose 命令兼容性](https://docs.docker.com/compose/cli-command-compatibility/)

### 项目文档
- [脚本优化说明](SCRIPT_OPTIMIZATION.md) - 详细的技术实现
- [企业级路径处理](ENTERPRISE_PATH_FIX.md) - 路径处理标准
- [主文档](../README.md) - 项目总览

---

## ✅ 检查清单

在提交代码前，请确认：

- [ ] 所有脚本使用 `docker compose`（无连字符）
- [ ] 文档中没有出现 `docker-compose`（除非在迁移说明中）
- [ ] 没有出现"使用 docker compose 或 docker-compose"的模糊表述
- [ ] 脚本注释中明确标注"项目标准"
- [ ] 新环境部署验证使用 Docker 20.10+

---

**标准维护者**: 项目维护团队
**最后更新**: 2025-10-20
**下次审查**: 2026-01-01 (或 Docker 重大版本更新时)
