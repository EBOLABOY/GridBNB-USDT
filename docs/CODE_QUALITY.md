# 代码质量工具使用指南

本项目使用多种工具来保证代码质量、一致性和可维护性。本文档将详细介绍如何安装和使用这些工具。

## 📦 快速开始

### 1. 安装开发依赖

```bash
# 确保虚拟环境已激活
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装所有开发工具
pip install -r requirements-dev.txt
```

### 2. 安装 Pre-commit 钩子

```bash
# 安装 Git 钩子 (首次使用必须执行)
pre-commit install

# 手动运行所有检查 (可选)
pre-commit run --all-files
```

安装完成后,每次 `git commit` 时会自动运行代码检查。

## 🔧 工具介绍

### 1. Black - 代码格式化

**作用**: 自动格式化 Python 代码,统一代码风格。

**手动运行**:
```bash
# 格式化所有 Python 文件
black .

# 仅检查不修改
black --check .

# 格式化单个文件
black config.py
```

**配置**: `pyproject.toml` 中的 `[tool.black]` 部分
- 行长度: 100 字符
- 目标版本: Python 3.8+

### 2. isort - 导入排序

**作用**: 自动排序和分组 import 语句。

**手动运行**:
```bash
# 排序所有文件的 import
isort .

# 仅检查不修改
isort --check-only .

# 排序单个文件
isort config.py
```

**配置**: `pyproject.toml` 中的 `[tool.isort]` 部分
- 使用 Black 兼容模式
- 行长度: 100 字符
- 导入分组: 标准库 → 第三方库 → 本地库

### 3. Flake8 - 代码质量检查

**作用**: 检查代码风格、语法错误和代码复杂度。

**手动运行**:
```bash
# 检查所有 Python 文件
flake8

# 检查单个文件
flake8 config.py

# 显示详细统计
flake8 --statistics
```

**配置**: `.flake8` 文件
- 最大行长度: 100 字符
- 最大圈复杂度: 15
- 文档字符串风格: Google 风格

**常见错误代码**:
- `E501`: 行太长 (由 Black 处理,已忽略)
- `F401`: 导入但未使用
- `F841`: 定义但未使用的变量
- `E302`: 函数定义前需要 2 个空行
- `D100-D107`: 缺少文档字符串

### 4. mypy - 静态类型检查

**作用**: 检查 Python 类型注解,提前发现类型错误。

**手动运行**:
```bash
# 检查所有文件
mypy .

# 检查单个文件
mypy config.py

# 显示详细信息
mypy --show-error-codes .
```

**配置**: `pyproject.toml` 中的 `[tool.mypy]` 部分
- 目标版本: Python 3.8
- 初期宽松配置,逐步严格

**当前检查的文件**:
- `config.py`
- `risk_manager.py`
- `helpers.py`

*注意*: mypy 初期仅检查部分核心文件,逐步扩展到全部代码。

### 5. Bandit - 安全检查

**作用**: 扫描代码中的安全漏洞和潜在风险。

**手动运行**:
```bash
# 扫描所有文件
bandit -r .

# 生成详细报告
bandit -r . -f html -o bandit_report.html

# 忽略测试文件
bandit -r . --exclude tests/
```

**配置**: `pyproject.toml` 中的 Bandit 部分

**常见告警**:
- `B201`: Flask debug 模式
- `B301`: Pickle 序列化风险
- `B404`: subprocess 使用
- `B608`: SQL 注入风险

### 6. Pre-commit - 自动化检查

**作用**: 在 Git 提交前自动运行所有代码检查。

**命令**:
```bash
# 安装钩子 (首次必须)
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 跳过检查提交 (不推荐)
git commit --no-verify

# 更新钩子版本
pre-commit autoupdate
```

**配置**: `.pre-commit-config.yaml`

**检查流程**:
1. 文件末尾换行符
2. 移除多余空白
3. 检查合并冲突标记
4. 检查 YAML/JSON 语法
5. 检查大文件 (>500KB)
6. 防止直接提交到 main/master
7. Black 代码格式化
8. isort 导入排序
9. Flake8 代码检查
10. mypy 类型检查 (仅部分文件)
11. Bandit 安全扫描
12. Markdown 文件检查
13. YAML 文件格式化

