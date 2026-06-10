# 技能优化 Git 版本管理

## 工作流程

### 1. 初始化仓库

```bash
cd ~/.hermes
git init
git config user.email "hermes@local"
git config user.name "Hermes Agent"
git config --global --add safe.directory ~/.hermes
```

### 2. 创建.gitignore

```gitignore
# Cache and temporary files
cache/
image_cache/
tmp/
logs/

# Runtime state
*.lock
*.pid
*.log

# Private data
.env
auth.json
memories/
```

### 3. 提交优化变更

```bash
git add skills/sk-darwin-v3/
git add skills/software-development/writing-plans/
git commit -m "feat: install sk-darwin-v3 and optimize writing-plans to S-grade

- Install sk-darwin-v3 skill (150/150 S级)
- Optimize writing-plans skill (70D → 150S)
- darwin-v3 validation: +80 points improvement"
```

### 4. 技能改名时提交

```bash
mv skills/darwin-v3 skills/sk-darwin-v3
git add skills/sk-darwin-v3/
git commit -m "refactor: rename skill darwin-v3 to sk-darwin-v3"
```

## Commit Message 格式

```
feat: 安装新技能
refactor: 重命名/重构技能
fix: 修复技能问题
docs: 更新技能文档
```

## 本会话案例

成功提交：
- `f297b46` feat: install sk-darwin-v3 and optimize writing-plans to S-grade
- `ecf056f` refactor: rename skill darwin-v3 to sk-darwin-v3
- `580a19d` feat: install sk-harness skill (S级150分)

---

*创建时间: 2026-05-29*