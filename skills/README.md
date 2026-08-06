# Skills

此目录只存放正式使用的个人 Skills。

每个一级子目录都是一个独立技能，至少包含一个带 YAML frontmatter 的 `SKILL.md`：

```text
skills/
└── example-skill/
    ├── SKILL.md
    ├── scripts/       # 可选
    ├── references/    # 可选
    └── assets/        # 可选
```

不要把多个无关能力堆进同一个技能，也不要在目录中保存真实凭证或本机敏感配置。

## 当前 Skills

| 目录 | 功能 |
|---|---|
| `before-dev/` | 所有开发需求实施前分析问题或目标、对比方案并等待用户审批 |
| `after-dev/` | 开发完成后依据实际差异复盘工作、前后变化、流程变化和验证结果 |
| `bark-notifications/` | 发送、集成、测试和排查 Bark iOS 推送通知 |
| `reflect/` | 从用户纠错中提炼有边界的候选规则，经审核后再写入项目 `AGENTS.md` |
| `simple/` | 将复杂说明转成易懂中文，并提供流程图、时序图和对照表 |
