# my-codex-skills

用于集中版本控制、持续改进并在多台电脑之间同步个人 Codex Skills 和插件。

## 仓库结构

```text
my-codex-skills/
├── plugins/                # 可安装插件；Bark 的 Skill 与生命周期 Hook 打包在这里
│   └── bark-notifications/
├── skills/                 # 独立技能；每个子目录都是一个独立 Skill
│   ├── before-dev/         # 开发前分析需求、对比方案并等待审批
│   ├── after-dev/          # 开发完成后复盘实际改动和验证结果
│   ├── reflect/            # 从纠错中提炼候选规则，经审核后写入项目记忆
│   └── simple/             # 把复杂内容解释清楚并生成配套图表
└── templates/
    └── skill-template/     # 新技能模板
```

## 已收录 Skills

| Skill | 用途 | 安装路径 |
|---|---|---|
| `before-dev` | 所有开发需求实施前分析问题或目标、对比方案并等待用户审批 | `skills/before-dev` |
| `after-dev` | 开发完成后依据实际差异复盘工作，对比修改前后、流程变化和验证结果 | `skills/after-dev` |
| `bark-notifications` | Bark 通知 Skill + 插件 Stop Hook | `plugins/bark-notifications` |
| `reflect` | 复盘人类纠正过程，提炼有边界的候选规则，经审核后写入项目 `AGENTS.md` | `skills/reflect` |
| `simple` | 用易懂中文、流程图、时序图和对照表解释复杂内容 | `skills/simple` |

## 开发协作工作流

1. 收到 Bug、新功能、重构、配置或其他开发需求时，先使用 `$before-dev` 进行只读分析。
2. `$before-dev` 说明原因或能力缺口、对比可行方案、给出建议和验收标准，然后等待用户明确审批。
3. 用户批准后再实施；方案或范围发生实质变化时重新审批。
4. 开发完成后使用 `$after-dev`，基于实际差异和验证证据输出修改前后对比；只有流程确实改变时才输出流程对比。

## 新建一个 Skill

```bash
cp -R templates/skill-template skills/my-new-skill
```

然后编辑 `skills/my-new-skill/SKILL.md`。建议一个技能只解决一类清晰的问题；需要的脚本、参考资料和资源都放在该技能自己的目录内。

## 在当前电脑安装

使用 Codex 的插件市场安装 `bark-notifications`。它会同时安装 Skill 和插件级 Stop Hook，不需要手动编辑 `~/.codex/hooks.json`。

独立 Skills 仍使用 Codex 内置的 `$skill-installer`，按需安装指定 Skill。例如：

```text
使用 $skill-installer 从 czm233/my-codex-skills 安装：
skills/before-dev
skills/after-dev
skills/reflect
skills/simple
```

也可以一次指定多个 Skill：

```text
使用 $skill-installer 从 czm233/my-codex-skills 安装：
skills/skill-one
skills/skill-two
```

## 在其他电脑同步

在目标电脑登录有权访问该仓库的 GitHub 账号，然后安装用户级 `bark-notifications` 插件；其他独立 Skill 仍通过 `$skill-installer` 安装。

`$skill-installer` 默认不会覆盖已存在的同名 Skill。需要更新时，让 Codex 删除本机旧版本并从仓库重新安装指定 Skill：

```text
使用 $skill-installer 重新安装 czm233/my-codex-skills 中的：
skills/before-dev
skills/after-dev
```

## 安全约定

- 不提交 API Key、Token、Cookie、密码、私钥或其他真实凭证。
- 本机配置使用 `.env.local`、`config.local.*` 等文件，并保持在 Git 忽略列表中。
- 需要展示配置格式时，只提交带明显占位值的 `.example` 或 `.sample` 文件。

## 推荐迭代流程

1. 在独立技能目录中修改并本机验证。
2. 检查 Git diff，确认没有凭证和本机敏感配置。
3. 提交并推送到 GitHub。
4. 其他电脑拉取最新版本。
