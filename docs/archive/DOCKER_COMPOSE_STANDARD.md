# Docker Compose 标准化说明

> **生效日期**: 2025-10-20
> **状态**: ✅ 已完成
> **影响范围**: 全项目

---

## 📋 标准化总结

本项目已完成 Docker Compose 命令标准化，统一使用 `docker compose` (无连字符) 作为项目标准。

---

## ✅ 已完成的工作

### 1. 文档更新

#### README.md
- ✅ 更新所有 Docker 命令示例为 `docker compose`
- ✅ 移除"使用 docker compose 或 docker-compose"的模糊表述
- ✅ 明确标注项目标准: Docker 20.10+

**修改内容**:
- 手动更新方式 (第332-349行)
- 监控命令 (第351-368行)
- 故障排除 (第370-385行)
- 更新脚本说明 (第313-325行)

#### docs/SCRIPT_OPTIMIZATION.md
- ✅ 在顶部添加"项目标准"声明
- ✅ 更新优化说明，强调 `docker compose` 为标准
- ✅ 明确降级逻辑仅用于旧环境过渡

**修改内容**:
- 文件头部添加标准声明 (第6行)
- 概览章节添加重要声明 (第14行)
- 背景说明改为"项目标准命令" (第22-36行)
- 技术实现添加重要提示 (第62行)
- 优势章节更新措辞 (第64-70行)

#### docs/CLAUDE.md
- ✅ 在顶部添加"项目标准"元信息
- ✅ 新增"项目技术标准"章节 (位于文档开头)
- ✅ 更新变更记录

**修改内容**:
- 文件头部添加标准信息 (第6行)
- 新增"项目技术标准"章节 (第21-44行)
- 更新变更记录 (第12行)

### 2. 脚本更新

#### scripts/start-with-nginx.sh
- ✅ 添加清晰的注释说明项目标准
- ✅ 标注降级逻辑的用途

**修改内容** (第117-130行):
```bash
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
```

#### scripts/update.sh
- ✅ 更新头部注释
- ✅ 添加项目标准说明
- ✅ 统一检测函数注释

**修改内容**:
- 头部注释添加标准声明 (第3-8行)
- 检测函数添加说明 (第54-67行)

### 3. 新文档创建

#### docs/PROJECT_STANDARDS.md (新文件)
完整的项目技术标准文档，包含：
- ✅ Docker Compose 命令规范
- ✅ 技术背景说明
- ✅ 环境要求
- ✅ 向后兼容说明
- ✅ 文档规范示例
- ✅ 迁移指南
- ✅ 检查清单

---

## 📊 修改统计

### 修改的文件
1. `README.md` - 4处修改
2. `docs/SCRIPT_OPTIMIZATION.md` - 5处修改
3. `docs/CLAUDE.md` - 3处修改
4. `scripts/start-with-nginx.sh` - 1处修改
5. `scripts/update.sh` - 2处修改

### 新增的文件
1. `docs/PROJECT_STANDARDS.md` - 项目技术标准文档
2. `docs/DOCKER_COMPOSE_STANDARD.md` - 本文件（标准化说明）

---

## 🎯 标准要点

### 命令格式

✅ **正确**:
```bash
docker compose up -d
docker compose ps
docker compose logs -f gridbnb-bot
docker compose restart
docker compose down
```

❌ **错误** (已废弃):
```bash
docker-compose up -d
docker compose / docker-compose  # 不要写双选项
docker-compose ps
```

### 文档表述

✅ **正确**:
```markdown
使用 `docker compose` 命令启动服务：
```bash
docker compose up -d
```
```

❌ **错误**:
```markdown
使用 `docker compose` 或 `docker-compose` 命令：
```bash
docker compose up -d
# 或
docker-compose up -d
```
```

---

## 📋 未修改的文件（说明）

以下文件中提到的 `docker-compose` **保持不变**，原因说明：

### docker-compose.yml (文件名)
- 这是 Docker Compose 的标准配置文件名
- 即使使用 `docker compose` 命令，配置文件名仍然是 `docker-compose.yml`
- 这是 Docker 官方规范，不需要修改

### docs/README-https.md
- 该文件是 HTTPS 配置教程
- 其中提到的 `docker-compose.yml` 是指配置文件名
- `docker-compose网络` 是 Docker Compose 的网络功能名称
- 这些是专有名词，不需要修改

### 脚本中的检测逻辑
- `detect_docker_compose_cmd()` 函数中保留了 `docker-compose` 检测
- 这是为了向后兼容旧环境
- 已添加清晰注释说明其用途

---

## ✨ 关键成果

1. **统一标准**: 全项目文档和脚本统一使用 `docker compose`
2. **清晰文档**: 创建完整的技术标准文档
3. **向后兼容**: 保留旧环境支持，但明确标注为降级逻辑
4. **易于维护**: 所有开发者和 AI 助手都能清楚项目标准

---

## 🔍 验证方法

### 检查文档一致性
```bash
# 查找所有文档中的 docker-compose 引用
git grep -n "docker-compose" -- "*.md" "*.sh" "*.bat"

# 应该只在以下情况出现:
# 1. docker-compose.yml (文件名)
# 2. 脚本中的降级检测逻辑
# 3. README-https.md 中的专有名词
```

### 检查脚本标准化
```bash
# 查看 start-with-nginx.sh 是否有清晰注释
grep -A 3 "项目标准" scripts/start-with-nginx.sh

# 查看 update.sh 是否有清晰注释
grep -A 3 "项目标准" scripts/update.sh
```

---

## 📚 相关文档

- [PROJECT_STANDARDS.md](PROJECT_STANDARDS.md) - 完整的项目技术标准
- [SCRIPT_OPTIMIZATION.md](SCRIPT_OPTIMIZATION.md) - 脚本优化说明
- [CLAUDE.md](CLAUDE.md) - AI 上下文文档
- [README.md](../README.md) - 项目主文档

---

**标准化完成时间**: 2025-10-20 18:30
**执行者**: Claude AI
**审核状态**: ✅ 完成
