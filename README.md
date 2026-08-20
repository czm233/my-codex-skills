# my-codex-skills

用于集中版本控制、持续改进并在多台电脑之间同步个人 Codex Skills 和插件。

## 仓库结构

```text
my-codex-skills/
├── plugins/                # 可安装插件
│   ├── bark-notifications/ # Bark Skill + 生命周期 Hook
│   └── dev-workflow/       # 开发前后工作流插件
│       ├── .codex-plugin/plugin.json
│       └── skills/
│           ├── before-dev/ # 开发前分析需求、对比方案并等待审批
│           └── after-dev/  # 开发完成后复盘改动、验证和用户验收
├── skills/                 # Skill 源码；包含插件 Skill 的仓库保留副本
│   ├── before-dev/         # dev-workflow 插件的仓库源副本
│   ├── after-dev/          # dev-workflow 插件的仓库源副本
│   ├── reflect/            # 从纠错中提炼候选规则，经审核后写入项目记忆
│   └── simple/             # 把复杂内容解释清楚并生成配套图表
└── templates/
    └── skill-template/     # 新技能模板
```

## 已收录 Skills

| Skill | 用途 | 安装路径 |
|---|---|---|
| `dev-workflow` | 包含 `before-dev` 和 `after-dev` 两个独立 Skill，管理开发前审批与开发后复盘验收 | `plugins/dev-workflow` |
| `bark-notifications` | Bark 通知 Skill + 插件 Stop Hook | `plugins/bark-notifications` |
| `reflect` | 复盘人类纠正过程，提炼有边界的候选规则，经审核后写入项目 `AGENTS.md` | `skills/reflect` |
| `simple` | 用易懂中文、流程图、时序图和对照表解释复杂内容 | `skills/simple` |

`before-dev` 和 `after-dev` 的仓库源目录保留用于版本追踪；本机不单独安装这两个副本，实际运行使用 `plugins/dev-workflow` 插件内的版本。

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

使用 Codex 的插件市场安装 `bark-notifications` 和 `dev-workflow`。`bark-notifications` 会同时安装 Skill 和插件级 Stop Hook；`dev-workflow` 会安装 `before-dev` 与 `after-dev` 两个独立 Skill。

迁移或更新后请重启 Codex Desktop，并重新打开需要使用通知的会话；旧的 CLI/app-server 会话可能仍在内存中缓存已删除的旧 Hook 路径。

仍需单独安装的 Skill 使用 Codex 内置的 `$skill-installer`，按需安装指定 Skill。例如：

```text
skills/reflect
skills/simple
```

安装工作流插件时，使用仓库 marketplace：

```bash
codex plugin marketplace add czm233/my-codex-skills
codex plugin add dev-workflow@my-codex-skills
```

## 在其他电脑同步

在目标电脑登录有权访问该仓库的 GitHub 账号，然后安装 `bark-notifications` 和 `dev-workflow` 插件；`reflect`、`simple` 等独立 Skill 仍通过 `$skill-installer` 安装。

插件更新时，刷新 marketplace 并重新安装对应插件；本机不要同时安装同名的独立 Skill 副本和插件内 Skill 副本。

```bash
codex plugin marketplace upgrade my-codex-skills
codex plugin add dev-workflow@my-codex-skills
```

## 安全约定

- 不提交 API Key、Token、Cookie、密码、私钥或其他真实凭证。
- 本机配置使用 `.env.local`、`config.local.*` 等文件，并保持在 Git 忽略列表中。
- 需要展示配置格式时，只提交带明显占位值的 `.example` 或 `.sample` 文件。

## 推荐迭代流程

1. 在插件目录中修改并本机验证。
2. 检查 Git diff，确认没有凭证和本机敏感配置。
3. 更新插件版本并验证 marketplace 条目。
4. 经授权后提交并推送到 GitHub。
5. 其他电脑刷新 marketplace，重新安装对应插件并在新任务中验证。