## 📊 测试和覆盖率

### Pytest - 单元测试

**运行测试**:
```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_config.py

# 显示详细输出
pytest -v

# 运行特定标记的测试
pytest -m unit          # 仅单元测试
pytest -m "not slow"    # 跳过慢速测试
```

### Coverage - 代码覆盖率

**生成覆盖率报告**:
```bash
# 运行测试并生成覆盖率报告
pytest --cov

# 生成 HTML 报告
pytest --cov --cov-report=html

# 查看报告
# Windows:
start htmlcov/index.html
# Linux/Mac:
open htmlcov/index.html
```

**配置**: `pyproject.toml` 中的 `[tool.coverage]` 部分

## 🚀 推荐工作流

### 开发新功能

```bash
# 1. 创建新分支
git checkout -b feature/new-feature

# 2. 编写代码
vim config.py

# 3. 格式化代码
black .
isort .

# 4. 运行检查
flake8
mypy .

# 5. 运行测试
pytest

# 6. 提交代码 (自动触发 pre-commit)
git add .
git commit -m "feat: add new feature"
```

### 修复检查失败

如果 pre-commit 检查失败:

1. **Black/isort 失败**: 这些工具会自动修复,重新 `git add` 并提交
2. **Flake8 失败**: 根据错误信息手动修复代码
3. **mypy 失败**: 添加类型注解或使用 `# type: ignore` 注释
4. **Bandit 失败**: 评估安全风险并修复或添加 `# nosec` 注释

### 跳过特定检查

在特殊情况下,可以跳过检查:

```python
# 跳过 Flake8 检查
print("debug")  # noqa: T001

# 跳过 Bandit 安全检查
subprocess.call(cmd, shell=True)  # nosec

# 跳过 mypy 类型检查
value = some_function()  # type: ignore
```

## ⚙️ 配置文件说明

### pyproject.toml
- **Black**: 代码格式化配置
- **isort**: 导入排序配置
- **mypy**: 类型检查配置
- **pytest**: 测试框架配置
- **coverage**: 覆盖率配置

### .flake8
- Flake8 代码检查配置
- *注意*: Flake8 不支持 `pyproject.toml`

### .pre-commit-config.yaml
- Pre-commit 钩子配置
- 包含所有工具的版本和参数

## 🔍 常见问题

### Q1: Black 和 Flake8 冲突?
**A**: 已在 `.flake8` 中配置忽略冲突的错误代码 (E203, E501, W503)。

### Q2: mypy 报告第三方库类型错误?
**A**: 在 `pyproject.toml` 中的 `[[tool.mypy.overrides]]` 添加 `ignore_missing_imports = true`。

### Q3: Pre-commit 太慢?
**A**: 可以跳过某些钩子:
```bash
SKIP=mypy,bandit git commit -m "message"
```

### Q4: 如何临时禁用 pre-commit?
**A**: 使用 `--no-verify` 标志:
```bash
git commit --no-verify -m "message"
```
*注意*: 不推荐频繁使用,可能引入质量问题。

### Q5: 如何为特定目录禁用检查?
**A**: 在各工具配置中添加 `exclude` 规则。例如:
```toml
# pyproject.toml
[tool.black]
extend-exclude = '''
/(
  | data
  | nginx
)/
'''
```

## 📚 扩展阅读

- [Black 官方文档](https://black.readthedocs.io/)
- [isort 官方文档](https://pycqa.github.io/isort/)
- [Flake8 官方文档](https://flake8.pycqa.org/)
- [mypy 官方文档](https://mypy.readthedocs.io/)
- [Bandit 官方文档](https://bandit.readthedocs.io/)
- [Pre-commit 官方文档](https://pre-commit.com/)
- [Pytest 官方文档](https://docs.pytest.org/)

## 🎯 下一步计划

为了持续提升代码质量,建议:

1. ✅ **已完成**: 配置所有基础工具
2. 📝 **进行中**: 为核心模块添加类型注解
3. 🔜 **计划**: 扩展 mypy 检查到更多文件
4. 🔜 **计划**: 提高测试覆盖率到 80%+
5. 🔜 **计划**: 添加 CI/CD 自动化检查

---

**注意**: 本文档会随着项目演进不断更新。如有问题或建议,请提交 Issue。
