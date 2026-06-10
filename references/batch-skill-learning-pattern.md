# Batch Skill Learning Pattern

> 学习技能广场技能的工作流模式

## 工作流

```
1. 选定分类 → 批量加载(5个/批) → 提取要点 → 存入记忆 → Git提交
```

## 具体步骤

### 1. 分类选择

按角色需求优先级：
- **程序员**：software-development → github → backend-patterns → devops
- **运维**：devops → kubernetes → security
- **创作者**：creative → media → copywriting

### 2. 批量加载

```python
# 同时加载多个技能
skill_view(name="skill-1")
skill_view(name="skill-2")
skill_view(name="skill-3")
skill_view(name="skill-4")
skill_view(name="skill-5")
```

**注意**：skill_view可能因JSON序列化问题失败，备用方案：
```python
read_file(path="/home/ubuntu/.hermes/skills/category/skill-name/SKILL.md")
```

### 3. 提取要点

每个技能提取：
- 核心原则（一句话）
- 关键流程（Phase/步骤）
- 常见坑点（陷阱）
- 快速参考命令

### 4. 存入记忆

更新 `~/.hermes/memories/EXTENDED_MEMORY.md`：
- 新增技能条目
- 简洁要点格式（便于回顾）

### 5. Git提交

```bash
cd /home/ubuntu/.hermes
git add skills/相关目录/
git commit -m "docs: 技能学习第N批 - skill1/skill2/..."
```

## 效率对比

| 方式 | 时间/技能 | 记忆留存 |
|------|----------|---------|
| 单个学 | 5min | 低 |
| 批量学 | 1min | 高（对比记忆）|

## 最佳实践

1. **对比学习**：同分类技能一起学，发现模式共性
2. **即时验证**：学完立即在当前会话应用（如TDD、debugging）
3. **定期回顾**：每周回顾记忆文件，强化理解

## 用户偏好（时刻生活）

- 用"继续"推进，不冗长解释
- 自主决策，无需询问许可
- 批量推进，每批提交
