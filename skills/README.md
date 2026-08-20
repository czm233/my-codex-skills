# Skills

此目录保留正式 Skill 源码，也保留 `dev-workflow` 插件内两个 Skill 的仓库源副本。需要统一分发的工作流放在仓库根目录 `plugins/`；本机实际使用插件安装版本。

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
| `before-dev/` 与 `../plugins/dev-workflow/skills/before-dev/` | 开发前分析问题或目标、对比方案并等待用户审批；前者为仓库保留源副本，后者为插件实际来源 |
| `after-dev/` 与 `../plugins/dev-workflow/skills/after-dev/` | 开发完成后依据实际差异复盘工作、前后变化、流程变化和验证结果；前者为仓库保留源副本，后者为插件实际来源 |
| `bark-notifications` | 已迁移到 `plugins/bark-notifications/`，由插件同时管理 Skill 和 Stop Hook |
| `reflect/` | 从用户纠错中提炼有边界的候选规则，经审核后再写入项目 `AGENTS.md` |
| `simple/` | 将复杂说明转成易懂中文，并提供流程图、时序图和对照表 |
